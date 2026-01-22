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
    path("translate_word/<int:text_id>/<int:paragraph>/<int:word_number>", views.translate_word.as_view(), name="translate_word"),
    path("learn/", views.learn_page, name = 'learn'),
    path("saved_word_update/<int:id>/<int:is_correct>",views.saved_word_update,name="saved_word_update"),
    path("profile", views.my_profile, name="my_profile"),
    path("delete_text/<int:text_id>/", views.delete_text, name="delete_text"),
    path("update_text_status/<int:text_id>/<slug:button_name>", views.update_text_status, name="update_text_status"),
    path("json/catalog/", views.json_catalog, name="json_catalog"),
    path("api/learn", views.api_learn_page.as_view(), name="api_learn"),
    path("api/login", views.api_login, name="api_login"),
    path("api/profile", views.api_profile.as_view(), name="api_profile"),
    path("api/text/<int:text_id>/", views.api_text.as_view(), name= "api_text"),
    path("api/update_text_status/<int:text_id>/<int:status>", views.update_text_status_api.as_view(),
         name="api_update_text_status"),
    path("api/new_text", views.api_new_text.as_view(), name= "api_new_text"),
    path("api/register", views.api_register_user.as_view(), name="api_register"),
    path("get_heatmap_data/<slug:user_name>/", views.get_heatmap_data, name="get_heatmap_data")
]