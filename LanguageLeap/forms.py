from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm

from .models import Text, Profile, Language


class RegistrationForm(forms.Form):
    language = forms.ModelChoiceField(
        queryset=Language.objects.all(),
        required=True,
        label="Язык обучения"
    )
    username = forms.CharField(label="Имя пользователя", max_length=100)
    email = forms.CharField(widget=forms.EmailInput)
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Повторите пароль")

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Пользователь с данным именем уже существует")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с данным email уже существует")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Пароли должны совпадать")

        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        Profile.objects.create(user=user, language=self.cleaned_data['language'])
        return user


class TextForm(ModelForm):
    class Meta:
        model = Text
        fields = ["name", "text", "language", "language_level", "public", "image", "audio"]


class CatalogFilterForm(forms.Form):
    searchField = forms.CharField(required=False, initial="")
    minLevel = forms.IntegerField(initial=1, min_value=1, max_value=6)
    maxLevel = forms.IntegerField(initial=6, min_value=1, max_value=6)
