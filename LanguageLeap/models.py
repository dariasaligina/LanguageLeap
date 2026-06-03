import os
from datetime import datetime
from datetime import timedelta
from typing import List, Optional

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone
from gtts import gTTS
from mistralai.client import Mistral
from pydantic import BaseModel, Field

from mysite import settings


class Language(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    image = models.ImageField(upload_to="languages/")
    voice_name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


class LanguageLevel(models.Model):
    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class Text(models.Model):
    name = models.CharField(max_length=256)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    language_level = models.ForeignKey(LanguageLevel, blank=True, on_delete=models.PROTECT)
    text = models.TextField()
    audio = models.FileField(upload_to="textAudio/", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    public = models.BooleanField(default=False)
    image = models.ImageField(upload_to="textImage/", blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)

    @classmethod
    def catalog_filter(cls, form_values, user):
        texts = cls.objects.filter(public=True, language_level_id__gte=form_values["minLevel"],
                                   language_level_id__lte=form_values["maxLevel"])
        if form_values['searchField']:
            texts = texts.filter(text__icontains=form_values['searchField']) | texts.filter(
                name__icontains=form_values['searchField'])
        if user:
            texts = texts.filter(language_id=user.profile.language_id)
        return texts

    @property
    def split_text(self):
        txt = str(self.text)
        paragraph = list(txt.split("\n"))
        ans = list()
        for p in paragraph:
            ans.append(list(p.split(" ")))
        return ans

    @property
    def save_count(self):
        return self.savedtext_set.count()

    @property
    def saves_this_week(self):
        ts = timezone.now() - timedelta(days=7)
        return self.savedtext_set.filter(save_date__gte=ts).count()

    @property
    def saves_this_month(self):
        ts = timezone.now() - timedelta(days=30)
        return self.savedtext_set.filter(save_date__gte=ts).count()

    @property
    def saves_this_year(self):
        ts = timezone.now() - timedelta(days=365)
        return self.savedtext_set.filter(save_date__gte=ts).count()

    def get_paragraph(self, paragraph_number: int):
        return self.split_text[paragraph_number]

    def get_word(self, paragraph_number: int, word_number: int):
        return self.get_paragraph(paragraph_number)[word_number]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/user.png')
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    creation_date = models.DateTimeField(auto_now_add=True)

    @property
    def user_stats(self):
        words_learned = SavedWord.objects.filter(user=self.user, knowledge_degree__id=7).count()
        words_saved = SavedWord.objects.filter(user=self.user).count()

        last_week = timezone.now() - timedelta(days=7)
        activity = ActivityTracker.objects.filter(user=self.user, creation_date__gt=last_week).aggregate(
            Sum("counter", default=0))
        words_saved_last_week = SavedWord.objects.filter(user=self.user, creation_date__gt=last_week).count()
        return {
            'words_learned': words_learned,
            'words_saved': words_saved,
            'activity_count': activity['counter__sum'] + words_saved_last_week
        }

    def __str__(self):
        return self.user.username


class Word(models.Model):
    word = models.CharField(max_length=256)
    audio = models.FileField(upload_to="wordAudio/")

    translation = models.CharField(max_length=256)
    definition = models.TextField()
    definition_translation = models.TextField()
    synonyms = ArrayField(models.CharField(max_length=256), null=True)
    antonyms = ArrayField(models.CharField(max_length=256), null=True)
    example = models.TextField()
    example_translation = models.TextField()

    text = models.ForeignKey(Text, on_delete=models.PROTECT)
    paragraph = models.IntegerField()
    word_in_paragraph = models.IntegerField()

    def __str__(self):
        return self.word

    def init_by_api(self, text_id: int, paragraph: int, word_number: int):
        text = Text.objects.get(pk=text_id)
        word = text.get_word(paragraph, word_number)
        language_name = text.language.name
        self.text_id = text_id
        self.paragraph = paragraph
        self.word_in_paragraph = word_number

        api_key = os.environ["MISTRAL_API_KEY"]
        model = "mistral-large-latest"
        client = Mistral(api_key=api_key)

        class Responce(BaseModel):
            word: str = Field(description="Исходное слово в начальной форме или выражение")
            translation: str = Field(description="перевод слова или выражения на русский язык")
            definition: str = Field(
                description=f"объяснение заначения слова на исходном языке ({language_name})")
            definition_translation: str = Field(description="перевод объяснения значения на русский язык")
            synonyms: Optional[List[str]] = Field(description="список из трех синонимов слова")
            antonyms: Optional[List[str]] = Field(description="список из трех антонимов слова")
            example: str = Field(description="пример использования исходного слова в предложении")
            example_translation: str = Field(description="перевод примера использования на русский")

        prompt = f"""
                    ты являешься учителем иностранного языка ({language_name}). твоя задача объяснить ученику значение слова {word} в контексте (слово {word} - {word_number + 1} слово в абзаце): 
                    {" ".join(text.get_paragraph(paragraph))}
                    в ответе выведи: 
                    1.исходное слово, если слово является частью фразеологизма или другого неразрывного выражения напиши все выражение, если слово находится не в начальной форме приведи его в начальную форму
                    2. перевод слова или выражения из первого пункта на русский язык с учетом контекста
                    3. определение(объяснение) слова или выражение из первого пункта на исходном языке ({language_name}), понятное ученику
                    4. перевод определения из 3 пункта на русский язык
                    5. если можешь приведи список из 3 синонимов к слову или выражению из 1 пункта(синоним также может быть словом или выражением)
                    6. если можешь приведи список из 3 антонимов к слову или выражению из 1 пункта(антоним также может быть словом или выражением)
                    7. пример использования слова или выражения из 1 пункта в предложении (слово или выражения не обязательно должно быть в начальной форме)
                    8. перевод примера из пункта 7 на русский язык
                    в ответе не используй выделений (жирный шрифт, курсив и т.д.).
                    """

        for attempt in range(3):
            try:
                chat_response = client.chat.parse(
                    model=model,
                    messages=[

                        {
                            "role": "user",
                            "content": prompt
                        },
                    ],
                    response_format=Responce,

                )
                response = chat_response.choices[0].message.parsed
                print(f"attempt {attempt + 1} succeeded")
                break

            except Exception as e:
                print(f"attempt {attempt + 1} failed")
                print(e)

        self.word = response.word
        self.translation = response.translation
        self.definition = response.definition
        self.definition_translation = response.definition_translation
        self.synonyms = response.synonyms or None
        self.antonyms = response.antonyms or None
        self.example = response.example
        self.example_translation = response.example_translation
        self._init_audio()

    def _init_audio(self):
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'wordAudio')
        os.makedirs(audio_dir, exist_ok=True)
        audio_filename = f"{self.text.id}-{self.paragraph}-{self.word_in_paragraph}.mp3"
        audio_path = os.path.join(audio_dir, audio_filename)
        audio = gTTS(text=self.word, lang=self.text.language.code)
        audio.save(audio_path)
        self.audio.name = os.path.join('wordAudio', audio_filename)


class KnowledgeDegree(models.Model):
    duration = models.DurationField()


class SavedWord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.PROTECT)
    knowledge_degree = models.ForeignKey(KnowledgeDegree, on_delete=models.PROTECT, default=1)
    next_rep = models.DateTimeField(null=True, default=datetime.now)
    creation_date = models.DateField(auto_now_add=True)
    learned_date = models.DateTimeField(null=True)

    def correct_answer(self):
        if self.knowledge_degree_id == 6:
            self.knowledge_degree_id = 7
            self.next_rep = None
            self.learned_date = timezone.now().date()
        else:
            self.knowledge_degree_id += 1
            self.next_rep = timezone.now() + self.knowledge_degree.duration

    def wrong_answer(self):
        self.knowledge_degree_id = (self.knowledge_degree_id + 1) // 2
        self.next_rep = timezone.now()

    @classmethod
    def filter_words_from_text(cls, user_id: int, text_id: int):
        saved_words = cls.objects.filter(word__text_id=text_id, user_id=user_id).order_by("word__paragraph",
                                                                                          "word__word_in_paragraph")
        return saved_words

    @classmethod
    def get_ordered_words_for_user(cls, user_id: int):
        words = cls.objects.filter(
            user_id=user_id
        ).select_related('word', 'word__text').order_by('creation_date', 'id')
        return words

    def __str__(self):
        return self.word

    @classmethod
    def get_known_word_counter(cls, user_id: int):
        known_words_counter = cls.objects.filter(user_id=user_id, knowledge_degree__id=7).values(
            'learned_date').annotate(
            num_words=Count("id")).order_by("learned_date")
        return known_words_counter

    @classmethod
    def get_saved_word_counter(cls, user_id):
        saved_words_counter = SavedWord.objects.filter(user_id=user_id).values('creation_date').annotate(
            num_words=Count("id")).order_by(
            "creation_date")
        return saved_words_counter


class SavedTextStatus(models.Model):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name + " " + str(self.id)


class SavedText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.ForeignKey(Text, on_delete=models.CASCADE)
    save_date = models.DateTimeField(auto_now_add=True)
    status = models.ForeignKey(SavedTextStatus, on_delete=models.PROTECT)

    def __str__(self):
        return self.text.name


class ActivityTracker(models.Model):
    creation_date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    counter = models.IntegerField(default=1)

    def plus_one(self):
        self.counter += 1


class Friends(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends_as_user')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends_as_friend')


class LastExport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_export_size = models.IntegerField(default=0)
