import csv
import os
from datetime import datetime
from typing import List, Optional

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from gtts import gTTS
from mistralai.client import Mistral
from pydantic import BaseModel, Field
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from mysite import settings
from .forms import RegistrationForm, TextForm, CatalogFilterForm
from .models import Text, LanguageLevel, Language, Word, SavedWord, SavedText, ActivityTracker, \
    Friends, LastExport


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
    return render(request, "LanguageLeap/catalog.html", {
        "texts": texts,
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
    except:
        text_status = 0

    return render(request, "LanguageLeap/text.html", {"text": text, "words": words, "text_status": text_status})


# TODO: не добавляется аудио
@csrf_protect
@login_required
def upload_text(request):
    form = TextForm()
    if request.method == "POST":
        form = TextForm(request.POST)
        if form.is_valid():
            new_text = Text()
            new_text.user = request.user
            new_text.name = form.cleaned_data["name"]
            new_text.text = form.cleaned_data["text"]
            new_text.language = form.cleaned_data["language"]
            new_text.language_level = form.cleaned_data["language_level"]
            new_text.public = form.cleaned_data["public"]
            if form.cleaned_data["image"]:
                new_text.image = form.cleaned_data["image"]
                print("found image")
            else:
                print("not found image")
                new_text.image.name = "textImage/book.jpg"
            if form.cleaned_data["audio"]:
                new_text.audio = form.cleaned_data["audio"]
                print("found audio")
            else:
                print("not found audio")
                new_text.save()
                audio_dir = os.path.join(settings.MEDIA_ROOT, 'textAudio')
                os.makedirs(audio_dir, exist_ok=True)
                audio_filename = f"{new_text.id}.mp3"
                audio_path = os.path.join(audio_dir, audio_filename)
                audio = gTTS(text=form.cleaned_data["text"], lang=new_text.language.code)
                audio.save(audio_path)
                new_text.audio.name = os.path.join('textAudio', audio_filename)
            new_text.save()
            return redirect("leap:text", text_id=new_text.pk)
    return render(request, "LanguageLeap/upload_text.html", {"form": form})


class TranslateWord(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, text_id, paragraph, word_number):
        try:
            word_object = Word.objects.get(text_id=text_id, paragraph=paragraph, word_in_paragraph=word_number)
        except Word.DoesNotExist:
            text = get_object_or_404(Text, pk=text_id)
            try:
                word = text.get_word(paragraph, word_number)
            except:
                raise Http404()
            print("new word:", word)
            word_object = Word(text_id=text_id, paragraph=paragraph, word_in_paragraph=word_number)
            api_key = os.environ["MISTRAL_API_KEY"]
            model = "mistral-large-latest"
            client = Mistral(api_key=api_key)

            class Responce(BaseModel):
                word: str = Field(description="Исходное слово в начальной форме или выражение")
                translation: str = Field(description="перевод слова или выражения на русский язык")
                definition: str = Field(
                    description=f"объяснение заначения слова на исходном языке ({request.user.profile.language.name})")
                definition_translation: str = Field(description="перевод объяснения значения на русский язык")
                synonyms: Optional[List[str]] = Field(description="список из трех синонимов слова")
                antonyms: Optional[List[str]] = Field(description="список из трех антонимов слова")
                example: str = Field(description="пример использования исходного слова в предложении")
                example_translation: str = Field(description="перевод примера использования на русский")

            prompt = f"""
            ты являешься учителем иностранного языка ({request.user.profile.language.name}). твоя задача объяснить ученику значение слова {word} в контексте (слово {word} - {word_number + 1} слово в абзаце): 
            {" ".join(text.get_paragraph(paragraph))}
            в ответе выведи: 
            1.исходное слово, если слово является частью фразеологизма или другого неразрывного выражения напиши все выражение, если слово находится не в начальной форме приведи его в начальную форму
            2. перевод слова или выражения из первого пункта на русский язык с учетом контекста
            3. определение(объяснение) слова или выражение из первого пункта на исходном языке ({request.user.profile.language.name}), понятное ученику
            4. перевод определения из 3 пункта на русский язык
            5. если можешь приведи список из 3 синонимов к слову или выражению из 1 пункта(синоним также может быть словом или выражением)
            6. если можешь приведи список из 3 антонимов к слову или выражению из 1 пункта(антоним также может быть словом или выражением)
            7. пример использования слова или выражения из 1 пункта в предложении (слово или выражения не обязательно должно быть в начальной форме)
            8. перевод примера из пункта 7 на русский язык
            в ответе не используй выделений (жирный шрифт, курсив и т.д.).
            """

            for attempt in range(3):
                try:
                    chat_response = client.chat.parse(
                        model=model,
                        messages=[

                            {
                                "role": "user",
                                "content": prompt
                            },
                        ],
                        response_format=Responce,

                    )
                    response = chat_response.choices[0].message.parsed
                    print(f"attempt {attempt + 1} succeeded")
                    break

                except Exception as e:
                    print(f"attempt {attempt + 1} failed")
                    print(e)

            word_object.word = response.word
            word_object.translation = response.translation
            word_object.definition = response.definition
            word_object.definition_translation = response.definition_translation
            word_object.synonyms = response.synonyms or None
            word_object.antonyms = response.antonyms or None
            word_object.example = response.example
            word_object.example_translation = response.example_translation

            audio_dir = os.path.join(settings.MEDIA_ROOT, 'wordAudio')
            os.makedirs(audio_dir, exist_ok=True)
            audio_filename = f"{word_object.text.id}-{word_object.paragraph}-{word_object.word_in_paragraph}.mp3"
            audio_path = os.path.join(audio_dir, audio_filename)
            audio = gTTS(text=word_object.word, lang=text.language.code)
            audio.save(audio_path)
            word_object.audio.name = os.path.join('wordAudio', audio_filename)

            word_object.save()

        saved_word = SavedWord()
        saved_word.word = word_object
        saved_word.user = request.user
        saved_word.knowledge_degree_id = 1
        saved_word.next_rep = datetime.now()
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
            print("found")
            at.plus_one()
        except:
            at = ActivityTracker(user=saved_word.user)
            print("not found")
            at.save()

        if saved_word.knowledge_degree_id == 6:
            saved_word.knowledge_degree_id = 7
            saved_word.next_rep = None
            saved_word.learned_date = timezone.now().date()

        else:
            saved_word.knowledge_degree_id += 1
            saved_word.next_rep = timezone.now() + saved_word.knowledge_degree.duration
    else:
        saved_word.knowledge_degree_id = (saved_word.knowledge_degree_id + 1) // 2
        saved_word.next_rep = timezone.now()
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
    except:
        saved_text = SavedText()
        saved_text.user = request.user
        saved_text.text_id = text_id
        saved_text.status_id = status
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
    known_words_counter = SavedWord.objects.filter(user=user, knowledge_degree__id=7).values('learned_date').annotate(
        num_words=Count("id")).order_by("learned_date")
    saved_words_counter = SavedWord.objects.filter(user=user).values('creation_date').annotate(
        num_words=Count("id")).order_by(
        "creation_date")
    sum_words = 0
    known_words_response = []
    for date in known_words_counter:
        sum_words += date['num_words']
        known_words_response.append({'x': str(date['learned_date']), 'y': sum_words})
    sum_words = 0
    saved_words_response = []
    for date in saved_words_counter:
        sum_words += date['num_words']
        saved_words_response.append({'x': str(date['creation_date']), 'y': sum_words})
    friends = user.friends_as_user.all()
    table = [[user.id, user.username + " 💎", user.profile.user_stats['words_learned'],
              user.profile.user_stats['words_saved'], user.profile.user_stats['activity_count']]]
    for friend in friends:
        table.append([friend.friend.id, friend.friend.username, friend.friend.profile.user_stats['words_learned'],
                      friend.friend.profile.user_stats['words_saved'],
                      friend.friend.profile.user_stats['activity_count']])
    my_page = False
    if user == request.user:
        my_page = True
    my_friend = False
    if request.user.is_authenticated:
        if Friends.objects.filter(user_id=request.user.id, friend_id=user.id):
            my_friend = True
    return render(request, "LanguageLeap/user_page.html",
                  {"user": user, 'known_words': known_words_response, 'saved_words': saved_words_response,
                   'table': table, "my_page": my_page, "my_friend": my_friend})


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
    if "rows" in request.GET:
        rows = request.GET['rows']
        words = SavedWord.objects.filter(user=request.user).order_by('creation_date', 'id')
        new_last_export_size = len(words)
        last_export = LastExport.objects.filter(user=request.user)
        if not last_export:
            last_export = LastExport(user=request.user)
            last_export.save()
        else:
            last_export = last_export[0]
        if rows == 'new':
            words = words[last_export.last_export_size:]

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="words.csv"'},
        )

        writer = csv.writer(response, delimiter='\t')

        header = []
        if 'col_date' in request.GET:
            header.append("Дата добавления")
        if 'col_text_name' in request.GET:
            header.append("Название текста")
        if 'col_word' in request.GET:
            header.append("Слово")
        if 'col_translation' in request.GET:
            header.append("Перевод")
        if 'col_example' in request.GET:
            header.append("Пример")
        if 'col_example_translation' in request.GET:
            header.append("Перевод примера")
        if 'col_definition' in request.GET:
            header.append("Пояснение")
        if 'col_definition_translation' in request.GET:
            header.append("Перевод пояснения")
        if 'col_synonyms' in request.GET:
            header.append("Синонимы")
        if 'col_antonyms' in request.GET:
            header.append("Антонимы")
        writer.writerow(header)
        for word in words:
            row = []
            if 'col_date' in request.GET:
                row.append(word.creation_date)
            if 'col_text_name' in request.GET:
                row.append(word.word.text.name)
            if 'col_word' in request.GET:
                row.append(word.word.word)
            if 'col_translation' in request.GET:
                row.append(word.word.translation)
            if 'col_example' in request.GET:
                row.append(word.word.example)
            if 'col_example_translation' in request.GET:
                row.append(word.word.example_translation)
            if 'col_definition' in request.GET:
                row.append(word.word.definition)
            if 'col_definition_translation' in request.GET:
                row.append(word.word.definition_translation)
            if 'col_synonyms' in request.GET:
                row.append(", ".join(word.word.synonyms))
            if 'col_antonyms' in request.GET:
                row.append(", ".join(word.word.antonyms))
            writer.writerow(row)
        last_export.last_export_size = new_last_export_size
        last_export.save()
        return response
    return render(request, "LanguageLeap/export.html")
