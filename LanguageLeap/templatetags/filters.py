import string

from django import template

register = template.Library()


@register.filter
def strip_punctuation(value):
    return value.strip(string.punctuation + '\n\r ')
