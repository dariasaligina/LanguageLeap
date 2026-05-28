from datetime import datetime

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .forms import RegistrationForm, TextForm, CatalogFilterForm, ExportForm
from .models import Text, LanguageLevel, Language, Word, SavedWord, SavedText, ActivityTracker, \
    Friends


# Create your views here.
def catalog(request):
    language_levels = LanguageLevel.objects.all()
    form_values = {"searchField": "",
                   "minLevel": 1,
                   "maxLevel": 6}
    form = CatalogFilterForm(request.GET or None)
    if form.is_valid():
        form_values = form.cleaned_data
    texts = Text.catalog_filter(form_values, request.user if request.user.is_authenticated else None)
    paginator = Paginator(texts, 12)
    page_number = request.GET.get('page')
    page_texts = paginator.get_page(page_number)
    return render(request, "LanguageLeap/catalog.html", {
        "texts": page_texts,
        "language_levels": language_levels,
        "form_values": form_values,
    })


@csrf_protect
def user_registration(request):
    languages = Language.objects.all()
    form = RegistrationForm(request.POST or None)

    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("leap:my_profile")

    return render(request, "LanguageLeap/registration.html", {
        "languages": languages,
        "form": form,
    })


@csrf_protect
def user_login(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect("leap:my_profile")

    return render(request, "LanguageLeap/login.html", {"form": form})


def user_logout(request):
    logout(request)
    return redirect("leap:login")


@login_required
def text(request, text_id):
    text = get_object_or_404(Text, pk=text_id)
    words = SavedWord.filter_words_from_text(request.user.id, text_id)
    try:
        saved_text = SavedText.objects.get(user=request.user, text=text)
        text_status = saved_text.status.id
    except SavedText.DoesNotExist:
        text_status = 0

    return render(request, "LanguageLeap/text.html", {"text": text, "words": words, "text_status": text_status})


@csrf_protect
@login_required
def upload_text(request):
    form = TextForm(request.user, request.POST, request.FILES)
    if form.is_valid():
        pk = form.save()
        return redirect("leap:text", text_id=pk)
    return render(request, "LanguageLeap/upload_text.html", {"form": form})


class TranslateWord(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, text_id, paragraph, word_number):
        try:
            word_object = Word.objects.get(text_id=text_id, paragraph=paragraph, word_in_paragraph=word_number)
        except Word.DoesNotExist:
            try:
                word_object = Word().init_by_api(text_id, paragraph, word_number)
            except (IndexError, Text.DoesNotExist):
                raise Http404()
            word_object.save()

        saved_word = SavedWord(word=word_object, user=request.user)
        saved_word.save()
        word_data = {
            "word": word_object.word,
            "translation": word_object.translation,
            "definition": word_object.definition,
            "synonyms": word_object.synonyms,
            "antonyms": word_object.antonyms
        }
        return JsonResponse(word_data)


@login_required
def learn_page(request):
    saved_words = request.user.savedword_set.filter(next_rep__lt=datetime.now())
    all_words = request.user.savedword_set.all()
    return render(request, "LanguageLeap/learn.html", {"words": saved_words, "all_words": all_words})


def saved_word_update(request, saved_word_id, is_correct):
    saved_word = get_object_or_404(SavedWord, id=saved_word_id)
    if saved_word.user != request.user:
        raise PermissionDenied
    if is_correct:
        try:
            at = ActivityTracker.objects.get(user=saved_word.user, creation_date=timezone.now().date())
            at.plus_one()
        except ActivityTracker.DoesNotExist:
            at = ActivityTracker(user=saved_word.user)
        at.save()
        saved_word.correct_answer()
    else:
        saved_word.wrong_answer()
    saved_word.save()
    return JsonResponse({"saved_word": "updated"})


@login_required
def my_profile(request):
    user = request.user
    my_texts = Text.objects.filter(user=user)
    completed_texts = Text.objects.filter(savedtext__status_id=1, savedtext__user=user)
    current_texts = Text.objects.filter(savedtext__status_id=2, savedtext__user=user)
    future_texts = Text.objects.filter(savedtext__status_id=3, savedtext__user=user)
    return render(request, "LanguageLeap/profile.html", {
        "user": user,
        "my_texts": my_texts,
        "completed_texts": completed_texts,
        "current_texts": current_texts,
        "future_texts": future_texts,
    })


def delete_text(request, text_id):
    text = get_object_or_404(Text, id=text_id)
    text.delete()
    return redirect("leap:my_profile")


@login_required
def update_text_status(request, text_id, button_name):
    if button_name == "completedBtn":
        status = 1
    elif button_name == "readLaterBtn":
        status = 3
    elif button_name == "readBtn":
        status = 2
    else:
        raise Http404()
    try:
        saved_text = SavedText.objects.get(user=request.user, text_id=text_id)
        if saved_text.status.id == status:
            saved_text.delete()
        else:
            saved_text.status_id = status
            saved_text.save()
    except SavedText.DoesNotExist:
        saved_text = SavedText(user=request.user, text_id=text_id, status_id=status)
        saved_text.save()
    return redirect("leap:text", text_id=text_id)


def get_heatmap_data(request, user_id):
    saved_words_subquery = SavedWord.objects.filter(user_id=user_id).values(
        'creation_date').annotate(saved_words=Count('id')).values("creation_date", 'saved_words')
    activity_tracker_subquery = ActivityTracker.objects.filter(user_id=user_id).values('creation_date', "counter")
    ans = []
    for result in activity_tracker_subquery:
        value = {"creation_date": result["creation_date"], "cards_done": result["counter"], "saved_words": 0}
        q = saved_words_subquery.filter(creation_date=value["creation_date"])
        if q:
            value["saved_words"] = q[0]["saved_words"]
        ans.append(value)
    for result in saved_words_subquery:
        value = {"creation_date": result["creation_date"], "cards_done": 0, "saved_words": result["saved_words"]}
        q = activity_tracker_subquery.filter(creation_date=value["creation_date"])
        if not q:
            ans.append(value)
    return JsonResponse(ans, safe=0)


def user_page(request, user_id):
    user = get_object_or_404(User, id=user_id)
    known_words_response = form_known_word_response(user_id)
    saved_words_response = form_saved_word_response(user_id)
    table = form_friend_table(user)
    my_page = False
    if user_id == request.user.id:
        my_page = True
    my_friend = False
    if request.user.is_authenticated:
        if Friends.objects.filter(user_id=request.user.id, friend_id=user.id):
            my_friend = True
    return render(request, "LanguageLeap/user_page.html",
                  {"user": user, 'known_words': known_words_response, 'saved_words': saved_words_response,
                   'table': table, "my_page": my_page, "my_friend": my_friend})


def form_friend_table(user):
    friends = user.friends_as_user.all()
    table = [[user.id, user.username + " 💎", user.profile.user_stats['words_learned'],
              user.profile.user_stats['words_saved'], user.profile.user_stats['activity_count']]]
    for friend in friends:
        table.append([friend.friend.id, friend.friend.username, friend.friend.profile.user_stats['words_learned'],
                      friend.friend.profile.user_stats['words_saved'],
                      friend.friend.profile.user_stats['activity_count']])
    return table


def form_saved_word_response(user_id):
    sum_words = 0
    saved_words_response = []
    saved_words_counter = SavedWord.get_saved_word_counter(user_id)
    for date in saved_words_counter:
        sum_words += date['num_words']
        saved_words_response.append({'x': str(date['creation_date']), 'y': sum_words})
    return saved_words_response


def form_known_word_response(user_id):
    sum_words = 0
    known_words_response = []
    known_words_counter = SavedWord.get_known_word_counter(user_id)
    for date in known_words_counter:
        sum_words += date['num_words']
        known_words_response.append({'x': str(date['learned_date']), 'y': sum_words})
    return known_words_response


@login_required
def add_friend(request, friend_id):
    fr = Friends(user_id=request.user.id, friend_id=friend_id)
    fr.save()
    return redirect('leap:user_page', friend_id)


@login_required
def delete_friend(request, friend_id):
    fr = get_object_or_404(Friends, user_id=request.user.id, friend_id=friend_id)
    fr.delete()
    return redirect('leap:user_page', friend_id)


@login_required
def popular(request):
    texts = Text.objects.filter(language=request.user.profile.language, public=True)
    all_time = sorted(texts, key=lambda t: -t.save_count)[:24]
    year = sorted(texts, key=lambda t: (-t.saves_this_year, -t.save_count))[:24]
    month = sorted(texts, key=lambda t: (-t.saves_this_month, -t.save_count))[:24]
    week = sorted(texts, key=lambda t: (-t.saves_this_week, -t.save_count))[:24]
    return render(request, "LanguageLeap/popular.html",
                  {"all_time": all_time, "year": year, "month": month, "week": week})


@login_required
def export(request):
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            return form.export_to_csv(request.user)
        return render(request, "LanguageLeap/export.html", {'form': form})
    return render(request, "LanguageLeap/export.html", {'form': ExportForm()})
