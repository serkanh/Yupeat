from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from uprofile.models import UserProfile

from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse

from django.utils import simplejson
from django.conf import settings

from django.core import serializers
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from geopy import geocoders

from meals.models import Recipe
from uprofile.views import getUser
from uprofile.models import Invitation, OrderHistory, Subscription

from commerce.views import confirmation_email, admin_alert_email
from commerce.views import getMeal, getLatestMeal, sub_to_store, getTime, generateItemDict, isSubscriber, getDay
from commerce.views import getExclude, nonexcluded_item_dict, get_items_latest_price, get_currentday_promo, get_latest_promo

from commerce.models import Store, PromoEmail, PromoSchedule

from google.appengine.api import images
from datetime import datetime, date, timedelta

from decimal import *
import re
from pytz import timezone, UTC

import stripe
import logging

from mailsnake import MailSnake

"""
SimpleJSON update - allows for decimals   
"""
class MyJSONEncoder(simplejson.JSONEncoder):

   """JSON encoder which understands decimals."""
   def default(self, obj):
       '''Convert object to JSON encodable type.'''
       if isinstance(obj, Decimal):
           return "%.2f" % obj
       return simplejson.JSONEncoder.default(self, obj)
   
"""
BLANK test API   
"""
def api_order_test(request, city):
    data = {}
    
    return HttpResponse(
        simplejson.dumps(data, use_decimal=True),
        content_type = 'application/javascript; charset=utf8'
    )


"""
API for ADDING CARD   
"""
@csrf_exempt
def api_add_card(request):
    if request.POST:
        userid = request.POST.get('userid')
        
        token = request.POST.get('stripeToken')
        customer = request.POST.get('stripeCustomer')
        firstname = request.POST.get('firstname')
        lastname = request.POST.get('lastname')
        address1 = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip = request.POST.get('zip')
        phone = request.POST.get('phone')
        
        try:
            stripe.api_key = settings.STRIPE_API_KEY
            customer = stripe.Customer.retrieve(customer)
            customer.card = token
            customer.save()
        
        
            card_type = customer.active_card.type
            card_num = customer.active_card.last4
            card_year = customer.active_card.exp_year
            card_month = customer.active_card.exp_month
            
            card = {}
            
            user = User.objects.get(id=int(userid))
            up = user.get_profile()
            
            """Save User Data"""
            up.name = firstname + ' ' +lastname 
            up.address_line1 = address1
            up.address_city = city
            up.address_state = state
            up.address_zip = zip
            up.phone = phone
            up.save()
            
            pacific = timezone('US/Pacific')
            lu = up.timestamp
            lu.replace(tzinfo=pacific)
            last_update = lu.strftime('%Y-%m-%dT%H:%M:%S%z')
            
            ms = user.date_joined
            ms.replace(tzinfo=pacific)
            member_since = ms.strftime('%Y-%m-%dT%H:%M:%S%z')
            
            
            """Prepare response object"""
            up_details = {}
            up_details['address'] = up.address_line1
            up_details['type'] = customer.active_card.type
            up_details['number'] = 'xxx-%s' % customer.active_card.last4
            up_details['cvc'] = ''
            up_details['state'] = up.address_state
            up_details['city'] = up.address_city
            up_details['zip'] = up.address_zip
            up_details['country'] = 'USA'
            up_details['cts'] = member_since
            up_details['uts'] = last_update
            up_details['fname'] = up.name
            up_details['lname'] = ''
            up_details['stripeid'] = up.stripeprofile
            
            expiry = '%s/%s' % (customer.active_card.exp_month, customer.active_card.exp_year)
            up_details['expiry'] = expiry
            
            code = 200
            data = {'code':code, 'card': up_details}
        except stripe.InvalidRequestError:
            code = 100
            data = {'code':code, 'error': 'Invalid Credit Card'}
    else:
        code = 100
        data = {'code':code, 'error': 'Not a Post Request'}
         
    return HttpResponse(simplejson.dumps(data, cls=MyJSONEncoder),content_type = 'application/javascript; charset=utf8')
    
"""
API for handling COMPLETED ORDER   
"""
@csrf_exempt
def api_complete_order(request):
    if request.POST:
        pickup_time = request.POST.get('pickup_time')
        s = request.POST.get('store')
        
        store_dict = simplejson.loads(s)
        
        store_id = store_dict['storeid']
        store = Store.objects.get(id=int(store_id))
        
        user_id = request.POST.get('userid')
        user = User.objects.get(id=int(user_id))
        user_profile = user.get_profile()
        
        phone = request.POST.get('phone')
        user_profile.phone = phone
        user_profile.save()
        
        customer_id = request.POST.get('customer')
        pi = request.POST.get('items')
        
        items = simplejson.loads(pi)
        purchased_items = {}
        for ida in items:
            selected = ida['selected']
            if int(selected) == 1:
                name = ida['name']
                value = ida['price'] 
                purchased_items[name] = value
            
        
        promo_id = request.POST.get('promoid')
        ps = PromoSchedule.objects.get(id=int(promo_id))
        
        recipe_id = ps.recipe.id
        recipe = Recipe.objects.get(id=recipe_id)
        
        amount = request.POST.get('amount')
        total = int(Decimal(amount) * 100)
        
        stripe.api_key = settings.STRIPE_API_KEY
        
        customer = stripe.Customer.retrieve(customer_id)
        if customer:
            charge = stripe.Charge.create(amount=total,currency='usd', customer=customer.id)
         
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
            
        oh = OrderHistory(userprofile=user_profile, date=now, meal=recipe, charge=charge.id, 
                              promo=ps, amount=Decimal(amount), pickuptime=pickup_time)
        oh.save()
        
        pickup_day = getDay()
        
        """notify admin and user"""
        data = {'pickup_time':pickup_time, 'pickup_day':pickup_day, 'user':user,
                    'store':store, 'recipes':[recipe], 'items':purchased_items, 
                    'recipe_id':recipe_id, 'charged':Decimal(amount)}
            
        confirmation_email(user, data, pickup_day)
        admin_alert_email(user,data,pickup_time)
        
        code = 200
        data = {'code':code, 'account': {}}
    else:
        code = 100
        data = {'code':code, 'error': 'Failed: Requires Post Request'}
        
    return HttpResponse(simplejson.dumps(data, cls=MyJSONEncoder),content_type = 'application/javascript; charset=utf8')

"""
API for handling SIGN UP   
"""
@csrf_exempt
def api_createuser(request):
    code = 100
    data = {'code':code, 'error': 'Request Error'}
    
    if request.POST:
        if 'name' in request.POST and 'email' in request.POST and 'password' in request.POST:
            name = request.POST['name']
            email_x = request.POST['email']
            password = request.POST['password']
            
            email = email_x.lower()
            
            if validateEmail(email):
                ck_u = User.objects.filter(email=email)
                if len(ck_u) > 0: 
                    existing_user = True
                    code = 100
                    data = {'code':code, 'error': 'User Already Exists'}
                else:
                    existing_user = False
                    u = User(username=email, password=password, email=email)
                    u.save()
                
                    """create invitation"""
                    store = Store.objects.filter(active=True,city='San Francisco')[0]
                    inv = Invitation(user=u, default_store=store, email=u.username, used=True)
                    inv.save()
                    
                    up = UserProfile(user=u, default_store=store)
                    up.save()
                    
                    """create default subscription"""
                    sub = Subscription(userprofile=up, subscription=False, subscription_type='un-subscribed')
                    sub.save()
                    
                    """Send admin email"""
                    sendSignupAdminEmail(u, 'San Francisco')
                    
                    """Send user email"""
                    sendWelcomeEmail(email,'sanfrancisco', 'San Francisco')
                    
                    """subscribe user to daily email"""
                    LIST_IDS = {'san-francisco':'eaa0a378ba'}
                    l_id = LIST_IDS['san-francisco']
                    
                    ms = MailSnake(settings.MAILCHIMP_API_KEY)
                    success = ms.listSubscribe(id=l_id, email_address=u.email, double_optin=False)
                    
                    d, code = api_auth_helper(u)
                    code = 200
                    data = {'code':code, 'account':d['account']}
            else:
                code = 100
                data = {'code':code, 'error': 'Invalid Email'}
        else:
            code = 100
            data = {'code':code, 'error': 'Invalid Sign-up'}
          
    return HttpResponse(simplejson.dumps(data, cls=MyJSONEncoder),content_type = 'application/javascript; charset=utf8')

"""
API for handling LOG IN   
"""
@csrf_exempt
def api_authentication(request):
    if request.POST:
        if 'username' in request.POST and 'password' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            
            user = authenticate(username=username, password=password)
            
            data, code = api_auth_helper(user)
        else:
            data = {'code':100, 'error': 'Invalid Login'}
            
    else:
        data = {'code':100, 'error': 'Invalid Login'}
        
    return HttpResponse(simplejson.dumps(data, cls=MyJSONEncoder),content_type = 'application/javascript; charset=utf8')

"""
Helper function for setting up LOG IN/SIGN UP return object   
"""
def api_auth_helper(user):
    customer = None
    customer_id = None
    
    if user:
        try:
            up = user.get_profile()
            customer_id = up.stripeprofile
            stripe.api_key = settings.STRIPE_API_KEY
            
            """create customer if they do not exist"""
            if customer_id:
                customer = stripe.Customer.retrieve(customer_id)
            else:
                desc = "New customer created for %s" % user.username
                c =  stripe.Customer.create(description=desc)
                up.stripeprofile = c.id
                up.save()
            
            pacific = timezone('US/Pacific')
            lu = up.timestamp
            lu.replace(tzinfo=pacific)
            last_update = lu.strftime('%Y-%m-%dT%H:%M:%S%z')
            
            ms = user.date_joined
            ms.replace(tzinfo=pacific)
            member_since = ms.strftime('%Y-%m-%dT%H:%M:%S%z')
            
            up_details = {}
            account_dict = {}
            card = {}
            try:
                up_details['address'] = up.address_line1
                
                up_details['type'] = customer.active_card.type
                up_details['number'] = 'xxx-%s' % customer.active_card.last4
                up_details['cvc'] = ''
                
                up_details['state'] = up.address_state
                up_details['city'] = up.address_city
                up_details['zip'] = up.address_zip
                up_details['country'] = 'USA'
                up_details['cts'] = member_since
                up_details['uts'] = last_update
                up_details['fname'] = up.name
                up_details['lname'] = ''
                up_details['stripeid'] = up.stripeprofile
                
                expiry = '%s/%s' % (customer.active_card.exp_month, customer.active_card.exp_year)
                up_details['expiry'] = expiry
                
                card[customer.active_card.last4] = up_details 
            
            except AttributeError:
                """no customer card on file"""
                pass
            
            se = datetime.now(pacific) + timedelta(days=14) 
            session_expires = se.isoformat()
            ssid = se.strftime('%Y%m%dT%H%M%S%z')
            
            account_dict['uts'] = last_update
            account_dict['email'] = up.user.email
            account_dict['name'] = up.name
            account_dict['session'] = {'expires':session_expires,'ssid':ssid}
            account_dict['cts'] = member_since
            account_dict['stripeid'] = up.stripeprofile
            
            profile = {}
            s = Subscription.objects.get(userprofile=up)
            profile['username'] = user.username
            profile['subscription_type'] = s.subscription_type
            profile['subscription'] = s.subscription
             
            id = user.id
            
            if len(card) > 0:
                account = {'basic':account_dict, 'cards':card, 'id':id, 'profile':profile}
            else:
                account = {'basic':account_dict, 'id':id, 'profile':profile}
            
            code = 200
            data = {'account':account,'code':code}
        
        except UserProfile.DoesNotExist:
            code = 100
            data = {'code':code, 'error': 'User Profile Does Not Exist'}
            pass
        
        
        return data, code
    else:
        code = 100
        data = {'code':code, 'error': 'Invalid Username/Password'}
        return data, code 

"""
API handles the sending of MEAL DATA   
"""
@csrf_exempt  
def api_order(request, city):
    #Check cache 
    from google.appengine.api import memcache
    
    pacific = timezone('US/Pacific')
    now = datetime.now(pacific)
    tomorrow = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=pacific)
    
    td = tomorrow-now
    expire = td.seconds
    
    order = memcache.get("latest_order-1")
    #if current_order(order):
    if False:
        return HttpResponse(order,content_type = 'application/javascript; charset=utf8')
    else:
        user = getUser(request)
        id = None
               
        """Get Meal"""
        selected_recipes, item_dict, total = getMeal(city, id)
        if selected_recipes:
            r = selected_recipes[0]
        else:
            #get earliest from previous day
            selected_recipes, item_dict, total = getLatestMeal(city,id)
            r = selected_recipes[0]
        
        servings = r.serv
        cooktime = r.cooktime
        name = r.name
        
        """Get Directions """
        #Check for direction sections - looks for <u> tag
        directions = r.dirfull
        dirfull_dict = format_directions(directions)
        
        """Get Service fee """
        service_fee = '3.99'
        if user:
            subscribed = isSubscriber(user)
            if subscribed:
                service_fee = '0.00'
            
        """Get Ingredients """
        #Check for direction sections - looks for <u> tag
        ingredients = r.ingrfull
        ingrfull_dict = format_ingredients(ingredients)
       
        
        """Get all stores"""
        from django.core import serializers
        data = serializers.serialize("json", Store.objects.filter(city='San Francisco', active=True),fields=('store_name','street1','city','state','postal_code','lat','lng'))
        sdata = simplejson.loads(data)
        stores = []
        for s in sdata:
            f = s['fields']
            store_dict = {}
            store_dict['storeid'] = s['pk']
            store_dict['name'] = f['store_name']
            store_dict['street'] = f['street1']
            store_dict['city'] = f['city']
            store_dict['state'] = f['state']
            store_dict['state'] = f['state'] 
            store_dict['country'] = 'United States'
            store_dict['zip'] = f['postal_code']
            store_dict['lat'] = f['lat']
            store_dict['lng'] = f['lng']
            
            stores.append(store_dict)
        
        """Get image"""
        image_key = str(r.image.file.blobstore_info.key())
        url_x = images.get_serving_url(image_key)
        url = '%s=s320'% url_x
        
        s1 = Store.objects.all()[2]
        pickuptime = getTime(s1)
        
        code = 200
        
        ps_all = get_currentday_promo('sanfrancisco')
        if ps_all:
            ps = ps_all[0]
        else:
            ps_all = get_latest_promo('sanfrancisco')
            ps = ps_all[0]
        
        #Sample format "2011-11-15T09:58:52-0800"
        
        promo_date_x = ps.date
        pacific = timezone('US/Pacific')
        promo_date = promo_date_x.replace(tzinfo=pacific)
        
        #Need to update
        dt = datetime(year=promo_date.year, month=promo_date.month, day=promo_date.day, hour=16, minute=30, tzinfo=pacific)
        endtime = dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        #Used for testing
        #now = datetime.now(pacific)
        #dt = datetime(year=now.year, month=now.month, day=now.day, hour=16, minute=30, tzinfo=pacific)
        #endtime = dt.strftime('%Y-%m-%dT%H:%M:%S%z')
        
        """Get items for meal"""
        item_array = []
        itemfull_dict = {}
        for k,v in item_dict.items():
            items = {}
            items['name'] = k
            items['price'] = "%.2f" % v
            items['selected'] = inExclude(k)
            
            item_array.append(items)
        
        new_dict = nonexcluded_item_dict(item_dict)
        item_dict, total = get_items_latest_price(new_dict, ps)
        
        price = total/r.serv
        price_per = ("%.2f" % price)
        
        total_x = ("%.2f" % total)
        
        pe = PromoEmail.objects.get(promoschedule=ps)
        summary = pe.meal_summary
        
        id = str(pe.id)
        
        meal_dict = {'image': url, 'cooktime': cooktime,'dirfull':dirfull_dict, 'endtime': endtime,
                      'ingrfull':ingrfull_dict, 'item_selections': item_array, 'name':name, 'promoid':ps.id,
                      'pickuptime':pickuptime, 'price_per':price_per, 'servings':servings, 
                      'stores':stores, 'summary':summary, 'total':total_x, 'id':id, 'service_fee':service_fee} 
        
        data = {'code':code, 'meal':meal_dict}
        order = simplejson.dumps(data, cls=MyJSONEncoder)
        
        memcache.delete("latest_order-1")
        if not memcache.add("latest_order-1", order):
            logging.error("Memcache set failed.")
        
    return HttpResponse(
        order,
        content_type = 'application/javascript; charset=utf8'
    )

"""
Helper for checking whether saved order is the same as cached order   
"""
def current_order(order):
    if order:
        order_dict = simplejson.loads(order)
        meal_dict = order_dict['meal']
        promoid = meal_dict['promoid']
        ps = PromoSchedule.objects.get(id=promoid)
        
        pacific = timezone('US/Pacific')
        now = datetime.now(pacific)
        n_str = "%s%s%s" % (now.year, now.month, now.day)
        
        d = ps.date
        d_str = "%s%s%s" % (d.year, d.month, d.day)
        
        if n_str == d_str:
            return True
        else:
            return False
    else:
        return False
    
"""
Helper for checking whether to deselect items   
"""
def inExclude(item_name):
    excluded = getExclude()
    item_name_x = item_name.replace(' ','-')
    if item_name_x in excluded: 
        return 0
    else:
        return 1

"""
Helper for formatting directions for iPhone   
"""
def format_directions(directions):  
    dir_dict = {}
    dirfull_dict = []
    
    split_on = []
    title = []
    
    
    if directions.find('<u>') != -1:
        #split on title
        regexp = re.compile('<u>(.*?)</u>')
        for m in regexp.finditer(directions):
            split_on.append(m.group())
            title.append(m.group(1))
        
        split_string = '|'.join([words for words in split_on])
        
        dir_array = []
        dir_array_x = re.split(split_string,directions.strip())
        for dax in dir_array_x:
            if dax != "":
                dir_array.append(dax)
            
        #store in dictionary
        i = 0
        for t in title:
            title_dir_dict = {}
            
            title_dir_dict['title'] = t
            
            cleaned_dir = []
            cleaned_dir_x = re.split(r'[\r\n]+', dir_array[i])
            for dx in cleaned_dir_x:
                if dx != "":
                    cleaned_dir.append(dx)
            title_dir_dict['directions'] = cleaned_dir
             
            i+=1 
            dirfull_dict.append(title_dir_dict)
    else:
        dir_dict['directions'] = re.split(r'[\r\n]+', directions)
        dirfull_dict.append(dir_dict)
        
    return dirfull_dict

"""
Helper for formatting ingredients for iPhone   
"""
def format_ingredients(ingredients):  
    ingr_dict = {}
    ingrfull_dict = []
    
    split_on = []
    title = []
    
    if ingredients.find('<u>') != -1:
        #split on title
        regexp = re.compile('<u>(.*?)</u>')
        for m in regexp.finditer(ingredients):
            split_on.append(m.group())
            title.append(m.group(1))
        
        split_string = '|'.join([words for words in split_on])
        
        ingr_array = []
        ingr_array_x = re.split(split_string,ingredients.strip())
        for iax in ingr_array_x:
            if iax != "":
                ingr_array.append(iax)
        
        #store in dictionary
        i = 0
        for t in title:
            title_ingr_dict = {}
            
            title_ingr_dict['title'] = t
            
            cleaned_ingr = []
            cleaned_ingr_x = re.split(r'[\r\n]+', ingr_array[i])
            for ix in cleaned_ingr_x:
                if ix != "":
                    cleaned_ingr.append(ix)
            title_ingr_dict['ingredients'] = cleaned_ingr
             
            i+=1 
            ingrfull_dict.append(title_ingr_dict)
    else:
        ingr_dict['ingredients'] = re.split(r'[\r\n]+', ingredients)
        ingrfull_dict.append(ingr_dict)
        
    return ingrfull_dict

def validateEmail( email ):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email( email )
        return True
    except ValidationError:
        return False

"""Email to Admin"""
def sendSignupAdminEmail(new_p, city):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    location = city
    text_message = 'New User: '+ str(new_p.email) + ' from iPhone' 
        
    admins = ['ray@yupeat.com','jess@yupeat.com']
    #admins = ['ray@yupeat.com']
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()
    
"""Email to users in Yupeat cities"""
def sendWelcomeEmail(email, city, cl_city):
    stores = Store.objects.filter(city=cl_city,active=True)
    
    ctx_dict = {'stores':stores }
    subject = "Yupeat and You!"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/welcome_iphone_email.html',ctx_dict)
    text_message = render_to_string('email/welcome_iphone_email.txt',ctx_dict)
   
    msg = EmailMultiAlternatives(subject, text_message, from_email, [email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()