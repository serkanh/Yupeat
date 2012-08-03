from django import template
from urlparse import urlparse

register = template.Library()

@register.filter(name='promo_meal')
def promo_meal(arg, value):
    if arg in value:
        return value[arg]
    else:
        return ''
    
@register.filter(name='city_to_id')
def city_to_id(value):
    {'San Francisco':0,'Vancouver':1}
    if arg in value:
        return value[arg]
    else:
        return ''

@register.filter(name='percentage')
def percentage(decimal):
    return "%d%%" % (decimal*100)

@register.filter(name='cents_to_dollars')
def cents_to_dollars(cents):
    return "%.2f" % (cents/100)