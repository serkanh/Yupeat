from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse

from items.models import Item

import logging
from decimal import *

"""
Administrative functions
- Form for adding stores
- TODO: Add new stores 
"""

def admin_items(request):
    item_array = []
    
    if request.method == 'POST':
        new_items = request.POST.get('new_items')
        item_array = new_items.split('\r\n')
        for i in item_array:
            #logging.debug(i)
            try:
                iarray = i.split(',')
                item = Item(name=iarray[0].strip(),quantity=iarray[1].strip(),price=Decimal(iarray[2].strip()))
                item.save()
            except IndexError:
                pass
    template = 'items/admin/admin_item.html'
    data = {}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Displays all of items 
- TODO: Add checkbox to store meal  
"""
def admin_items_all(request):
    template = 'items/admin/admin_all.html'
    data = {'items':Item.objects.all()}
    
    return render_to_response(template, data,context_instance=RequestContext(request))