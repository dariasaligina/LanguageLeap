from django.contrib.auth.forms import UserCreationForm
from django.contrib.postgres.search import SearchVector
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth import authenticate, login, logout
from .models import Text, LanguageLevel, Language
from django.views.decorators.csrf import csrf_protect


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


    if (request.POST):
        pass

    return render(request, "LanguageLeap/registration.html", {
        "languages":languages,
    })


@csrf_protect
def user_login(request):
    if request.POST:
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("leap:catalog")
    return render(request, "LanguageLeap/login.html")




def user_logout(request):
    logout(request)
    return redirect("leap:login")

