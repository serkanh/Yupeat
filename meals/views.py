from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import simplejson

from meals.models import Recipe
from uprofile.views import getUser
from uprofile.models import UserProfile

from google.appengine.api import images
from django.contrib.auth.models import User
import base64

import logging

"""
Used to display recipe details 'recipes/details' page
"""
def details(request,recipe_id):
    
    user = getUser(request)
    if user:
        up = UserProfile.objects.get(user=user)
        
        """Get users current city"""
        store = up.default_store
        c = store.city
        city = c.lower().replace(' ','')
    else:
        city = None
        
    r = Recipe.objects.get(id=recipe_id)
    
    ingrlist = r.ingrfull.split('\n') 
    dirlist = r.dirfull.split('\n')
    
    image_key = str(r.image.file.blobstore_info.key())
    url = images.get_serving_url(image_key)
    
    template = "meals/detail.html"
    data = {'recipe':r, 'directions':dirlist, 'ingredients':ingrlist, 
            'image':url, 'user':user, 'city':city}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

