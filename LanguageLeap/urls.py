from django.urls import path

from . import views

app_name = "leap"
urlpatterns = [
    path("catalog/", views.catalog, name="catalog"),

]