import csv
import os

from django import forms
from django.contrib.auth.models import User
from django.forms import ModelForm
from django.http import HttpResponse
from gtts import gTTS

from mysite import settings
from .models import Text, Profile, Language, SavedWord, LastExport


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
            new_text.save()
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


class ExportForm(forms.Form):
    """Форма для экспорта слов с выбором колонок"""

    col_date = forms.BooleanField(
        required=False,
        label="Дата добавления",
        initial=False
    )
    col_text_name = forms.BooleanField(
        required=False,
        label="Название текста",
        initial=False
    )
    col_word = forms.BooleanField(
        required=False,
        label="Слово",
        initial=True
    )
    col_translation = forms.BooleanField(
        required=False,
        label="Перевод",
        initial=True
    )
    col_example = forms.BooleanField(
        required=False,
        label="Пример",
        initial=True
    )
    col_example_translation = forms.BooleanField(
        required=False,
        label="Перевод примера",
        initial=True
    )
    col_definition = forms.BooleanField(
        required=False,
        label="Пояснение",
        initial=False
    )
    col_definition_translation = forms.BooleanField(
        required=False,
        label="Перевод пояснения",
        initial=False
    )
    col_synonyms = forms.BooleanField(
        required=False,
        label="Синонимы",
        initial=False
    )
    col_antonyms = forms.BooleanField(
        required=False,
        label="Антонимы",
        initial=False
    )

    EXPORT_CHOICES = [
        ('all', 'Все слова'),
        ('new', 'Только новые слова'),
    ]
    rows = forms.ChoiceField(
        choices=EXPORT_CHOICES,
        widget=forms.RadioSelect,
        initial='all',
        label="Экспортировать",

    )

    def get_header(self):
        """Возвращает заголовок CSV на основе выбранных полей"""
        header = []
        field_labels = {
            'col_date': "Дата добавления",
            'col_text_name': "Название текста",
            'col_word': "Слово",
            'col_translation': "Перевод",
            'col_example': "Пример",
            'col_example_translation': "Перевод примера",
            'col_definition': "Пояснение",
            'col_definition_translation': "Перевод пояснения",
            'col_synonyms': "Синонимы",
            'col_antonyms': "Антонимы",
        }
        for field_name, label in field_labels.items():
            if self.cleaned_data.get(field_name):
                header.append(label)

        return header

    def get_row_data(self, word):
        """Возвращает строку данных для конкретного слова"""
        row = []
        field_mapping = {
            'col_date': lambda w: w.creation_date,
            'col_text_name': lambda w: w.word.text.name,
            'col_word': lambda w: w.word.word,
            'col_translation': lambda w: w.word.translation,
            'col_example': lambda w: w.word.example,
            'col_example_translation': lambda w: w.word.example_translation,
            'col_definition': lambda w: w.word.definition,
            'col_definition_translation': lambda w: w.word.definition_translation,
            'col_synonyms': lambda w: ", ".join(w.word.synonyms) if w.word.synonyms else "",
            'col_antonyms': lambda w: ", ".join(w.word.antonyms) if w.word.antonyms else "",
        }
        for field_name, getter in field_mapping.items():
            if self.cleaned_data.get(field_name):
                row.append(getter(word))

        return row

    def export_to_csv(self, user):
        """Выполняет экспорт и возвращает HttpResponse"""
        words = SavedWord.get_ordered_words_for_user(user.id)
        rows_type = self.cleaned_data['rows']
        last_export, created = LastExport.objects.get_or_create(user=user)
        new_export_size = words.count()
        if rows_type == 'new':
            words = words[last_export.last_export_size:]
        last_export.last_export_size = new_export_size
        last_export.save()
        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="words.csv"'},
        )
        writer = csv.writer(response, delimiter='\t')
        writer.writerow(self.get_header())
        for word in words:
            writer.writerow(self.get_row_data(word))
        return response


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'avatar', 'language']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Расскажите о себе...'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'bio': 'О себе',
            'avatar': 'Аватар',
            'language': 'Язык',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].required = False
        self.fields['bio'].widget.attrs.update({'class': 'form-control'})
