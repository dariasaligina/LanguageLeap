from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.contrib.auth.models import User


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


    def get_paragraph(self, paragraph_number):


        return self.split_text[paragraph_number]


    def get_word(self, paragraph_number, word_number):

        return self.get_paragraph(paragraph_number)[word_number]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Word(models.Model):
    word = models.CharField(max_length=256)
    audio = models.FileField(upload_to="wordAudio/")

    translation = models.CharField(max_length=256)
    definition = models.TextField()
    synonyms = ArrayField(models.CharField(max_length=256), null=True)
    antonyms = ArrayField(models.CharField(max_length=256), null=True)

    text = models.ForeignKey(Text, on_delete=models.PROTECT)
    paragraph = models.IntegerField()
    word_in_paragraph = models.IntegerField()

    def __str__(self):
        return self.word


class KnowledgeDegree(models.Model):
    duration = models.DurationField()


class SavedWord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.PROTECT)
    knowledge_degree = models.ForeignKey(KnowledgeDegree, on_delete=models.PROTECT)
    next_rep = models.DateTimeField()
    creation_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.word


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

    @property
    def add(self):
        self.counter += 1
        self.save()


class KnownWord(models.Model):
    creation_date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.PROTECT)


class KnownWord(models.Model):
    creation_date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.PROTECT)


