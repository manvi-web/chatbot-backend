from django import template

register = template.Library()

@register.filter
def replace_Name(value):
    if "parallelcluster" in value:
        value = value.replace("parallelcluster","pc")
        value = value.replace("ctx-numen-","")
    else:
        value = value.replace("ctx-numen-","")
    return value

@register.filter
def set_userName(value):
    value = value.split("@")
    value = value[0].split(".")
    return value[0].capitalize()

register.filter('replace_Name', replace_Name)
register.filter('set_userName', set_userName)