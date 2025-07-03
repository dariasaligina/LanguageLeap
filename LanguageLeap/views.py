from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import authenticate, login, logout
from .models import Text, LanguageLevel, Language, Profile
from django.views.decorators.csrf import csrf_protect
from .forms import RegistrationForm


# Create your views here.
def catalog(request):
    texts = Text.objects.filter(public = True)
    if request.user.is_authenticated:
        texts = texts.filter(language_id = request.user.profile.language_id)
    language_levels = LanguageLevel.objects.all()
    form_values = {"searchField": "",
                   "minLevel": 1,
                   "maxLevel": 6}
    if request.GET:
        form_values["searchField"] = request.GET["searchField"]
        form_values["minLevel"] = int(request.GET["minLevel"])
        form_values["maxLevel"] = int(request.GET["maxLevel"])
        if form_values['searchField']:
            texts = texts.filter(text__icontains=form_values['searchField']) | texts.filter(name__icontains=form_values['searchField'])
        texts = texts.filter(language_level_id__gte=form_values["minLevel"], language_level_id__lte=form_values["maxLevel"])

    return render(request, "LanguageLeap/catalog.html", {
        "texts": texts,
        "language_levels": language_levels,
        "form_values": form_values,
    })


@csrf_protect
def user_registration(request):
    languages = Language.objects.all()
    form = RegistrationForm()

    if (request.method == "POST"):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            language = request.POST["language"]
            user = User.objects.create_user(username, email,password)
            user.save()
            profile = Profile(language_id = language, user=user)
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
    return render(request, "LanguageLeap/login.html", {"errors":errors})




def user_logout(request):
    logout(request)
    return redirect("leap:login")

