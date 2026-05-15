from django.urls import path

from . import views

app_name = "leap"
urlpatterns = [
    path("catalog/", views.catalog, name="catalog"),
    path("register/", views.user_registration, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("text/<int:text_id>/", views.text, name="text"),
    path("upload_text", views.upload_text, name="upload_text"),
    path("translate_word/<int:text_id>/<int:paragraph>/<int:word_number>", views.TranslateWord.as_view(),
         name="translate_word"),
    path("learn/", views.learn_page, name='learn'),
    path("saved_word_update/<int:id>/<int:is_correct>", views.saved_word_update, name="saved_word_update"),
    path("saves", views.my_profile, name="my_profile"),
    path("delete_text/<int:text_id>/", views.delete_text, name="delete_text"),
    path("update_text_status/<int:text_id>/<slug:button_name>", views.update_text_status, name="update_text_status"),
    path("get_heatmap_data/<int:user_id>/", views.get_heatmap_data, name="get_heatmap_data"),
    path("user_page/<int:user_id>", views.user_page, name="user_page"),
    path("add_friend/<int:friend_id>", views.add_friend, name='add_friend'),
    path("delete_friend/<int:friend_id>", views.delete_friend, name='delete_friend'),
    path("popular/", views.popular, name='popular'),
    path("export/", views.export, name="export"),
]
