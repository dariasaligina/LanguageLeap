from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(SavedText)
admin.site.register(SavedWord)
admin.site.register(Word)
admin.site.register(Text)
admin.site.register(Profile)
admin.site.register(LanguageLevel)
admin.site.register(Language)
admin.site.register(KnowledgeDegree)