import string

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def strip_punctuation(value):
    return value.strip(string.punctuation + '\n\r ')


@register.filter
def set_len(value, arg):
    if len(value) <= arg:
        value += ' &nbsp;' * ((arg - len(value)) // 2)
    else:
        value = value[:arg - 3] + "..."
    return mark_safe(value)
