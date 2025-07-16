import string

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import authenticate, login, logout

from mysite import settings
from .models import Text, LanguageLevel, Language, Profile, Word, SavedWord, SavedText
from django.views.decorators.csrf import csrf_protect
from .forms import RegistrationForm, TextForm
from gtts import gTTS
from datetime import datetime
import os
from PyMultiDictionary import MultiDictionary
from translate import Translator
from nltk.stem import WordNetLemmatizer
from django.utils import timezone
from datetime import timedelta


# Create your views here.
def catalog(request):
    texts = Text.objects.filter(public=True)
    if request.user.is_authenticated:
        texts = texts.filter(language_id=request.user.profile.language_id)
    language_levels = LanguageLevel.objects.all()
    form_values = {"searchField": "",
                   "minLevel": 1,
                   "maxLevel": 6}
    if request.GET:
        form_values["searchField"] = request.GET["searchField"]
        form_values["minLevel"] = int(request.GET["minLevel"])
        form_values["maxLevel"] = int(request.GET["maxLevel"])
        if form_values['searchField']:
            texts = texts.filter(text__icontains=form_values['searchField']) | texts.filter(
                name__icontains=form_values['searchField'])
        texts = texts.filter(language_level_id__gte=form_values["minLevel"],
                             language_level_id__lte=form_values["maxLevel"])

    return render(request, "LanguageLeap/catalog.html", {
        "texts": texts,
        "language_levels": language_levels,
        "form_values": form_values,
    })


@csrf_protect
def user_registration(request):
    languages = Language.objects.all()
    form = RegistrationForm()

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            language = request.POST["language"]
            user = User.objects.create_user(username, email, password)
            user.save()
            profile = Profile(language_id=language, user=user)
            profile.save()
            login(request, user)
            return redirect("leap:catalog")

    return render(request, "LanguageLeap/registration.html", {
        "languages": languages,
        "form": form,
    })


@csrf_protect
def user_login(request):
    errors = []
    if request.POST:
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("leap:catalog")
        else:
            errors.append("Неправильное имя или пароль")
    return render(request, "LanguageLeap/login.html", {"errors": errors})


def user_logout(request):
    logout(request)
    return redirect("leap:login")


def filter_words(user, text):
    words_in_text = text.text.split()
    set_of_words = set()
    for word in words_in_text:
        set_of_words.add(word.lower().strip(string.punctuation + '\n\r '))
    saved_words = user.savedword_set.order_by("word__word")
    filtered_words = []
    for word in saved_words:
        if word.word.word in set_of_words:
            filtered_words.append(word.word)
    return filtered_words


@login_required
def text(request, text_id):
    text = get_object_or_404(Text, pk=text_id)
    words = filter_words(request.user, text)

    try:
        saved_text = SavedText.objects.get(user = request.user, text= text)
        text_status = saved_text.status.id
    except:
        text_status = 0

    return render(request, "LanguageLeap/text.html", {"text": text, "words": words, "text_status":text_status})


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
            else:
                new_text.image.name = "textImage/book.jpg"
            if form.cleaned_data["audio"]:
                new_text.audio = form.cleaned_data["audio"]
            else:
                new_text.save()
                audio_dir = os.path.join(settings.MEDIA_ROOT, 'textAudio')
                os.makedirs(audio_dir, exist_ok=True)  # Создаем директорию, если ее нет
                audio_filename = f"{new_text.id}.mp3"
                audio_path = os.path.join(audio_dir, audio_filename)
                audio = gTTS(text=form.cleaned_data["text"], lang=new_text.language.code)
                audio.save(audio_path)
                # Устанавливаем путь к аудиофайлу относительно MEDIA_ROOT
                new_text.audio.name = os.path.join('textAudio', audio_filename)
            new_text.save()
            return redirect("leap:text", text_id=new_text.pk)
    return render(request, "LanguageLeap/upload_text.html", {"form": form})


@login_required
def translate_word(request, language_code, word):
    language_object = get_object_or_404(Language, code=language_code)
    try:
        word_object = Word.objects.get(word=word, language=language_object)
    except Word.DoesNotExist:
        word_object = Word()
        word_object.word = word
        word_object.language = language_object

        audio_dir = os.path.join(settings.MEDIA_ROOT, 'wordAudio')
        os.makedirs(audio_dir, exist_ok=True)
        audio_filename = f"{word}-{language_code}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        audio = gTTS(text=word, lang=language_code)
        audio.save(audio_path)
        word_object.audio.name = os.path.join('wordAudio', audio_filename)

        dictionary = MultiDictionary()
        lemmatizer = WordNetLemmatizer()

        meanings = dictionary.meaning(language_code, lemmatizer.lemmatize(word))[1]

        translator = Translator(to_lang="ru", from_lang=language_code)
        translation = translator.translate(word)

        word_object.response = {"translation": translation, "meaning": meanings}
        word_object.save()
    try:
        saved_word = SavedWord.objects.get(word=word_object, user=request.user)
    except SavedWord.DoesNotExist:
        saved_word = SavedWord()
        saved_word.word = word_object
        saved_word.user = request.user
    saved_word.knowledge_degree_id = 1
    saved_word.next_rep = datetime.now()
    saved_word.save()
    word_data = {
        "word": word,
        "response": word_object.response
    }

    return JsonResponse(word_data)


@login_required
def learn_page(request):
    saved_words = request.user.savedword_set.filter(next_rep__lt=datetime.now())
    all_words = request.user.savedword_set.all()

    return render(request, "LanguageLeap/learn.html", {"words" : saved_words, "all_words":all_words})


def saved_word_update(request, id, is_correct):
    print("saved_word_update", id, is_correct)
    saved_word = get_object_or_404(SavedWord, id=id)
    if is_correct:
        if saved_word.knowledge_degree_id == 6:
            saved_word.delete()
            return JsonResponse({"saved_word": "deleted"})
        else:
            saved_word.knowledge_degree_id += 1
            saved_word.next_rep = timezone.now() + saved_word.knowledge_degree.duration
    else:
        saved_word.knowledge_degree_id = (saved_word.knowledge_degree_id+1)//2
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
        "user":user,
        "my_texts":my_texts,
        "completed_texts": completed_texts,
        "current_texts":current_texts,
        "future_texts":future_texts,
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
        saved_text = SavedText.objects.get(user = request.user, text_id = text_id)
        if (saved_text.status.id == status):
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

    return redirect("leap:text", text_id = text_id)