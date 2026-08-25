from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Enables {{ my_dict|get_item:dynamic_key }} in templates."""
    if not dictionary:
        return ""
    return dictionary.get(key, "")
