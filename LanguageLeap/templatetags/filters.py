from django import template

import string

register = template.Library()


@register.filter
def strip_punctuation(value):
    return value.strip(string.punctuation)
