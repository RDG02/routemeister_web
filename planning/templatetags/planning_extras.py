from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter om een waarde uit een dictionary te halen met een key
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key, '')
    elif dictionary and hasattr(dictionary, '__getitem__'):
        try:
            return dictionary[key]
        except (KeyError, IndexError, TypeError):
            return ''
    return ''
