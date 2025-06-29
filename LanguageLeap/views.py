from django.contrib.postgres.search import SearchVector
from django.shortcuts import render
from .models import Text, LanguageLevel

# Create your views here.
def catalog(request):

    texts = Text.objects.all()
    language_levels = LanguageLevel.objects.all()
    form_values = {"searchField": "",
                   "minLevel": 1,
                   "maxLevel": 6}
    if request.GET:
        form_values["searchField"] = request.GET["searchField"]
        form_values["minLevel"] = int(request.GET["minLevel"])
        form_values["maxLevel"] = int(request.GET["maxLevel"])
        if form_values['searchField']:
            texts = Text.objects.filter(text__icontains=form_values['searchField']) | texts.filter(name__icontains=form_values['searchField'])


        texts = texts.filter(language_level_id__gte=form_values["minLevel"], language_level_id__lte=form_values["maxLevel"])

    return render(request, "LanguageLeap/catalog.html", {
        "texts": texts,
        "language_levels": language_levels,
        "form_values": form_values,
    })