from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from .models import Text


class RegistrationForm(forms.Form):
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


class TextForm(ModelForm):
    class Meta:
        model = Text
        fields = ["name", "text", "language", "language_level", "public", "image", "audio"]

