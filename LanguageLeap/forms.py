import os

from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from gtts import gTTS

from mysite import settings
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

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        new_text = Text()
        new_text.user = self.user
        new_text.name = self.cleaned_data["name"]
        new_text.text = self.cleaned_data["text"]
        new_text.language = self.cleaned_data["language"]
        new_text.language_level = self.cleaned_data["language_level"]
        new_text.public = self.cleaned_data["public"]
        if self.cleaned_data.get("image"):
            new_text.image = self.cleaned_data["image"]
        else:
            new_text.image = "textImage/book.jpg"

        if self.cleaned_data.get("audio"):
            new_text.audio = self.cleaned_data["audio"]
        else:
            new_text.audio = self._generate_audio(new_text.pk, new_text.language.code)
        new_text.save()
        return new_text.pk

    def _generate_audio(self, text_id, language_code):
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'textAudio')
        os.makedirs(audio_dir, exist_ok=True)
        audio_filename = f"{text_id}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        audio = gTTS(text=self.cleaned_data["text"], lang=language_code)
        audio.save(audio_path)
        return audio_path


class CatalogFilterForm(forms.Form):
    searchField = forms.CharField(required=False, initial="")
    minLevel = forms.IntegerField(initial=1, min_value=1, max_value=6)
    maxLevel = forms.IntegerField(initial=6, min_value=1, max_value=6)
