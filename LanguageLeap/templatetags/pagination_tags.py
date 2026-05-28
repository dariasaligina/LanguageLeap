from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Заменяет или добавляет параметры в текущую строку GET-запроса.
    """

    d = context['request'].GET.copy()

    for k, v in kwargs.items():
        d[k] = v

    return d.urlencode()