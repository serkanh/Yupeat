from commerce.models import Store

from django import forms
from gmapi import maps
from gmapi.forms.widgets import GoogleMap
from geopy import geocoders

"""
Used to display map on order form
"""
class LargeMapForm(forms.Form):
    map = forms.Field(widget=GoogleMap(attrs={'width':400, 'height':250}))

class MapForm(forms.Form):
    map = forms.Field(widget=GoogleMap(attrs={'width':250, 'height':150}))

"""Single Marker"""
def getMap(lat,lng, largeMap=False, zoomControl=False, panControl=False):
    gmap = maps.Map(opts = {
        'center': maps.LatLng(lat, lng),
        'mapTypeId': maps.MapTypeId.ROADMAP,
        'zoom': 15,
        'zoomControl': zoomControl,
        'panControl':panControl,
        'scrollwheel': False,
        'mapTypeControl': False,
        'streetViewControl': False,
    })
    
    marker = maps.Marker(opts = {
        'map': gmap,
        'position': maps.LatLng(lat, lng),
    })
    
    if largeMap:
        return LargeMapForm(initial={'map': gmap})
    else:
        return MapForm(initial={'map': gmap})

"""Multiple marker"""
def getMapMulti(locations, city, state, largeMap=False, zoomControl=False, panControl=False):
    
    store = Store.objects.filter(city=city, active=False)[0]
    center_lat = float(store.lat)
    center_lng = float(store.lng)
    
    gmap = maps.Map(opts = {
        'center': maps.LatLng(center_lat, center_lng),
        'mapTypeId': maps.MapTypeId.ROADMAP,
        'zoom': 12,
        'zoomControl': zoomControl,
        'panControl':panControl,
        'scrollwheel': False,
        'mapTypeControl': False,
        'streetViewControl': False,
    })
    
    for loc in locations:
        lat = loc[0]
        lng = loc[1]
        marker = maps.Marker(opts = {
            'map': gmap,
            'position': maps.LatLng(lat, lng),
        })
    
    if largeMap:
        return LargeMapForm(initial={'map': gmap})
    else:
        return MapForm(initial={'map': gmap})