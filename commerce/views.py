from __future__ import with_statement
from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core import serializers
from django.shortcuts import redirect, get_object_or_404

from django.contrib.sessions.models import Session
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test

from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.core.files.storage import default_storage

from django.views.decorators.csrf import csrf_exempt

from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.ipn.signals import payment_was_successful

from items.models import Item, ItemPriceHistory
from meals.models import Recipe
from meals.templatetags.meal_extras import url_cleanup

from cdn.models import CDN

from uprofile.models import *
from uprofile.views import getUser
from uprofile.forms import PartyGuestForm, DinnerPartyForm

from prospects.models import Prospect

from commerce.models import Store, CurrentPromo, PromoSchedule
from commerce.forms import * 

from itemparser.views import *

from filetransfers.api import prepare_upload
from django.core.urlresolvers import reverse

from geopy import geocoders
from django.conf import settings

from google.appengine.api import files
from google.appengine.ext import blobstore

from django import forms
from gmapi import maps
from gmapi.forms.widgets import GoogleMap
from mygeo.views import getMapMulti

from django.utils import simplejson
from django.utils.encoding import smart_unicode

from google.appengine.api import images

from pytz import timezone
from datetime import datetime, date, timedelta
from decimal import *
from py26math.fractions import Fraction

import operator
import logging
import stripe
import time
import string
import random
    
import base64

from contextlib import closing
import zipfile
import os
import shutil
import codecs
import StringIO
import re
import urllib2

from mailsnake import MailSnake
from beautifulsoup.BeautifulSoup import BeautifulSoup

CUSTOM_PROMO_SALT = 'GKLdh{mN39'

STORE_MARKUP = {'Whole Foods (Franklin)':0.15}

UNCHECKED_ITEMS = ['salt', 'ground-black-pepper','black-pepper', 'red-pepper-flakes', 
                   'ketchup','sugar','brown-sugar','vegetable-oil', 'soy-sauce',
                   'olive-oil', 'milk', 'butter', 'egg', 'curry-powder','cumin',
                   'mustard','cornmeal','onion-powder', 'flour','mayo', 'canola-oil'
                   'dijon-mustard', 'bread', 'tabasco', 'honey', 'vinegar', 'cooking-spray',
                   'paprika','cayenne-pepper', 'garlic-powder','chili-powder', 'coriander',
                   'cinnamon', 'canola-oil', 'mayonnaise', 'rice-vinegar', 'cornstarch',
                   'crushed-red-pepper']

US_CITY = ['sanfrancisco']

"""
Main view to render '/order' page
"""
def order(request, city=None, id=None):
    user = getUser(request)
    #disabled = afterDeadline()
    disabled = True

    not_subscribed=True
    subscribed = False
    if user:
        subscribed = isSubscriber(user)
        if not subscribed:
            not_subscribed=True
        else:
            not_subscribed = False
    
    """Get City"""
    city = getCity(request, city)
    
    us_city = False
    if city in US_CITY:
        us_city=True
    
    """Get a default store for city"""
    store = sub_to_store(city)
    
    CITY_DICT = {'sanfrancisco':'San Francisco', 'vancouver':'Vancouver'}
    store_city = CITY_DICT[city]
    store_all = Store.objects.filter(city=store_city, active=True)
    
    
    """Check for user designated store"""
    if user:
        try:
            user_profile = user.get_profile()
            store = user_profile.default_store 
        except UserProfile.DoesNotExist:
            user_profile = UserProfile(user=user, default_store=store)
            user_profile.save()
            store = user_profile.default_store
            
    if request.GET.get("store_id"):
        store_id = request.GET.get("store_id")
        store = Store.objects.get(id=int(store_id))
    
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    now_str = now.strftime('%d%m%y')
         
    form = AuthenticationForm()
    
    """Get Meal"""
    if oldMeal(city, id):
        return redirect('/meals/details/%s' % id) 
    
    selected_recipes, item_dict, total = getMeal(city, store, id)
    
    if not selected_recipes and not item_dict and not total:
        
        template = 'commerce/order_tbd.html'
        data = {'user':user}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
    
    """Create map"""
    mapForm = createMap(store)
        
    valid = False
    
    """Initialize excluded items"""
    excluded = UNCHECKED_ITEMS
    
    pickup_day = getDay()
    pickup_time = getTime(store)
    default_pickup_time = default_pickuptime(user,store)
    
    if request.POST and us_city:
        if request.POST.get('store_id'):
            store_id = int(request.POST.get('store_id'))
            store = Store.objects.get(id=store_id)
             
        pickup_time = getPickupTime(request,store)
        valid, error_msg, calc_total, purchased_items = submit_order(request, item_dict, total, city, pickup_time, store)
        
        if valid:
            recipe_id = selected_recipes[0].id
                
            request.session['_us_confirmed_order'] = {'store':store_id, 
                                                      'pickup_time':pickup_time, 
                                                      'recipe_id':recipe_id}
            
            data = {'pickup_time':pickup_time, 'pickup_day':pickup_day, 'map':mapForm, 'user':user,
                    'auth_form':form, 'store':store, 'recipes':selected_recipes, 
                    'city':city, 'items':purchased_items, 'recipe_id':recipe_id, 'charged':calc_total}
            
            confirmation_email(user, data, pickup_day)
            admin_alert_email(user,data,pickup_time)
            
            return redirect('/order/complete')
            #return render_to_response(template, data,context_instance=RequestContext(request))
    
    """Create image"""
    r = selected_recipes[0]
    image_key = str(r.image.file.blobstore_info.key())
    url = images.get_serving_url(image_key)
    
    """Handle payments"""    
    paypal = False
    if us_city:
        change_card, customer, payForm = us_checkout(request, user)
    else:
        cc_data = {'user':user, 'recipes':selected_recipes, 'pickup_day':pickup_day,
                'total':total, 'items':item_dict, 'store':store}
        change_card, customer, payForm = canada_checkout(request, cc_data)
        paypal = True
    
    """if not subscriber update total"""
    if not_subscribed:
        total += Decimal("3.99")
    
    template = 'commerce/order.html'
    data = {'store':store, 'store_all':store_all,'map':mapForm, 'payment':payForm, 'disabled':disabled,
            'items':item_dict, 'user':user, 'auth_form':form, 'now':now_str, 
            'not_subscribed':not_subscribed, 'subscribed':subscribed, 
            'recipes':selected_recipes, 'pickup_time':pickup_time, 'default_pickup_time':default_pickup_time,
            'image':url, 'day':pickup_day, 'total':total, 'city':city, 'excluded':excluded,
            'customer':customer, 'change_card':change_card, 'paypal':paypal}
        
    return render_to_response(template, data,context_instance=RequestContext(request))


"""return list of excluded items"""
def getExclude():
    return UNCHECKED_ITEMS

"""return pickup time from previous order"""
def default_pickuptime(user,store):
    default = 1
    if user:
        up = user.get_profile()
        oh = OrderHistory.objects.filter(userprofile=up)
        if len(oh) > 0:
            latest = len(oh)-1
            time = oh[latest].pickuptime
             
            if time:
                gt = getTime(store)
                default = gt.index(time)+1
    
    return default

"""return page for canceled order"""
def select_city(request):
    if request.POST:
        city = request.POST.get('select_city')
        request.session['city'] = city
        return HttpResponseRedirect('/order/%s' % str(city))
    
    city = [('sanfrancisco','San Francisco'), ('vancouver','Vancouver')]
    template = 'commerce/select_city.html'
    data = {'city':city}
    return render_to_response(template, data,context_instance=RequestContext(request))

"""return page for canceled order"""
def order_soldout(request):
    template = 'commerce/order_soldout.html'
    data = {}
    return render_to_response(template, data,context_instance=RequestContext(request))

"""return page for canceled order"""
def order_cancel(request):
    template = 'commerce/order_cancel.html'
    data = {}
    return render_to_response(template, data,context_instance=RequestContext(request))

"""return order popup page"""
def order_popup(request):
    user = getUser(request)
    
    disabled = False
    if user == None:
        disabled = True
         
    title = request.GET.get('title')
    url = request.GET.get('url')
    
    """Validate URL """
    url_array = []
    c_url = url_cleanup(url)
    eligible_urls = list(OrderEligibleSite.objects.values('url'))
    
    for e in eligible_urls: 
        url_array.append(e['url'])
    
    if c_url not in url_array:
        template = 'commerce/order_popup_ineligible.html'
        data = {'override':False, 'notice':''}
        return render_to_response(template, data,context_instance=RequestContext(request))
    
    n_url = 'http://rest.yupeat.beta.relishthedish.com/create-recipe?url=%s' % url 
    
    page = urllib2.urlopen(url)
    soup = BeautifulSoup(page)
    title = soup.html.head.title.text
    
    req = urllib2.Request(n_url)
    opener = urllib2.build_opener()
    f = opener.open(req)
    json = simplejson.load(f)
    
    price_check = []
    ingr_item_arr = []
    
    try:
        for ingr in json['ingrfull'][0]['ingredients']:
            si = structureIngredient()
            si.get_tokens(ingr)
            
            all_matches = si.row[0]['ingredient']  
            if len(all_matches) == 0:
                price_check.append(ingr)
            else:
                ingr_item_arr.append(all_matches[0])
    except KeyError:
        template = 'commerce/order_popup_ineligible.html'
        data = {'override':True, 'parseError':False}
        return render_to_response(template, data,context_instance=RequestContext(request))
    except AttributeError:
        template = 'commerce/order_popup_ineligible.html'
        data = {'override':True, 'parseError':True}
        return render_to_response(template, data,context_instance=RequestContext(request))
    items, total = price_helper(ingr_item_arr)
    
    form = AuthenticationForm()
    
    template = 'commerce/order_popup.html'
    data = {'items':items, 'price_check':price_check, 'total':total,
            'title':title, 'auth_form':form, 'user':user, 'disabled':disabled}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""helper function for retrieving latest price"""
def price_helper(all_ingr):
    item_dict = {}
    total = Decimal('0.00')
    
    for ic in all_ingr:
        item_obj = Item.objects.filter(name__exact=ic)
        if len(item_obj) > 0:
            
            #check for a more recent price for given item
            iph = ItemPriceHistory.objects.filter(item=item_obj[0])
            
            if len(iph) > 0:
                index_val = len(iph)-1
                item_dict[item_obj[0].name] = iph[index_val].price
                total += iph[index_val].price
                
            else:
                item_dict[item_obj[0].name] = item_obj[0].price
                total += item_obj[0].price
        else:
            item_dict[i.strip()] = 0.00
    
    return item_dict, total

"""return page for completed order"""
@csrf_exempt
def order_complete(request):
    template = 'commerce/order_complete.html'   
    data = {}
    if '_us_confirmed_order' in request.session:
        data = request.session.get('_us_confirmed_order')
        
        try:
            del request.session['_us_confirmed_order']
        except:
            pass
        
        """get store object"""
        store_id = data['store']
        store = Store.objects.get(id=int(store_id))
        
        #logging.debug(store.id)
        #logging.debug(store.store_name)
        
        """get recipe object"""
        recipe_id = data['recipe_id']
        recipe = Recipe.objects.get(id=int(recipe_id))
        
        """get map"""
        mapForm = createMap(store)
        
        data['map']=mapForm
        data['store']=store
        data['recipes'] = [recipe]
    else:
        charge_id = request.GET.get('order_id')
        st = SavedTransaction.objects.get(charge=charge_id)
        data = pp_decode_data(st.data)
        
        store = data['store']
        
        """get map"""
        mapForm = createMap(store)
        data['map'] = mapForm
        
        item_array = st.custom
        ia = item_array.replace('-',' ').split(',')
        
        time_array = getTime(store)
        pu_time = time_array[int(ia[0])-1]
        data['pickup_time'] = pu_time
           
    return render_to_response(template, data,context_instance=RequestContext(request))

"""creates a map"""
def createMap(store, largeMap=False, zoomControl=False, panControl=False):
    try:
        g = geocoders.Google(settings.GOOGLE_MAPS_API_KEY)
        location = '%s %s %s %s' % (store.street1, store.city, store.state, store.postal_code)
        
        lat = float(store.lat)
        lng = float(store.lng)
        
        mapForm = getMap(lat,lng, largeMap, zoomControl, panControl)
    except geocoders.google.GTooManyQueriesError:
        mapForm = None
        pass
        
    return mapForm

"""creates a map with multiple markers"""
def createMapMulti(store_all, city, state, largeMap=False, zoomControl=False, panControl=False):
    try:
        g = geocoders.Google(settings.GOOGLE_MAPS_API_KEY)
        location_all = []
        for store in store_all:
            location_all.append((float(store.lat),float(store.lng)))
        mapForm = getMapMulti(location_all, city, state, largeMap, zoomControl, panControl)
    except geocoders.google.GTooManyQueriesError:
        mapForm = None
        pass
        
    return mapForm

@csrf_exempt
def ajax_remove_coupon(request):
    code = request.POST.get('coupon_val')
    total = request.POST.get('total_val')
    c_code = CouponCode.objects.filter(code=code)
    
    invalid = False
    invalid_msg = ''
    if c_code:
        coupon_code = c_code[0]
        dp = coupon_code.discount_percent
        d_total = Decimal(total)
        new_total = (d_total/(1 - dp)).quantize(Decimal(".01"))
    
    t = 'commerce/ajax/coupon_snippet_restore.html'
    d = {'restored_total':new_total, 'coupon':''}  
    
    rendered = render_to_string(t,d)
    
    return HttpResponse(rendered, status=200)
    
@csrf_exempt
def ajax_apply_coupon(request):
    code = request.POST.get('coupon_val')
    total = request.POST.get('total_val')
    c_code = CouponCode.objects.filter(code=code)
    
    invalid = False
    invalid_msg = ''
    if c_code:
        coupon_code = c_code[0]
        if coupon_code.coupon_used == False:
            dp = coupon_code.discount_percent
            d_total = Decimal(total)
            new_total = ((1 - dp)*d_total).quantize(Decimal(".01"))
            percent = (dp * 100).quantize(Decimal("1"))
            discount_amount = (coupon_code.discount_percent * d_total).quantize(Decimal(".01"))
        else:
            return HttpResponse(status=400)
    else:
        return HttpResponse(status=400)
    
    t = 'commerce/ajax/coupon_snippet.html'
    d = {'new_total':new_total, 'percent':percent, 'discount_amount':discount_amount, 'coupon':coupon_code.code}  
    
    rendered = render_to_string(t,d)
    
    return HttpResponse(rendered, status=200)

@csrf_exempt
def ajax_change_location(request):
    id = request.POST.get('store_id')
    
    store = Store.objects.get(id=int(id))
    mapForm = createMap(store)
    
    pickup_day = getDay()
    pickup_time = getTime(store)
    
    city = request.POST.get('city')
    #logging.debug(city)
    
    CITY_DICT = {'sanfrancisco':'San Francisco', 'vancouver':'Vancouver'}
    store_city = CITY_DICT[city]
    store_all = Store.objects.filter(city=store_city, active=True)
    
    t1 = 'commerce/ajax/location_snippet.html'
    d1 = {'store':store, 'map':mapForm, 'pickup_time':pickup_time, 'store_all':store_all,
         'day':pickup_day, 'pickup_time':pickup_time, 'city':city}
    
    user = getUser(request)
    
    not_subscribed=True
    subscribed = False
    if user:
        subscribed = isSubscriber(user)
        if not subscribed:
            not_subscribed=True
        else:
            not_subscribed = False
    
    excluded = UNCHECKED_ITEMS
    
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    now_str = now.strftime('%d%m%y')
    
    selected_recipes, item_dict, total = getMeal(city, store)
    """if not subscriber update total"""
    if not_subscribed:
        total += Decimal("3.99")
        
    rendered1 = render_to_string(t1,d1)
    
    t2 = 'commerce/ajax/items_snippet.html'
    d2 = {'now':now_str,'excluded':excluded,'items':item_dict, 'subscribed':subscribed,
          'not_subscribed':not_subscribed,'total':total,'coupon':''}
    
    rendered2 = render_to_string(t2,d2)
    rendered = rendered1+"::"+rendered2
    
    return HttpResponse(rendered, status=200)   

@csrf_exempt
""" save users meal """
def ajax_save_meal(request):
    

""" run checkout steps for us """
def us_checkout(request, user):
    #Change payment form depending on location
    init = {'country':'US'}
    payForm = PaymentForm(initial=init)
    
    customer = None
    if user:
        try:
            user_profile = user.get_profile()
            customer_id = user_profile.stripeprofile
            stripe.api_key = settings.STRIPE_API_KEY
            customer = stripe.Customer.retrieve(customer_id)
        except UserProfile.DoesNotExist:
            pass
        except stripe.InvalidRequestError:
            pass
        except AttributeError:
            pass
    
    change_card = False
    if 'change_card' in request.GET:
        if request.GET.get('change_card')=='True':
            change_card = True
            
    return change_card, customer, payForm

""" run checkout steps for canada """
def canada_checkout(request, data):
    change_card = False
    customer = None
    payForm = chargePayPal(request,data)
    
    return change_card, customer, payForm
    
"""
Sends confirmation email
"""
def confirmation_email(user, data, pickup_day):
    subject = "Yupeat Order Confirmation - Pick up for %s" % (pickup_day)
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/confirmation_email.html',data)
    text_message = render_to_string('email/confirmation_email.txt',data)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [user.username])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

"""
Notifies admin that an order's been placed
"""
def admin_alert_email(user, data, pickup_time):
    u = User.objects.get(username=user)
    user_profile = u.get_profile()
    
    data['user_profile'] = user_profile
    
    subject = "Yupeat Order Placed - Pick up time set for %s" % (pickup_time)
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/order_alert_email.html',data)
    text_message = render_to_string('email/order_alert_email.txt',data)
    
    #admins = ['ray@yupeat.com', 'jess@yupeat.com']
    admins = ['ray@yupeat.com']
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

"""
Submits order
"""
def submit_order(request, item_dict, total, city=None, pickuptime=None, pickuplocation=None):
    min = 0
    max = total 
    purchased_items = {}
    
    error_msg = None
    
    calc_total = 0
    #logging.debug(item_dict)
    
    valid = False
    
    for key, value in request.POST.iteritems():
        #logging.debug(key)
        mod_key = key.replace('-',' ')
        if  mod_key in item_dict:
            calc_total += Decimal(value)
            #store purchased items
            purchased_items[mod_key] = value
    
    #Add payment success
    if calc_total > max:
        error_msg = "Please enter a valid total amount."
        messages.add_message(request, messages.ERROR, error_msg)
    elif calc_total <= 0.50:
        error_msg = "Please select amount total greater than 0.50 cents."
        messages.add_message(request, messages.ERROR, error_msg)
    else:
        valid = True
    
    """Add service fee if not subscriber """
    user = getUser(request)
    if not isSubscriber(user):
        calc_total += Decimal("3.99")
    
    """ Apply coupon discount  """
    confirm_coupon = request.POST.get("confirm_coupon")
    if confirm_coupon:
        up = user.get_profile()
        free_meal, calc_total = apply_coupon(confirm_coupon, up, calc_total)
        
    """Process payment with stripe"""
    if valid:
        valid = charge_Stripe(request, calc_total, purchased_items, city, free_meal, pickuptime, pickuplocation)
        
    return valid, error_msg, calc_total, purchased_items
    
def charge_Stripe(request, calc_total, purchased_items, city=None, free_meal=False, pickuptime=None, pickuplocation=None):
    user = getUser(request)
    valid = False
    
    recipe_id = request.POST.get('recipe_id')
    
    first = request.POST.get('first_name')
    last = request.POST.get('last_name')
    
    name=''
    if first and last:
        name = first +' '+ last
        
    address_line1 = request.POST.get('street1')
    address_line2 = request.POST.get('street2')
    address_city = request.POST.get('city')
    address_state = request.POST.get('state')
    address_zip = request.POST.get('postal_code')
    
    up_dict = {'name':name,
               'address_line1':address_line1,
               'address_line2':address_line2,
               'address_city': address_city,
               'address_state': address_state,
               'address_zip': address_zip }
    
    stripe.api_key = settings.STRIPE_API_KEY
    
    try:  
        """Check for saved version"""
        user_profile = user.get_profile()
        customer_id = user_profile.stripeprofile
        if customer_id:
            customer = stripe.Customer.retrieve(customer_id)
        else:
            customer = createStripeCustomer(request, user, up_dict, up_exists = True)
    except UserProfile.DoesNotExist:
        """Create new and save """
        customer = createStripeCustomer(request, user, up_dict, up_exists = False)
     
    total = int(calc_total*100)
    r = Recipe.objects.get(id=recipe_id)
    token = request.POST.get('stripeToken')
    
    ps_all = get_currentday_promo(city, pickuplocation)
    ps = ps_all[0]
    
    """check for free meal"""
    if free_meal:
        charge_id = 'free%d' % user_profile.id
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        
        oh = OrderHistory(userprofile=user_profile, meal=r, date=now, charge=charge_id, 
                          promo=ps, amount=total,pickuptime=pickuptime, pickupstore=pickuplocation)
        oh.save()
        
         #Keep a copy of the purchased items
        for k,v in purchased_items.iteritems():
            item = Item.objects.filter(name=k)[0]
            o = Order(orderhistory=oh, item=item)
            o.save()
        valid = True
        return valid
    
    """update stripe customer"""
    if 'change_card' in request.GET:
        cu = stripe.Customer.retrieve(customer.id)
        cu.card = token
        cu.save()
    
    try:
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        desc = 'charge for %s' % user.username
        charge = stripe.Charge.create(amount=total,currency='usd', customer=customer.id, description=desc)
        oh = OrderHistory(userprofile=user_profile, date=now, meal=r, charge=charge.id, 
                          promo=ps, amount=total, pickuptime=pickuptime, pickupstore=pickuplocation)
        oh.save()
        
        #Keep a copy of the purchased items
        for k,v in purchased_items.iteritems():
            item = Item.objects.filter(name=k)[0]
            o = Order(orderhistory=oh, item=item)
            o.save()
            
        valid=True
    except stripe.CardError, e: 
        messages.add_message(request, messages.ERROR, e)
        valid = False 
    except stripe.InvalidRequestError, e:
        messages.add_message(request, messages.ERROR, e)
        valid = False
    return valid
      
def createStripeCustomer(request, user, up_dict, up_exists=False):
    valid=True
    mnemonic = user.username
    
    currency = 'usd'    
    token = request.POST.get('stripeToken')
    
    msg = ''
    
    """create customer account"""
    stripe.api_key = settings.STRIPE_API_KEY
    try:
        customer = stripe.Customer.create(
          validate=True,
          mnemonic= user.username,
          card=token)
    except stripe.CardError, e:
        valid = False
        messages.add_message(request, messages.ERROR, e)
    
    if valid:
        """ if profile exists update user profile with contact details"""
        if up_exists:
            user_profile = user.get_profile()
            user_profile.stripeprofile = customer.id
            user_profile.name=up_dict['name']
            user_profile.address_line1 = up_dict['address_line1']
            user_profile.address_line2 = up_dict['address_line2']
            user_profile.address_city = up_dict['address_city']
            user_profile.address_state = up_dict['address_state']
            user_profile.address_zip = up_dict['address_zip']
        else:
            """ create user profile"""
            user_profile = UserProfile(user=user,
                                 stripeprofile=customer.id,
                                 name=up_dict['name'],
                                 address_line1=up_dict['address_line1'],
                                 address_line2=up_dict['address_line2'],
                                 address_city=up_dict['address_city'],
                                 address_state=up_dict['address_state'],
                                 address_zip=up_dict['address_zip'])
        user_profile.save()
    
    return customer
 
"""Create and return paypal submit button """
def chargePayPal(request, data):
    user = getUser(request)
    
    """Create an invoice id"""
    rand = "".join([random.choice(string.letters+string.digits) for x in range(1,7)])
    tc = str(time.clock()).replace('.','')
    charge_id = 'pp-%s-%s' % (tc,rand)
    
    
    """Add default pickup time"""
    data['pickup_time'] = 1
    
    """Store recipe name"""
    recipes = data['recipes']
    rname = recipes[0].name
    
    en_data = pp_encode_data(data)
    
    if user:
        saved_transaction = simplejson.dumps(en_data)
        st = SavedTransaction(user=user, charge=charge_id, data=saved_transaction, complete=False)
        st.save()
    
    custom = ""
    
    notify_url = "https://yupeat.appspot.com/ppipn/"
    return_url = "https://yupeat.appspot.com/order/complete/?order_id=%s" % charge_id 
    cancel_url = "https://yupeat.appspot.com/order/cancel/"
    
    paypal_dict = {
        "business": "ray@yupeat.com",
        "custom":custom,
        "amount": data['total'],
        "currency_code":'CAD',
        "item_name": rname,
        "invoice": charge_id,
        "notify_url": notify_url,
        "return_url": return_url,
        "cancel_return": cancel_url,
    }
    
    form = PayPalPaymentsForm(initial=paypal_dict)
    
    return form

def pp_encode_data(data):
    
    """convert decimals to str"""
    id={}
    item_dict = data['items']
    for k,v in item_dict.iteritems():
        id[k] = str(v)
    data['items']=id
    
    tot = data['total']
    data['total'] = str(tot)
    
    
    """serialize django objects"""
    recipes = data['recipes']
    data['recipes'] = serializers.serialize('json',recipes, fields=('name'))
    
    user = data['user']
    if user != None:
        data['user'] = serializers.serialize('json',[user], fields=('username'))
    
    store = data['store']
    data['store'] = serializers.serialize('json',[store], fields=('id'))
    
    return data

def pp_decode_data(en_data):
    data = simplejson.loads(en_data)
    
    user = data['user']
    u = simplejson.loads(user)[0]
    data['user'] = User.objects.get(id=u['pk'])
    
    recipes = data['recipes']
    r = simplejson.loads(recipes)[0]
    data['recipes'] = [Recipe.objects.get(id=r['pk'])] 
    
    store = data['store']
    s = simplejson.loads(store)[0]
    data['store'] = Store.objects.get(id=s['pk']) 
    
    return data
    
""" Receive paypal ipn signals"""
def order_update(sender, **kwargs):
    amount = sender.mc_gross
    charge_id = sender.invoice
    st = SavedTransaction.objects.get(charge=charge_id)
    st.complete = True
    st.custom = sender.custom
    st.save()
    
    data = pp_decode_data(st.data)
    data['charged'] = amount
    
    recipes = data['recipes']
    user = data['user']
    
    try:
        user_profile= user.get_profile()
        name = '%s %s' % (sender.first_name, sender.last_name)
        user_profile.name = name
        user_profile.save()
    except UserProfile.DoesNotExist:
        """Create new and save """
        name = '%s %s' % (sender.first_name, sender.last_name) 
        user_profile = UserProfile(user=user, name=name)
        user_profile.save()
        
        
    """parse custom tags returned by paypal
    custom contains info of excluded items and pickup time"""
    purchased_items,pu_time = parseCustom(data, sender)
    data['items'] = purchased_items
    data['pickup_time'] = pu_time
    
    """return store """
    store = data['store']
    
    
    pickup_day = data['pickup_day']
    
    """Format pickup time """
    val = int(data['pickup_time'])
    time_array = getTime(store)
    pickup_time = time_array[val-1]
    data['pickup_time'] = pickup_time
    
    c = store.city
    city = c.lower().replace(' ','')
    
    ps_all = get_currentday_promo(city,store)
    ps = ps_all[0]
    
    if not echeck_confirm(sender):
        oh = OrderHistory(userprofile=user_profile, meal=recipes[0], charge=charge_id, promo=ps,
                          amount=amount, pickuptime=pickup_time, pickupstore=store)
        oh.save()
        
        try:    
            #Keep a copy of the purchased items
            for k,v in purchased_items.iteritems():
                item = Item.objects.filter(name=k)[0]
                o = Order(orderhistory=oh, item=item)
                o.save()
        except IndexError:
            logging.error(purchased_items)
        
        
        confirmation_email(user, data, pickup_day)
        admin_alert_email(user,data,pickup_time)
    
payment_was_successful.connect(order_update)

"""if echeck payment transfer complete / skip duplicate order save and email """
def echeck_confirm(sender):
    is_echeck = False
    is_completed = False
    
    if sender.payment_type == 'echeck':
        is_echeck = True
    if sender.payment_status == 'Completed':
        is_completed = True
    
    if is_echeck and is_completed:
        return True
    
    return False
    
"""
returns subset of purchased items for paypal purchases
"""
def parseCustom(data, sender):
    purchased_items = {}
    excluded_items = sender.custom
    ei = excluded_items.replace('-',' ').split(',')
    ei_array = ei[1:]
    
    all_items = data['items']
    ai = []
    for k,v in all_items.iteritems():
        ai.append(k)
    
    pi = set(ai).difference(ei_array)
    for p in pi:
        purchased_items[p] = all_items[p]
    
    pickup_time = ei[0]
    
    return purchased_items, pickup_time
 
"""
Returns shopping day
"""
def getDay(default_day=5):
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    
    month = now.month
    year = now.year
    day = now.day
    
    d = date(year, month, day) # January 1st                                                          
    d += timedelta(days = default_day - d.weekday())  # First Sunday                                                         
    return now.strftime("%a (%b %d, %Y)")

"""
Returns current week (Week %wk_num of %month)
"""
def getWeek():
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    
    day = now.day
    week_number = (day - 1) // 7 + 1
    
    val = "Week %s of %s" % (week_number, now.strftime("%B"))   
    
    return val
"""
Generates list of pick-up times for dropdown
"""
def getTime(store=None):
    
    if store:
        d = store.pickup_time
    else:
        d = datetime(2011,1,1,16)
    
    time_array= []
    for x in range(0,4):
        time = d.strftime("%I:%M")
        
        d += timedelta(minutes=30)
        time_plus = d.strftime("%I:%M %p")
        
        time_string = time.lstrip('0') + ' - ' + time_plus.lstrip('0')
        
        time_array.append(time_string)
        
    return time_array
        
""" 
Returns pick-up time
"""
def getPickupTime(request,store):
    
    val = int(request.POST.get('pickup_time'))
    time_array = getTime(store)
    return time_array[val-1]

"""
Returns boolean value indicating whether website is being accessed after deadline
"""
def afterDeadline():
    cutoff = ['16','30', 'Saturday','Sunday'] #4:30pm
    
    pacific = timezone('US/Pacific')
    pa_time = datetime.now(pacific)
    pa = pa_time.strftime('%H,%M')
    p_array = pa.split(',')
    day_str = pa_time.strftime('%A')
    
    if int(p_array[0]) > int(cutoff[0]):
        return True
    
    if int(p_array[0]) >= int(cutoff[0]) and int(p_array[1]) > int(cutoff[1]):
        return True
    
    if day_str in cutoff:
        return True
    
    return False 

"""
Returns boolean value indicating whether it's the weekend
"""
def isWeekend():
    cutoff = ['Saturday','Sunday']
    pacific = timezone('US/Pacific')
    pa_time = datetime.now(pacific)
    day_str = pa_time.strftime('%A')
    if day_str in cutoff:
        return True
    return False

"""
Applies coupon discount to final price 
"""
def apply_coupon(code, userprofile, calc_total):
    new_total = calc_total
    free_meal = False
    
    c_code = CouponCode.objects.filter(code=code)
    if c_code:
        coupon_code = c_code[0]
        if coupon_code.coupon_used == False:
            dp = coupon_code.discount_percent
            new_total = ((1 - dp)*calc_total).quantize(Decimal(".01"))
            
            coupon_code.coupon_used = True
            coupon_code.userprofile = userprofile
            coupon_code.save()
            
            if dp == 1:
                free_meal = True
    
    return free_meal, new_total

"""
Returns boolean value indicating whether user is subscribed
"""
def isSubscriber(user):
    user_profile = user.get_profile()
    try:
        sub = Subscription.objects.get(userprofile=user_profile)
    except Subscription.DoesNotExist:
        sub = Subscription(userprofile=user_profile, subscription=False)
    
    subscribed = sub.subscription
    
    return subscribed

""" 
Returns city
"""
def getCity(request, city):
    if not city:
        if 'city' in request.session:
            city = request.session['city']
        else:
            city = 'sanfrancisco'
            request.session['city'] = city    
        
    return city
   
""" 
Returns list of items for selected meals
"""
def getMeal(city, store=None, id=None):
    item_dict = {}
    recipe_ids = []
    
    """If no id provided get promo for current day and city"""
    if id==None:
        recipe = sub_to_city(city)
        if recipe == None:
            return None, None, None
        
        recipe_list = [recipe.id]
    else:
        recipe_list = [id]
        
    for recipe in recipe_list:
      recipe_ids.append(int(recipe))
    
    """Add default pricing"""
    recipe_all = Recipe.objects.filter(id__in=recipe_ids)
    for r in recipe_all:
        item_dict, total = generateItemDict(item_dict, r)
    
    """Update item_dict with latest"""
    if store:
        ps_all = get_currentday_promo(city, store)
    else:
        ps_all = get_currentday_promo(city)
        
    try:
        ps = ps_all[0]
        item_dict, total = get_items_latest_price(item_dict, ps)
    except:
        total = None
        recipe_all = None
        item_dict = None
        
    return recipe_all, item_dict, total 

""" 
Returns list of items for selected meals
"""
def getLatestMeal(city, id=None):
    item_dict = {}
    recipe_ids = []
    
    """If no id provided get promo for current day and city"""
    if id==None:
        promo = get_latest_promo(city)[0]
        recipe = promo.recipe
        if recipe == None:
            return None, None, None
        
        recipe_list = [recipe.id]
    else:
        recipe_list = [id]
        
    for recipe in recipe_list:
      recipe_ids.append(int(recipe))
    
    """Add default pricing"""
    recipe_all = Recipe.objects.filter(id__in=recipe_ids)
    for r in recipe_all:
        item_dict, total = generateItemDict(item_dict, r)
    
    """Update item_dict with latest"""
    ps_all = get_latest_promo(city)
    try:
        ps = ps_all[0]
        item_dict, total = get_items_latest_price(item_dict, ps)
    except:
        total = None
        recipe_all = None
        item_dict = None
        
    return recipe_all, item_dict, total

"""
Check if user wants to access and old meal
"""
def oldMeal(city, id):
    if id != None:
        ps_all = get_currentday_promo(city)
        #logging.debug(ps_all)
        if len(ps_all) == 0:
            return True
        else:
            ps = ps_all[0]
            if int(id) != int(ps.recipe.id):
                return True
    return False

"""
get promo for current day's promo for a city
"""
def get_currentday_promo(city, store=None):
   pacific = timezone('US/Pacific')
   now = datetime.now(pacific)
   
   n = datetime(now.year,now.month,now.day)
   
   if store:
       ps_all = PromoSchedule.objects.filter(store=store, date=n)
   else:
       #Get promo for any store within city
       store = sub_to_store(city)
       ps_all = PromoSchedule.objects.filter(store=store, date=n) 
   
   return ps_all  

"""
get most recent promo (use when current days promo is missing) 
TODO: Modify to handle multiple stores in a city
"""
def get_latest_promo(city):
    store = sub_to_store(city)
    ps_all = PromoSchedule.objects.filter(store=store).order_by('-date')
    return ps_all

"""
Match subdomain to city
TODO: Modify to handle multiple stores in a city
"""
def sub_to_city(request_city):
    city = {'sanfrancisco':'San Francisco', 'vancouver':'Vancouver'}
    c=city[request_city]
    store = Store.objects.filter(city=c, active=True)[0]
    
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    
    n = datetime(now.year,now.month,now.day)
    ps = PromoSchedule.objects.filter(store=store, date=n)
    
    if len(ps)>0:
        promo = ps[0]
        recipe = promo.recipe
    else:
        recipe = None
    
    return recipe

"""
Match subdomain to store
TODO: Modify to handle multiple stores in a city
"""
def sub_to_store(request_city):
    s = Store.objects.exclude(active=False)
    store_mapping = {}
    
    """
    TO-DO: Move to cache
    """
    for store in s:
        city = store.city.lower()
        store_mapping[city.replace(' ','')] = store   
    
    if request_city in store_mapping:
        sm = store_mapping[request_city]
    else:
        sm = None
    
    return sm

"""
Converts item text blob to dictionary 
"""
def generateItemDict(item_dict, r):
    total = 0
    items_all = r.items.split('\n')
    
    for i in items_all:
        ic = cleanup(i)
        if len(i.strip()) > 0:
            item_obj = Item.objects.filter(name__exact=ic)
            if len(item_obj) > 0:
                
                #check for a more recent price for given item
                iph = ItemPriceHistory.objects.filter(item=item_obj[0])
                
                if len(iph) > 0:
                    index_val = len(iph)-1
                    item_dict[item_obj[0].name] = iph[index_val].price
                    total += iph[index_val].price
                    
                else:
                    item_dict[item_obj[0].name] = item_obj[0].price
                    total += item_obj[0].price
            else:
                item_dict[i.strip()] = 0.00
    return item_dict, total

"""
Remove additional unwanted characters
"""
def cleanup(i):    
    return i.replace('\r','').strip()

"""
Converts number strings to ints 
"""
def string_to_int(ids):
    num_array = []
    for i in ids:
        num_array.append(int(i))
    return num_array

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

"""
Administrative functions
- Used to edit a meal to list of meal offers 
"""
@user_passes_test(lambda u: u.is_staff)
def edit_meal(request, recipe_id):
    r = get_object_or_404(Recipe, pk=recipe_id)
    #view_url = reverse('commerce.views.edit_meal', args=[recipe_id])
    view_url = '/order/admin/edit/%s/' % recipe_id
    if request.POST:
        offer = OfferForm(request.POST, request.FILES, instance=r)
        try:
            if offer.is_valid():
               offer.save()
            else:
                view_url += '?error=Not a valid image'
            return HttpResponseRedirect(view_url)
        except Exception,e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error('caught %s in image upload',e)
            raise e
    else:
        offer = OfferForm(instance=r)
    
    upload_url, upload_data = prepare_upload(request, view_url, backend='djangoappengine.storage.prepare_upload')
    template = 'commerce/admin/admin_offer.html'
    
    data = {'offer':offer, 'upload_url':upload_url, 'upload_data':upload_data }
    return render_to_response(template, data,context_instance=RequestContext(request))

"""Admin function 
- Used to delete meals
"""
@user_passes_test(lambda u: u.is_staff)  
def delete_meal(request, recipe_id):
    r = Recipe.objects.get(pk=recipe_id)
    r.delete()

    return HttpResponseRedirect('/order/admin/all')
   
"""
Administrative functions
- Used to add a meal to list of meal offers 
"""
@user_passes_test(lambda u: u.is_staff)
def new_meal(request):
    #view_url = reverse('commerce.views.new_meal')
    view_url = '/order/admin/new/'
    upload_url, upload_data = prepare_upload(request, view_url, backend='djangoappengine.storage.prepare_upload')
    
    if request.POST:
        offer = OfferForm(request.POST, request.FILES)
        try:
            if offer.is_valid():
               offer_obj = offer.save()
               stylize_meal_page(offer_obj)
            else:
                view_url += '?error=Not a valid image'
                
            info_msg = "New meal saved!"
            messages.add_message(request, messages.INFO, info_msg)
            
            template = 'commerce/admin/admin_offer.html'
            data = {'offer':offer, 'upload_url':upload_url, 'upload_data':upload_data }
    
            return render_to_response(template, data,context_instance=RequestContext(request))
        
        except Exception,e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error('caught %s in image upload',e)
            raise e
    else:
        offer = OfferForm()
    
    template = 'commerce/admin/admin_offer.html'
    data = {'offer':offer, 'upload_url':upload_url, 'upload_data':upload_data }
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Helper function to stylize meal page
- re-saves meal content with new style    
"""
def stylize_meal_page(offer):
    r = Recipe.objects.get(id=offer.id)
    directions = r.dirfull
    
    nd = directions.replace('=\r\n','')
    nnd = nd.replace('=B0','')
    nnnd = nnd.replace('=20','')
    r.dirfull = nnnd
    
    units = ['yards', 'yard', 'teaspoons', 'teaspoon', 'tablespoons', 'tablespoon',
      'tbsps', 'tsps', 'tbsp', 'tsp', 'quarts', 'quart', 'pounds', 'pound', 'lb','lbs',
      'pints', 'pint', 'pinches', 'pinch', 'oz', 'ounces', 'ounce', 'liters', 
      'liter', 'inches', 'inch', 'gallons', 'gallon', 'fluid oz.', 'feet', 'foot', 
      'dashes', 'dash', 'cups', 'cup']
    
    updated_array = []
    
    ingr = r.ingrfull 
    ingr = ingr.replace('&bull;','')
    ingr = ingr.replace('.','')
    ingr = ingr.replace('x','')
    ingr = ingr.replace('pound','lb')
    ingr = ingr.replace('teaspoons','tsp')
    ingr = ingr.replace('teaspoon','tsp')
    ingr = ingr.replace('tablespoon','tbsp')
    nn_ingr = ingr.replace('tablespoon','tbsp')
    
    ingr_array = re.split(r'[\n\r]+',nn_ingr)
    
    for ia in ingr_array:
        i = ia.split()
        no_unit = True
        for ii in i: 
            if ii.lower() in units:
                unit_item = ia.split(ii)
                
                unit = unit_item[0].lstrip()
                item = unit_item[1].rstrip()
                
                updated_array.append((unit+ii,item))
                no_unit = False
        
        #catch all for ingredient lines with no units
        if no_unit == True:
            number = ''
            other = ''
            for val in ia.split():
                if is_number(val):
                    number += val
                else:
                    other += ' '+val
            updated_array.append((number,other.lstrip()))
    
    new_ingrfull = ''
    for ua in updated_array:
        whole, num, denom, unit = get_fraction(ua)
        item = get_item(ua)
        
        if num and denom: 
            frac = True
        else:
            frac = False
        
        data = {'fraction':frac, 'numerator':num, 
                'denominator':denom, 'quantity':whole,
                'unit':unit, 'item':item }
        
        template = 'meals/details_style_snippet.html'
        rts = render_to_string(template,data)
        
        new_ingrfull += rts + "\r\n"
    
    r.igrfull_styled = new_ingrfull
    r.save()
    
    
"""
Helper function
- return fraction   
"""
def get_fraction(ua):
    whole = None
    num = None
    denom = None
    unit = None 
    
    other = []
    numbers = []
    
    vals = ua[0].split()
    for v in vals:
        if is_number(v):
            numbers.append(v)
            
        else:
            other.append(v)
        
    if len(numbers) > 0:
        for n in numbers:
            if '/' in n:
                num = n.split('/')[0]
                denom = n.split('/')[1]
            else:
                whole = n
    
    unit = ' '.join([o for o in other])
    return whole, num, denom, unit


"""
Helper function
- return item   
"""
def get_item(ua):
    return ua[1]

"""
Helper function
- is string a number   
""" 
def is_number(s):
    try:
        num = float(Fraction(s))
        return True
    except ValueError:
        try:
            float(s)
            return True
        except ValueError:
            return False

"""
Administrative functions
- Displays all of the meal offers provided by store
- TODO: Add checkbox to store meal  
""" 
@user_passes_test(lambda u: u.is_staff)
def admin_all(request):
    template = 'commerce/admin/admin_all.html'
    recipes = Recipe.objects.all()
    data = {'recipes':recipes}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Form for adding stores
- TODO: Add new stores 
"""
@user_passes_test(lambda u: u.is_staff)
def admin_store(request):
    if request.POST:
        store = StoreForm(request.POST)
        if store.is_valid():
            store.save()
    else:
        store = StoreForm()
    
    template = 'commerce/admin/admin_store.html'
    data = {'store_form':store}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Displays all of the stores
"""
@user_passes_test(lambda u: u.is_staff)
def admin_store_all(request):
    template = 'commerce/admin/admin_store_all.html'
    data = {'store':Store.objects.all()}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

def admin_store_edit(request, store_id):
    s = get_object_or_404(Store, pk=store_id)
    if request.POST:
        store = StoreForm(request.POST, instance=s)
        if store.is_valid():
            store.save()
    else:
        store = StoreForm(instance=s)
    
    template = 'commerce/admin/admin_store.html'
    
    data = {'store_form':store}
    return render_to_response(template, data,context_instance=RequestContext(request))

@user_passes_test(lambda u: u.is_staff)
def admin_store_delete(request, store_id):
    s = Store.objects.get(pk=store_id)
    s.delete()
    
    return HttpResponseRedirect('/order/admin/store/all')


"""
Administrative functions
- disable page if item is sold out at certain store
"""
@user_passes_test(lambda u: u.is_staff)
def admin_soldout(request, store_id=None):
    if store_id:
        store = Store.objects.get(id=store_id)
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        n = datetime(now.year,now.month,now.day)
        
        #logging.debug(store.id)
        #logging.debug(n)
        
        ps_all = PromoSchedule.objects.filter(store=store, date=n)
        ps = ps_all[0]
        
        if request.POST:
            form = SoldoutForm(request.POST, instance=ps)
            form.save()
        else:
            form = SoldoutForm(instance=ps)
        
        template = 'commerce/admin/admin_soldout_details.html'
        data = {'form':form,  'store':store, 'recipe':ps.recipe, 'date':ps.date}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
    
    store = Store.objects.all()
    template = 'commerce/admin/admin_soldout.html'
    data = {'store':store}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- track the day's orders for a specified store
"""
@user_passes_test(lambda u: u.is_staff)
def admin_track_orders(request, store_id=None):
    if store_id:
        store = Store.objects.get(id=store_id)
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        
        n = datetime(now.year,now.month,now.day)
        
        """Check if selected store is an "(All City)" placehoder"""
        promo_schedule_array = []
        
        allcity_bool, city = isAllCity(store)
        if allcity_bool:
            #if all city create an array of PromoSchedules
            stores_all = Store.objects.filter(city=city)
            for s in stores_all:
                ps = PromoSchedule.objects.filter(store=s, date=n)
                promo_schedule_array.append(ps)
                
                #TODO: Update to handle case where stores carry different meals
                recipe = ps[0].recipe
                date = ps[0].date
        else:
            ps_all = PromoSchedule.objects.filter(store=store, date=n)
            ps = ps_all[0]
            promo_schedule_array.append(ps)
            
            recipe = ps[0].recipe
            date = ps[0].date
        
        daysorders = generate_daysorder_dict(promo_schedule_array, recipe)
        
        template = 'commerce/admin/admin_track_orders_details.html'
        data = {'items_ordered':daysorders,  'store':store, 'recipe':recipe, 'date':date}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
    
    store = Store.objects.all().order_by('city')
    template = 'commerce/admin/admin_track_orders.html'
    data = {'store':store}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- returns a dictionary summarizing the total of the days orders
"""
def generate_daysorder_dict(ps_array, recipe):
   """Initialize to default of 0 for all items"""
   daysorder_dict = {}
   daysorder_dict, total = generateItemDict(daysorder_dict, recipe)
   for k,v in daysorder_dict.iteritems():
       daysorder_dict[k] = 0
   
   logging.debug(daysorder_dict)
   
   for ps in ps_array:         
       oh = OrderHistory.objects.filter(promo=ps[0]) 
       oh_array = []
       
       for o in oh:
           oh_array.append(o.id) 
       
       logging.debug('Store %s has length order array: %s' % (ps[0].store.store_name, len(oh_array)))
       
       all_items = []
       if len(oh) > 0:
           all_items = Order.objects.filter(orderhistory__in=oh_array)
       
       for ai in all_items:
           if ai.item.name in daysorder_dict:
               daysorder_dict[ai.item.name] += 1
       
   return daysorder_dict

"""
Administrative functions
- Manage order eligible websites
"""
@user_passes_test(lambda u: u.is_staff)
def admin_order_eligiblesite(request):
    if request.POST:
        url_array = []
        url_list = request.POST.get('url')
        url_array = url_list.splitlines()
        for u in url_array:
            cu = url_cleanup(u)
            oe = OrderEligibleSite(url=cu, active=True)
            oe.save()
        
        info_msg = "URLs saved!"
        messages.add_message(request, messages.INFO, info_msg)
    
    form = OrderEligibleSiteForm()
    
    template = 'commerce/admin/admin_order_eligible_site.html'
    data = {'form':form}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Manage promotion schedule
"""
@user_passes_test(lambda u: u.is_staff)
def admin_promo_schedule(request, store_id=None, date=None):
    if store_id and date:
        if request.POST:
            return update_scheduled_promo(request)
        store = Store.objects.get(id=store_id)
        date = datetime.strptime(date,'%A-%B-%d-%Y')
        
        recipe_id = request.GET.get('meal')
        recipe = Recipe.objects.get(id=recipe_id)
        
        ps_all = PromoSchedule.objects.filter(store=store, date=date)
        if len(ps_all) == 0:
            ps = PromoSchedule(store=store, date=date, recipe=recipe, soldout=False)
            ps.save()
        else:
            ps = ps_all[0]
            if ps.recipe.id != recipe_id:
                ps.recipe = recipe
                ps.save()
                
        item_dict = {}
        item_dict, total = generateItemDict(item_dict, recipe)
        item_dict, total = get_items_latest_price(item_dict, ps)
        
        template = 'commerce/admin/admin_promo_schedule_details.html'
        data = {'recipe':recipe, 'store':store,'date':date, 'items':item_dict, 'promo_id':ps.id}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
        
    if store_id:
        fullyear = get_calendar()
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        
        today = now
        year,weeknumber,dayofweek = today.isocalendar()
        schedule = fullyear[weeknumber]
        
        #try except used to handle the new year    
        try:
            two_week_schedule = schedule + fullyear[weeknumber+1]
        except KeyError:
            nextyear = get_nextyear_calendar()
            two_week_schedule = schedule + nextyear[1]
        
        store = Store.objects.get(id=store_id)
        
        ps_dict = {}
        ps_all = PromoSchedule.objects.filter(store=store)
        for ps in ps_all:
            pd = ps.date
            d  = pd.strftime('%A (%B %d,  %Y)')
            ps_dict[d] = ps.recipe.name
        
        s_form = ScheduleRecipeForm()
        template = 'commerce/admin/admin_promo_schedule.html'
        data = {'two_week':two_week_schedule,  'store':store,'s_recipes':s_form, 'promo':ps_dict}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
    
    store = Store.objects.all().order_by('city')
    template = 'commerce/admin/admin_promo_select_store.html'
    data = {'store':store}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Update promotion schedule
"""
@user_passes_test(lambda u: u.is_staff)
def update_scheduled_promo(request):
    promo_id = request.POST.get('promo_id')
    ps = PromoSchedule.objects.get(id=promo_id)
    ps_array = [ps]
    
    """Check if selected store is an "(All City)" placehoder"""
    store = ps.store
    allcity_bool, city = isAllCity(store)
    if allcity_bool:
        ps_array = update_allcity_stores(request, city, ps)
    
    #Code to loop over inputs
    for k,v in request.POST.iteritems():
        
        if k != 'promo_id' and k !='csrfmiddlewaretoken':
            i = Item.objects.filter(name=k)
            if len(i) > 0:
                ii = i[0]
                for ps in ps_array:
                    iph_all = ItemPriceHistory.objects.filter(promo=ps, item=ii)
                    if len(iph_all) == 0:
                        iph = ItemPriceHistory(promo=ps, item=ii)
                    else:
                        iph = iph_all[0]
                    sm_price = store_markup(allcity_bool, ps.store, Decimal(v))
                    iph.price = sm_price
                    iph.save()
            else:
                
                #Save item
                i = Item(name=k,price=v)
                i.save()
                for ps in ps_array:
                    #Save itempricehistory
                    iph = ItemPriceHistory(promo=ps, item=i)
                    sm_price = store_markup(allcity_bool, ps.store, Decimal(v))
                    iph.price = sm_price
                    iph.save()
    
    date = ps.date.strftime('%A-%B-%d-%Y')
    
    return redirect('/order/admin/promoemail/%s' % ps.id)

"""
Helper function - applies price markup for specific stores
i.e. whole foods...  
"""
def store_markup(allcity_bool, store, price):
    """manually entered individual store prices preserved
    i.e., someone actually went to whole foods and entered prices
    """
    if not allcity_bool:
        return price 
    
    """is there a markup for the specifid store?"""
    if STORE_MARKUP.has_key(store.store_name):
        mu = STORE_MARKUP[store.store_name]
        value = Decimal(1+mu) * price
        return value.quantize(Decimal('.01'), rounding=ROUND_UP)
    
    return price
    
"""
Helper function - checks if store is an allcity placeholder
- returns true if store is an all city placeholder 
"""
def isAllCity(store):
    ALL_CITY_LIST = ['San Francisco (All Stores)']
    
    if store.store_name in ALL_CITY_LIST:
        return True, store.city
    return False, None 

"""
Administrative functions to update promo for all stores at once
- update promo for all stores in a city 
"""
def update_allcity_stores(request, city, ps):
    ps_array = []
    recipe = ps.recipe
    date = ps.date
    
    recipe_id = request.GET.get('meal')
    store_array = Store.objects.filter(city=city, active=True)
    
    for store in store_array:
        ps_all = PromoSchedule.objects.filter(store=store, date=date)
        if len(ps_all) == 0:
            ps = PromoSchedule(store=store, date=date, recipe=recipe, soldout=False)
            ps.save()
            ps_array.append(ps)
        else:
            ps = ps_all[0]
            if ps.recipe.id != recipe_id:
                ps.recipe = recipe
                ps.save()
            ps_array.append(ps)
    return ps_array

"""
Administrative functions to update email contents
- preview and edit email contents 
"""
def admin_promo_email(request, promo_id):
    promo = PromoSchedule.objects.get(id=promo_id)
    download_zip = None
    
    fromdate = date(2011,8,1)
    todate = promo.date.date()
    daygenerator = (fromdate + timedelta(x + 1) for x in xrange((todate - fromdate).days))
    since_launch = sum(1 for day in daygenerator if day.weekday() < 5) + 1
    
    str_day = todate.strftime('%b. %d')
    campaign_name = 'SF Launch %s (Day %s) - %s' % (str_day, since_launch, promo.recipe.name)
    
    if request.POST:
        pef = PromoEmailForm(request.POST, request.FILES)
        if pef.is_valid():
            
            pe_obj = pef.save()
            admin_create_chimpmail(pe_obj.id, promo)
            
            info_msg = "File zipped and ready to ship"
            messages.add_message(request, messages.INFO, info_msg)
            
            return HttpResponseRedirect('/order/admin/promoemail/sendzip/%s' % pe_obj.id)
            
    else:
        items_x = promo.recipe.items
        items = re.sub(r'[\r\n]+',', ',items_x)
        pef = PromoEmailForm(initial={'email_subject':promo.recipe.name, 
                                      'ingr_summary':items,
                                      'campaign_name':campaign_name})
    
    template = 'commerce/admin/admin_promo_email.html'
    data = {'email_form':pef, 'ps':promo, 'campaign_name':campaign_name}
    return render_to_response(template, data,context_instance=RequestContext(request)) 
    
"""
Administrative functions
- Create mailchimp 
"""
def admin_create_chimpmail(id, promo):
    pe_obj = PromoEmail.objects.get(id=id)
    pe_obj.promoschedule = promo
    pe_obj.email_subject = promo.recipe.name
    pe_obj.save()
    
    #call admin create email
    ps = pe_obj.promoschedule
    #limit visibility to city specific lists 
    store = ps.store
    r = ps.recipe
    
    meal_name = r.name
    cook_time = r.cooktime
    
    item_dict = {}
    item_dict, total = generateItemDict(item_dict, r)
    
    new_dict = nonexcluded_item_dict(item_dict)
    item_dict, total = get_items_latest_price(new_dict, ps)
    
    price = total/r.serv
    price_per = ("%.2f" % price)
    
    store_name = store.store_name
    store_street1 = store.street1
    store_city = store.city
    store_state = store.state
    store_zip = store.postal_code
    
    meal_summary_x = pe_obj.meal_summary
    meal_summary = re.sub(r'[\r\n]+','<br/><br/>',meal_summary_x) 
    
    ingr_summary = pe_obj.ingr_summary
    
    city = store.city.lower().replace(' ','')
    
    url_to_promo = 'https://yupeat.appspot.com/order/%s/%s' % (city,r.id)
    
    """ensure proper encoding"""
    utp = url_to_promo.encode('utf-8')
    pp = price_per.encode('utf-8')
    ms = meal_summary.encode('utf-8')
    ingr_sum = ingr_summary.encode('utf-8')
    
    #create pre populated text box for ingredient subset list
    context = {'meal_name':meal_name, 'price_per':pp, 'cook_time':cook_time, 
               'servings':r.serv,'meal_summary':ms, 'ingr_summary':ingr_sum, 
               'url_to_promo':utp, 'store_name':store_name,
               'store_street1':store_street1, 'store_city':store_city,
               'store_state':store_state, 'store_zip':store_zip}
    
    output = StringIO.StringIO()
    z = zipfile.ZipFile(output,'w')
    
    html = render_to_string('email/yupeat_email_template.html', context)
    email_image = pe_obj.email_image 
    
    z.writestr("current.html", html.encode('utf-8'))
    z.writestr("current.jpg", email_image)
    z.close()
    
    file_name = files.blobstore.create(mime_type='application/zip',_blobinfo_uploaded_filename='yupeat.zip')
    with files.open(file_name, 'a') as f:
        f.write(output.getvalue())
    files.finalize(file_name)
    blob_key = files.blobstore.get_blob_key(file_name)        
    
    pe_obj.zip_file_key = blob_key
    pe_obj.save()

"""
Administrative functions
- send zipped chimp file
"""
def admin_sendzip_chimp(request, promo_email_id):
    download_zip = '/order/admin/remote_fetch_zip/%s' % (promo_email_id)
    if request.POST:
        pe_obj = PromoEmail.objects.get(id=promo_email_id)
        ps = pe_obj.promoschedule
        r = ps.recipe
        meal_name = r.name
        
        encoded = fetch_encoded_zip(promo_email_id)
        
        content = {}
        content['archive'] = encoded
        content['archive_type'] = 'zip'
        
        type = 'regular'
        
        opt = {}
        
        opt['list_id'] = 'eaa0a378ba' 
        opt['subject'] = meal_name #r.name
        opt['from_email'] = 'yupeat@yupeat.com' 
        opt['from_name'] = 'Yupeat'
        opt['to_email'] = 'Yupeat'
        
        opt['analytics'] = {'google':'UA-12532896-4'}
        opt['title'] = pe_obj.campaign_name
        opt['generate_text'] = True
        
        #call create campaign
        ms = MailSnake(settings.MAILCHIMP_API_KEY)
        cc = ms.campaignCreate(type=type, options=opt, content=content)
        
        pe_obj.campaign_id = cc
        pe_obj.save()
        
        info_msg = "Zipped File Sent to MailChimp"
        messages.add_message(request, messages.INFO, info_msg)
    
    template = 'commerce/admin/admin_promo_sendzip.html'
    context = {'download_zip':download_zip}
    return render_to_response(template, context,context_instance=RequestContext(request))
    

"""
Administrative functions
- Fetch encoded zip file
"""
def fetch_encoded_zip(promo_email_id):
    pe = PromoEmail.objects.get(id=promo_email_id)
    blob_key = pe.zip_file_key
    
    # Fetch blob by key from blobstore
    blob_info = blobstore.BlobInfo.get(blob_key)
    if not blob_info:
        raise Exception('Blob Key does not exist')

    blob_file_size = blob_info.size
    blob_content_type = blob_info.content_type
    
    # Attempt to fetch the blob in one or more chunks depending on size and api limits
    blob_concat = ""
    start = 0
    end = blobstore.MAX_BLOB_FETCH_SIZE - 1
    step = blobstore.MAX_BLOB_FETCH_SIZE - 1
    
    while(start < blob_file_size):
        blob_concat += blobstore.fetch_data(blob_key, start, end)
        temp_end = end
        start = temp_end + 1
        end = temp_end + step
    encoded = base64.b64encode(blob_concat)
    
    return encoded
 
"""
Administrative functions
- Download zip file
"""
@user_passes_test(lambda u: u.is_staff)
def remote_fetch_zip(request,promo_email_id):
    pe = PromoEmail.objects.get(id=promo_email_id)
    blob_key = pe.zip_file_key
    
    # Fetch blob by key from blobstore
    blob_info = blobstore.BlobInfo.get(blob_key)
    if not blob_info:
        raise Exception('Blob Key does not exist')

    blob_file_size = blob_info.size
    blob_content_type = blob_info.content_type
    
    # Attempt to fetch the blob in one or more chunks depending on size and api limits
    blob_concat = ""
    start = 0
    end = blobstore.MAX_BLOB_FETCH_SIZE - 1
    step = blobstore.MAX_BLOB_FETCH_SIZE - 1
    
    while(start < blob_file_size):
        blob_concat += blobstore.fetch_data(blob_key, start, end)
        temp_end = end
        start = temp_end + 1
        end = temp_end + step
    return HttpResponse(blob_concat, mimetype=blob_content_type)
   
"""
Administrative functions
- Update item dict with only non-excluded items
"""        
def nonexcluded_item_dict(item_dict):
    new_dict = {}
    excluded = UNCHECKED_ITEMS
    for k,v in item_dict.items():
        item = k.replace(' ','-')
        if item in excluded:
            pass
        else:
            new_dict[k] = v
    return new_dict

"""
Administrative functions
- Update item dict with prices for current promo
"""
def get_items_latest_price(item_dict, ps):
    total = Decimal('0.00')
    iph = ItemPriceHistory.objects.filter(promo=ps)
    for i in iph:
        if i.item:
            item_name = i.item.name
            if item_name in item_dict:
                item_dict[item_name] = i.price
                total += i.price 
    return item_dict, total
    
"""Used to generate week schedule for admin view"""    
def allsundays(year):
    """This code was provided in the previous answer! It's not mine!"""
    d = date(year, 1, 1)                    # January 1st                                                          
    d += timedelta(days = 6 - d.weekday())  # First Sunday                                                         
    while d.year == year:
        yield d
        d += timedelta(days = 7)

def get_calendar():
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    
    year = now.year
    
    cal = {}
    for wn,d in enumerate(allsundays(year)):
        # This is my only contribution!
        cal[wn+1] = [(d + timedelta(days=k)).strftime('%A (%B %d,  %Y)') for k in range(0,7) ]
    
    return cal

def get_nextyear_calendar():
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    
    year = now.year + 1
    
    cal = {}
    for wn,d in enumerate(allsundays(year)):
        # This is my only contribution!
        cal[wn+1] = [(d + timedelta(days=k)).strftime('%A (%B %d,  %Y)') for k in range(0,7) ]
    
    return cal

def get_rand_token():
    import string
    import random
    return "".join([random.choice(string.letters+string.digits) for x in range(1,7)])

"""
Administrative functions
- Manage meal store associations  
"""
@user_passes_test(lambda u: u.is_staff)
def admin_manage(request):
    if request.POST:
        form = ManageForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            s = cd['store']
            m = cd['meal']
            
            store = Store.objects.get(id=s)
            recipe = Recipe.objects.get(id=m)
            cp = CurrentPromo.objects.filter(store=store)
            
            if len(cp) > 0:
                cp[0].promo = recipe
                cp[0].save()
            else:
                cp = CurrentPromo(store=store,promo=recipe)
                cp.save()
    else:
        form = ManageForm()
        
    template = 'commerce/admin/admin_manage.html'
    data = {'form':form}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""
Administrative functions
- Generate new codes  
"""
@user_passes_test(lambda u: u.is_staff)
def admin_generate_code(request):
    if request.POST:
        da = request.POST.get('discount_percent')
        discount = Decimal(da)
        new_code = "".join([random.choice(string.letters+string.digits) for x in range(1,9)])
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        
        coupon_code = CouponCode(code=new_code, discount_percent=discount, coupon_used=False, created_on=now)
        coupon_code.save()
    
    all_coupons = CouponCode.objects.all()
    template = 'commerce/admin/admin_gen_discount.html'
    data = {'all_coupons': all_coupons }
    
    return render_to_response(template, data,context_instance=RequestContext(request))