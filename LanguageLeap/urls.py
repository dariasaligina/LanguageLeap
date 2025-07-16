from django.urls import path

from . import views

app_name = "leap"
urlpatterns = [
    path("catalog/", views.catalog, name="catalog"),
    path("register/", views.user_registration, name = "register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("text/<int:text_id>/", views.text, name = "text"),
    path("upload_text", views.upload_text, name = "upload_text"),
    path("translate_word/<slug:language_code>/<slug:word>", views.translate_word, name="translate_word"),
    path("learn/", views.learn_page, name = 'learn'),
    path("saved_word_update/<int:id>/<int:is_correct>",views.saved_word_update,name="saved_word_update"),
    path("profile", views.my_profile, name="my_profile"),
    path("delete_text/<int:text_id>/", views.delete_text, name="delete_text"),
    path("update_text_status/<int:text_id>/<slug:button_name>", views.update_text_status, name="update_text_status"),
]