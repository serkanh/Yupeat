from django.views.generic.simple import direct_to_template
from django.conf.urls.defaults import *
from views import *

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    #(r'^api/', include('api.urls')),
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),
    
    url('^$', main, name='main'),
    #url('^v/(?P<template_id>\d+)/$', ab, name='ab'),
    url('^signup/(?P<city>\w+)/$', signup, name='signup'),
    url('^thanks/$', direct_to_template, {'template': 'thanks.html'}),
    
    (r'^pricing/$',direct_to_template, {'template': 'footer/pricing.html'}),
    (r'^faq/$',direct_to_template, {'template': 'footer/faq.html'}),
    (r'^terms/$',direct_to_template, {'template': 'footer/terms.html'}),
    (r'^privacy/$',direct_to_template, {'template': 'footer/privacy.html'}),
    
    url(r'^ajax/vote/filter/$',ajax_vote_filter,name='ajax_vote_filter'),
    url(r'^ajax/vote/$',ajax_vote,name='ajax_vote'),
    
    url(r'^vote/$', vote, name='vote'),
    url(r'^what/$', what, name='what'),
    
    url(r'^about/buy-button/$', buybutton, name='aboutus'),
    url(r'^about/$', aboutus, name='aboutus'),
    
    (r'^gifts/', include('gifts.urls')),
    
    (r'^items/', include('items.urls')),
    (r'^order/', include('commerce.urls')),
    (r'^meals/', include('meals.urls')),
    (r'^profile/', include('uprofile.urls')),
    (r'^cdn/', include('cdn.urls')),
    (r'^api/', include('api.urls')),
    (r'^ppipn/', include('paypal.standard.ipn.urls')),
   #Ajax
   url('^ajax/location/$', saveLocation, name='saveLocation'),
   #Ajax
   url('^ajax/ip/$', saveIP, name='saveIP'),
   
)
