from django.shortcuts import redirect, render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings
from django.middleware import csrf

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import user_passes_test, login_required

from django.core.validators import email_re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.models import User
from django.contrib.auth.forms import *
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from django.db.models import Q

from uprofile.forms import *
from uprofile.models import UserProfile, Invitation, FriendInvites, OrderHistory, Subscription, CouponCode
from prospects.models import Prospect
from prospects.forms import ProspectForm

from commerce.forms import PaymentForm
from commerce.models import Store

from paypal.standard.ipn.models import PayPalIPN
from geopy import geocoders
from mygeo.views import getMapMulti 

import stripe
import logging
import base64

import string
import random

from datetime import datetime
from decimal import Decimal

from mailsnake import MailSnake
import operator

"""logic for retrieving user from cookie"""
def getUser(request):
    user = None
    if 'user' in request.session:
        u = base64.b16decode(request.session['user'])
        try:
            user = User.objects.get(id=u)
            if user.is_authenticated():
                return user
        except User.DoesNotExist:
            pass
    return user

"""view for profile/manage page"""
@login_required
def manage(request):
    user = getUser(request)
    
    try:
        up = user.get_profile()
    except UserProfile.DoesNotExist:
        store = Store.objects.all()[0]
        user_profile = UserProfile(user=user, default_store=store)
        user_profile.save()
    
    if request.POST:
        if 'update_profile' in request.POST:
            form = MyUserChangeForm(request.POST)
            if form.is_valid():
                fn = form.cleaned_data['first_name']
                ln = form.cleaned_data['last_name']
                em = form.cleaned_data['email']
                
                user.first_name = fn
                user.last_name = ln
                user.email = em
                
                user.save()
                messages.add_message(request, messages.SUCCESS, 'Updated profile details saved!')
        elif 'change_password' in request.POST:
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.add_message(request, messages.SUCCESS, 'Updated password saved!')
        elif 'update_location' in request.POST:
            store_id = request.POST.get('default_store')
            store = Store.objects.get(id=store_id)
            up.default_store = store
            up.save()
            messages.add_message(request, messages.SUCCESS, 'Updated location saved!')
            admin_email_newlocation(up)
                
    if user:
        if 'city' in request.session:
            city = request.session['city'] 
        else:
            city = 'sanfrancisco'
             
        change_form = PasswordChangeForm(user)
        user_form = MyUserChangeForm(instance=user)
        userprofile_form = UserProfileForm(instance=up)
        sub = Subscription.objects.get(userprofile=up)
        all_coupons = CouponCode.objects.filter(userprofile=up)
        
        template = "profile/profile.html"
        data = {'change_form':change_form, 'user_form':user_form,
                'user':user, 'city':city, 'subscription':sub, 'all_coupons':all_coupons,
                'userprofile_form':userprofile_form, 'profile':up}
    
        return render_to_response(template, data,context_instance=RequestContext(request))
    else:
        return login_view(request)

"""Notify admin of new preferred location"""
def admin_email_newlocation(up):
    subject = "Updated Preferred Location"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    text_message = 'User: '+ str(up.user.email) + ' new location ' + str(up.default_store)
    
    #admins = ['ray@yupeat.com', 'jess@yupeat.com']
    admins = ['ray@yupeat.com']
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()

"""view for profile/order-history page"""
@login_required
def order_history(request):
    user = getUser(request)
    up = UserProfile.objects.get(user=user)
    order = OrderHistory.objects.filter(userprofile=up).order_by('date')
    
    template = 'profile/order_history.html'    
    data = {'order':order}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""returns detailed history of orders"""
#def get_order_details(order, charge_id):
#    return {'order':order, 'day':day, 'amount':amount}

"""temp"""
def load_order_details():
    order = OrderHistory.objects.all()
    for o in order:
        st = False
        pp = False
        
        """check if stripe charge or paypal charge"""
        charge_id = o.charge
        #split on stripe
        ca = charge_id.split('_')
        #split on paypal
        cpa = charge_id.split('-')
        
        if ca[0] == 'ch': st = True
        elif cpa[0] == 'pp': pp = True
        
        if st:
            stripe.api_key = settings.STRIPE_API_KEY
            scharge = stripe.Charge.retrieve(charge_id)
            day = datetime.fromtimestamp(scharge.created)
            amount = Decimal(scharge.amount/100)
            
            o.date = day
            o.amount = amount
            o.save()
        elif pp:
            ppipn = PayPalIPN.objects.filter(invoice=charge_id)[0]
            day = ppipn.created_at
            amount = ppipn.mc_gross
            
            o.date = day
            o.amount = amount
            o.save()



"""view for profile/invite friend page"""
@login_required
def invite_friends(request):
    user = getUser(request)
    
    if request.POST:
        form = FriendInvitationForm(request.POST)
        if form.is_valid():
            c_email = form.cleaned_data['email']
            email = c_email.lower()
            token = get_rand_token()
            
            #Check if new invite is already a user
            ck_u = User.objects.filter(email=email)
            if len(ck_u) > 0: 
                error_msg = "Looks like we already have a user signed up with this email.  Do you have any other friends?"
                messages.add_message(request, messages.INFO, error_msg)
            else:    
                new_u = User(username=email, password=token, email=email)
                new_u.save()
                
                exstng_up = UserProfile.objects.get(user=user)
                ds = exstng_up.default_store
                up = UserProfile(user=new_u, default_store=ds)
                up.save()
                
                c = ds.city.lower()
                city = c.replace(' ','')
                
                #Send invite to friend
                send_invite_email(email, token, city, ds, gift=True, gifter=user.email)
                
                #Notify admin of new invite
                send_admin_new_invite(new_u, user)
                
                inv = Invitation(user=new_u, default_store=ds, email=new_u.username, token=token,used=False)
                inv.save()
                
                invfrnd = FriendInvites(user=user,invitation=inv)
                invfrnd.save()
                
                #assign new user to subscription
                s_type = "1 month unlimited (friend invite)"
                s = Subscription(userprofile=up, subscription=True, subscription_type=s_type)
                s.save()
                
                msg = "Invite to %s sent! Don't stop now, keep inviting friends." % email
                messages.add_message(request, messages.INFO, msg)
    else:
        form = FriendInvitationForm()
    
    invites = FriendInvites.objects.filter(user=user)
    
    template = 'profile/invite_friend.html'    
    data = {'form':form, 'invites':invites }
    return render_to_response(template, data,context_instance=RequestContext(request))

"""view for profile/reset-passwords page"""
def reset_password(request):
    user = getUser(request)
    if request.POST:
        domain = request.META['HTTP_HOST']
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(domain_override=domain, email_template_name='email/password_reset_email.html')
            template = "profile/reset_password_email_sent.html"
            data = {'user':user}
            return render_to_response(template, data,context_instance=RequestContext(request))
        else:
            form = PasswordResetForm()
    else:
        form = PasswordResetForm()
            
    if 'city' in request.session:
        city = request.session['city']
    else:
        city= 'sanfrancisco'
        
    template = "profile/reset_password.html"
    data = {'form':form, 'user':user, 'city':city}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""view for /profile/set-password page"""
def set_password(request):
    user = None
    
    token = request.POST.get('token')
    if not token:
        token = request.GET.get('token')
    
    city = 'sanfrancisco'
    #if 'city' in request.GET:
    #    city = request.GET.get('city')
         
    try:
        inv = Invitation.objects.get(token=token)
        user = inv.user
        request.session['user'] = base64.b16encode(str(user.id))
    except Invitation.DoesNotExist:
        raise Http404
    
    if user:        
        if request.POST:
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                
                inv.used = True
                inv.save()
                
                """Get users default city"""
                up = UserProfile.objects.filter(user=user)
                if up:
                    store = up[0].default_store
                    c = store.city
                    city = c.lower().replace(' ','')
                    
                data = {'user':user, 'city':city}
                template = "profile/thanks_password_updated.html"
                return render_to_response(template, data,context_instance=RequestContext(request))
        
        else:
            form = SetPasswordForm(user) 
        
        data = {'form':form, 'user':user, 'token':token}
        template = 'profile/set_password.html'
        
        return render_to_response(template, data, context_instance=RequestContext(request))

"""view for profile/subscribe/cancel page"""
def subscribe_update_cancel(request):
    user = getUser(request)
    if request.POST:
        if 'cancel_subscribe' in request.POST:
            user_profile = user.get_profile()
            
            #remove subscription
            stripe.api_key = settings.STRIPE_API_KEY
            cu = stripe.Customer.retrieve(user_profile.stripeprofile)
            cu.cancel_subscription()
            
            #remove from email list
            LIST_IDS = {'sflaunch_group':'eaa0a378ba'}
            l_id = LIST_IDS['sflaunch_group']
              
            ms = MailSnake(settings.MAILCHIMP_API_KEY)
            success = ms.listUnsubscribe(id=l_id, email_address=user.email, send_notify=False)
            
            #email admin / email user
            subscription_cancel_email(user.email)
            
            #update userprofile
            sub = Subscription.objects.get(userprofile=user_profile)
            sub.subscription = False
            sub.subscription_type = 'canceled'
            sub.save()
            messages.add_message(request, messages.SUCCESS, 'Subscription canceled!')
        
            return redirect('/profile/manage')
        
        elif 'update_stripe_cc' in request.POST:
            updateStripecc_Subscription(request)
            messages.add_message(request, messages.SUCCESS, 'Credit card updated!')
        
    template = 'profile/subscribe_update_cancel.html'
    
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
    
    data = {'customer':customer, 'change_card':change_card, 'payment':payForm, 'user':user}
    
    return render_to_response(template, data, context_instance=RequestContext(request))

"""Sends subscription canceled email to admin and user"""
def subscription_cancel_email(email):
    subject = "Yupeat Subscription Canceled"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    """send user email"""
    data = {}
    html_message = render_to_string('email/cancel_email.html',data)
    text_message = render_to_string('email/cancel_email.txt',data)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()
    
    """send admin email"""
    text_message = 'Canceled User: '+ str(email)
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']

    admin_msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    admin_msg.send()
    

"""view for profile/subscribe page"""
def subscribe(request,city=None):
    user = getUser(request)
    if request.POST:
        cs = createStripe_Subscription(request)
        up = user.get_profile()
        
        
        store_id = request.POST.get('default_store')
        if store_id:
            store = Store.objects.get(id=int(store_id))
        else:
            store = Store.objects.filter(city='San Francisco')[0]
        up.default_store = store
        up.save()  
        
        """generate discount code"""
        discount = Decimal('0.5')
        new_code = "".join([random.choice(string.letters+string.digits) for x in range(1,9)])
        coupon_code = CouponCode(code=new_code, discount_percent=discount, userprofile=up, created_on=datetime.now())
        coupon_code.save()
        
        #email admin
        subscription_admin_email(user.email)
        
        #email user
        subscription_user_email(user.email, coupon_code.code)
        
        return redirect('/profile/manage')
        
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
    
    if city == None:
        city = 'sanfrancisco'
        
    LOCATIONS = {'sanfrancisco':'San Francisco'}
    STATE = {'sanfrancisco':'CA'}
    
    store_city = LOCATIONS[city]
    store_state = STATE[city]
    store_all = Store.objects.filter(city=store_city, active=True)
    
    location_form = UserProfileForm()
    mapForm = createMapMulti(store_all, store_city, store_state, largeMap=True, zoomControl=True, panControl=True)
    
    
    template = 'profile/subscribe_v2.html'
    data = {'payment':payForm, 'customer':customer, 'change_card':change_card, 
            'map':mapForm, 'user':user, 'store_all':store_all, 'location_form':location_form}
    
    return render_to_response(template, data, context_instance=RequestContext(request))


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

"""Sends subscription email to admin"""
def subscription_admin_email(email):
    subject = "New Yupeat SUBSCRIPTION"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    """send admin email"""
    text_message = 'New Paid User: '+ str(email)
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']

    admin_msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    admin_msg.send()

"""Sends subscription confirmation email to user"""
def subscription_user_email(email, coupon_code):
    subject = "Thanks, Your Account's been Upgraded - Unlimited Subscription"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    data = {'coupon_code':coupon_code}
    
    """send user confirmation email"""
    html_message = render_to_string('email/subscription_confirm_email.html',data)
    text_message = render_to_string('email/subscription_confirm_email.txt',data)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()
    
def updateStripecc_Subscription(request):
    user = getUser(request)
    valid = False
    
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
    
    #check if stripe user exists
    #if not create one and get id / if so get id
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
     
    #associate user with plan
    token = request.POST.get('stripeToken')
    
    try:
        customer.update_subscription(plan='unlimited', card=token)
        valid=True
    except stripe.CardError, e: 
        messages.add_message(request, messages.ERROR, e)
        valid = False 
    except stripe.InvalidRequestError, e:
        messages.add_message(request, messages.ERROR, e)
        valid = False
    return valid
    
def createStripe_Subscription(request):
    user = getUser(request)
    valid = False
    
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
    
    #check if stripe user exists
    #if not create one and get id / if so get id
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
     
    #associate user with plan
    token = request.POST.get('stripeToken')
    
    """update stripe customer"""
    if 'change_card' in request.GET:
        customer = stripe.Customer.retrieve(customer.id)
        customer.card = token
        customer.save()
    
    try:
        customer.update_subscription(plan='unlimited')
        
        #get userprofile and associate user profile with subscription type
        subscrip_details = Subscription.objects.filter(userprofile=user_profile)
        if len(subscrip_details) == 0:
            subscrip_details = Subscription(userprofile=user_profile, subscription=True, subscription_type='unlimited')
        else:
            subscrip_details = subscrip_details[0]
            subscrip_details.subscription = True
            subscrip_details.subscription_type = 'unlimited'
        subscrip_details.save()
        
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
        
def login_view(request):
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                
                #save in session
                request.session['user'] = base64.b16encode(str(user.id))
                
                logging.debug(request.POST)
                if request.POST.get('next') != 'None':
                    redirect = request.POST.get('next')
                else:
                    redirect = '/' 
                return HttpResponseRedirect('%s' % (redirect,))
        else:
            error_msg = "Incorrect username/password."
            messages.add_message(request, messages.ERROR, error_msg)
            
            form = MyAuthenticationForm()
            data = {'form':form}
            template = 'profile/login.html'
    else:
        next = '/'
        if request.GET.get('next'):
            next = request.GET.get('next')
        
        form = MyAuthenticationForm()
        
        data = {'form':form, 'next':next}
        template = 'profile/login.html'
    
    return render_to_response(template, data,context_instance=RequestContext(request))
    
    
"""view for profile/logout page"""
def logout_view(request):
    logout(request)
    
    #default_city = 'vancouver'
    #city = default_city
    #if 'city' in request.GET:
    #    city = request.GET['city']
    return HttpResponseRedirect('/')

def is_valid_email(email):
    if email_re.match(email):
        return True
    return False

"""ajax for landing page"""
def ajax_prospect_other(request):
    if request.POST: 
        prospect_email = request.POST.get('email')
        p = Prospect.objects.filter(email=prospect_email)[0]
        
        form = ProspectForm(request.POST)
        if form.is_valid():
            c_postal_code = form.cleaned_data['postal_code']
            
            p.postal_code = c_postal_code
            p.save()  
            
            other = False
            active_city = False
            social = True
            
            prospect_msg = "Thanks! Find us on Facebook and Twitter to stay updated."
            sub_msg = "Invite friends to get an early invite when we make it to your city"
            
            form = ProspectForm()
            social = True
            
            """Send referral email"""
            sendComingSoonEmail(p)
            
            """Send admin referral email"""
            sendOtherSignupAdminEmail(p.email, c_postal_code)
            
            t = 'home/ajax/newprospect_snippet.html'
            d = {'form':form,'prospect_msg':prospect_msg, 'sub_msg':sub_msg, 
                  'active_city':active_city, 'other':other,  
                 'social':social}
            
            rendered = render_to_string(t,d)
            
            return HttpResponse(rendered, status=200)
        
        msg = "Enter valid postal code"
        return HttpResponse(msg, status=403)
        
"""ajax for landing page"""
def ajax_prospect(request, other_submit=False):
    
    if request.POST:
        form = ProspectForm(request.POST)
        
        if form.is_valid():
            c_email = form.cleaned_data['email']
            c_city = request.POST.get('select_city')
            
            if 'other' not in c_city:
                other = False
                active_city = True
                social = False
                
                existing_user = CreateNewUserHelper(request, c_email, c_city)
                
                prospect_msg = "Sweet! You're signed up to start receiving Yupeat service."
                sub_msg = ""
                
                city = c_city.replace('-','')
                t = 'home/ajax/newprospect_snippet.html'
                d = {'prospect_msg':prospect_msg, 'other':other, 'social':social,
                     'active_city':active_city, 'sub_msg':sub_msg, 'city':city}
                rendered = render_to_string(t,d)
                
                return HttpResponse(rendered, status=200)
 
            else:
                #created 'user_email' because of appengine quirk
                p = form.save()
                
                other = True
                active_city = False
                social = False
                
                prospect_msg = "Enter your postal code. Get notified when we make it to your city."
                sub_msg = "Want us in your city now? Be sure to tell all of your friends."
                
                pform = ProspectForm()
                csrf_token = csrf.get_token(request)
                
                t = 'home/ajax/newprospect_snippet.html'
                d = {'form':pform,'prospect_msg':prospect_msg, 'sub_msg':sub_msg, 
                     'csrf_token':csrf_token, 'active_city':active_city, 'social':social, 
                     'other':other, 'prospect':p}
                
                rendered = render_to_string(t,d)
                
                return HttpResponse(rendered, status=200)
            
        else:
            logging.error("request post not valid")
            msg = 'Enter valid email to continue'
    return HttpResponse(msg, status=200)


"""
Helper for creating new user
"""
def CreateNewUserHelper(request, c_email, c_city):
    email = c_email.lower()
    token = get_rand_token()
    
    ck_u = User.objects.filter(email=email)
    if len(ck_u) > 0: 
        existing_user = True
    else:
        existing_user = False
        u = User(username=email, password=token, email=email)
        u.save()
        
        """create invitation"""
        store = Store.objects.filter(active=True,city='San Francisco')[0]
        inv = Invitation(user=u, default_store=store, email=u.username, token=token,used=False)
        inv.save() 
        
        #save in session
        request.session['user'] = base64.b16encode(str(u.id))
        
        CITY_LIST = {"san-francisco":'San Francisco'}
        cl_city = CITY_LIST[c_city]
        
        up = UserProfile(user=u, default_store=store)
        up.save()
        
        """create default subscription"""
        sub = Subscription(userprofile=up, subscription=False, subscription_type='un-subscribed')
        sub.save()
        
        """Send admin email"""
        sendSignupAdminEmail(u, cl_city)
        
        """Send welcome email to new user"""
        c = cl_city.lower()
        city = c.replace(' ','')
        sendWelcomeEmail(email, token, city, cl_city)
        
        """subscribe user to daily email"""
        LIST_IDS = {'san-francisco':'eaa0a378ba'}
        l_id = LIST_IDS[c_city]
        
        ms = MailSnake(settings.MAILCHIMP_API_KEY)
        success = ms.listSubscribe(id=l_id, email_address=u.email, double_optin=False)
        
    

"""Email to users in Yupeat cities"""
def sendWelcomeEmail(email, token,city, cl_city):
    url = 'https://yupeat.appspot.com/profile/set-password/?token=%s&city=%s' % (token,city)
    stores = Store.objects.filter(city=cl_city,active=True)
    
    ctx_dict = { 'url': url, 'stores':stores }
    subject = "Yupeat and You!"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/welcome_email_v2.html',ctx_dict)
    text_message = render_to_string('email/welcome_email_v2.txt',ctx_dict)
   
    msg = EmailMultiAlternatives(subject, text_message, from_email, [email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

"""Email to users in non-Yupeat cities"""
def sendComingSoonEmail(new_p):
    referral_url = 'https://yupeat.appspot.com/?referral='+new_p.referral_id
    
    ctx_dict = { 'referral_url': referral_url }
    subject = "Yupeat and You - Referral Code!"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/welcome_email.html',ctx_dict)
    text_message = render_to_string('email/welcome_email.txt',ctx_dict)
   
    msg = EmailMultiAlternatives(subject, text_message, from_email, [new_p.email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

"""Email admin of users in non-Yupeat cities"""
def sendOtherSignupAdminEmail(email, postal):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    text_message = 'New User: '+ str(email) + ' @ ' + postal 
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']
        
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()

def sendSignupAdminEmail(new_p, city):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    location = city
    text_message = 'New User: '+ str(new_p.email) + ' in ' + location 
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']
        
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()

"""ajax for login page"""
def ajax_login(request):
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        city = request.POST['city']
        user = authenticate(username=username, password=password)
        
        customer = None
        if user:
            try:
                profile = user.get_profile()
                customer_id = profile.stripeprofile
                stripe.api_key = settings.STRIPE_API_KEY
                customer = stripe.Customer.retrieve(customer_id)
            except UserProfile.DoesNotExist:
                pass
            except AttributeError:
                pass
            
        if user is not None:
            if user.is_active:
                #return modified ajax snippets
                login(request, user)
                
                #save in session
                request.session['user'] = base64.b16encode(str(user.id))
                #logging.debug(request.session['user'])
                #Change payment form depending on location
                if city=='sanfrancisco': init = {'country':'US'}
                else: init = {'country':'CA'}
                    
                payForm = PaymentForm(initial=init)
                
                t1 = 'commerce/ajax/login_snippet.html'
                d1 = {'user':user, 'city':city}
                rendered1 = render_to_string(t1,d1)
                
                t2 = 'commerce/ajax/payment_snippet.html'
                d2 = {'payment':payForm, 'customer':customer}
                rendered2 = render_to_string(t2,d2)
                
                r = rendered1+'::'+rendered2
                
                return HttpResponse(r, status=200)
                
            else:
                #return failed login-signal
                msg = 'Username and/or password is incorrect. Please try again'
        else:
            msg = 'Username and/or password is incorrect. Please try again'
    return HttpResponse(msg, status=403)

"""ajax signup"""
def ajax_signup(request):
    if request.POST:
        new_signup = MyUserCreationForm(request.POST)
        if new_signup.is_valid():
            new_signup.save()
            uname = new_signup.cleaned_data['username']
            
            """set up so username and email are the same"""
            user = User.objects.get(username=uname)
            user.email = uname
            user.save()
            
            """create user profile"""
            store_id = request.POST.get('default_store')
            store = Store.objects.get(id=store_id)
            up = UserProfile(user=user, default_store=store)
            up.save()
            
            """create default subscription"""
            sub = Subscription(userprofile=up, subscription=False, subscription_type='un-subscribed')
            sub.save()
            
            """email admin of new signup"""
            sendSignupAdminEmail(user, store)
            
            """email user with signup information"""
            sendSignupEmail(user, store)
            
            """subscrbe user to daily email"""
            LIST_IDS = {'sflaunch_group':'eaa0a378ba'}
            l_id = LIST_IDS['sflaunch_group']
      
            ms = MailSnake(settings.MAILCHIMP_API_KEY)
            success = ms.listSubscribe(id=l_id, email_address=user.email, double_optin=False)
            
            username = user.username
            password = user.password
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
            
            return HttpResponse('success', status=200)
            
    return HttpResponse('Username is already taken', status=403)

"""invite new user"""
@user_passes_test(lambda u: u.is_staff)
def admin_invite(request):
    if request.POST:
        form = InvitationForm(request.POST)
        if form.is_valid():
            c_email = form.cleaned_data['email']
            email = c_email.lower()
            token = get_rand_token()
            
            u = User(username=email, password=token, email=email)
            u.save()
            
            store = form.cleaned_data['store']
            up = UserProfile(user=u, default_store=store)
            up.save()
            
            """create default subscription"""
            sub = Subscription(userprofile=up, subscription=False, subscription_type='un-subscribed')
            sub.save()
            
            c = store.city.lower()
            city = c.replace(' ','')
            send_invite_email(email, token, city, store)
            
            inv = Invitation(user=u, default_store=store, email=u.username, token=token,used=False)
            inv.save()
            
            """subscrbe user to daily email"""
            LIST_IDS = {'sflaunch_group':'eaa0a378ba'}
            l_id = LIST_IDS['sflaunch_group']
      
            ms = MailSnake(settings.MAILCHIMP_API_KEY)
            success = ms.listSubscribe(id=l_id, email_address=u.email, double_optin=False)
            
    else:
        form = InvitationForm()
    
    invites = Invitation.objects.all()
    
    template = 'profile/admin/admin_invite.html'    
    data = {'form':form, 'invites':invites }
    
    return render_to_response(template,data,context_instance=RequestContext(request))

def get_rand_token():
    return "".join([random.choice(string.letters+string.digits) for x in range(1,7)])

"""Send an invitation email"""
def send_admin_new_invite(new_p, exstng_user):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    text_message = 'New User: '+ str(new_p.email) + ' invited by ' + str(exstng_user)
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']

    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()
    
"""Send an invitation email"""
def send_invite_email(email, token, city=None, store=None, gift=False, gifter=None):
    
    subject = "Yupeat Invitation"
    if gift:
        subject = "A Gift from %s - Yupeat (1 Month Free Subscription)" % gifter
        
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    if not city:
        city = 'sanfrancisco'
    
    url = 'https://yupeat.appspot.com/profile/set-password/?token=%s&city=%s' % (token,city)
    data = {'url':url, 'store':store, 'gift':gift, 'gifter':gifter}
    
    html_message = render_to_string('email/invitation_email.html',data)
    text_message = render_to_string('email/invitation_email.txt',data)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()


"""view for inviting new users"""
@user_passes_test(lambda u: u.is_staff)
def admin_user(request):
    if request.POST:
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = UserCreationForm()        
    
    users = User.objects.all()
    
    template = 'profile/admin/admin_profiles.html'
    data = {'form':form, 'users':users}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""temp / initialize subscribers if subscription=false"""
def init_subscription():
    s_all = Subscription.objects.all()
    for s in s_all:
        if s.subscription == False:
            s.subscription_type = 'non-subscriber'
            s.save()

"""view for managing users"""
@user_passes_test(lambda u: u.is_staff)
def admin_manage_users(request):
    """profile length"""
    u = User.objects.all()
    up_length = len(UserProfile.objects.all())
    
    """invitee length"""
    invite_array = []
    i = Invitation.objects.all()
    invitee_length = len(i)
    
    used = len(Invitation.objects.filter(used=True))
    unused = len(i) - used  
    
    for ii in i:
        invite_array.append(ii.email.lower())
    
    """prospect length"""
    prospect_array= []
    prospect_dict = {}
    p = Prospect.objects.all().order_by('-timestamp')
    for pp in p:
        prospect_array.append(pp.email.lower())
        prospect_dict[pp.email.lower()] = pp.timestamp
    
    uninvited = set(prospect_array) - set(invite_array)
    
    """subscriber length"""
    issubscriber = len(Subscription.objects.filter(subscription=True))
    subscriber = Subscription.objects.all().order_by('subscription_type')
    
    subscriber_page = paginate_helper(subscriber)
    
    template = 'profile/admin/admin_profiles_manage.html'
    data = {'invitees':invitee_length, 'issubscriber':issubscriber, 'used':used,
            'unused':unused, 'profiles':up_length, 'prospects':uninvited, 
            'subscriber':subscriber_page}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

"""ajax helper function for swapping table views"""
@csrf_exempt
def ajax_admin_tablepage(request):
    page_str = request.POST.get('page')
    clicktype = request.POST.get('clicktype')
    profiletab = request.POST.get('profiletab')
    
    if clicktype == 'page_next':
        page = int(page_str)
        
    elif clicktype == 'page_previous':
        page = int(page_str)
        
    template, data = tab_helper(profiletab, page)
    rendered = render_to_string(template, data)
    
    return HttpResponse(rendered, status=200)

"""ajax function for swapping table views"""
@csrf_exempt
def ajax_admin_manage_users(request):
    profiletab = request.POST.get('profiletab')
    template, data = tab_helper(profiletab)  
    
    if template and data:
        rendered = render_to_string(template, data) 
        return HttpResponse(rendered, status=200)
    
    return HttpResponse('Error generating view', status=403)

"""tab helper function for admin manage profile page"""
def tab_helper(profiletab, page=1):
    template = None
    data = None
    
    if profiletab == 'subscribers':
        
        """generate list of subscribers"""
        issubscriber = len(Subscription.objects.filter(subscription=True)) 
        subscriber = Subscription.objects.all().order_by('subscription_type') 
        
        subscriber_pages = paginate_helper(subscriber, page)
        
        template = 'profile/admin/ajax/admin_subscriber_snippet.html'
        data = {'subscriber':subscriber_pages}
        
    elif profiletab == 'prospects' or profiletab == 'invitees':
        """generate list of invitees"""
        invite_array = []
        i = Invitation.objects.all()
        used = len(Invitation.objects.filter(used=True))
        unused = len(i) - used  
        
        for ii in i:
            invite_array.append(ii.email.lower())
                
        prospect_array= []
        prospect_dict = {}
        p = Prospect.objects.all().order_by('-timestamp')
        for pp in p:
            prospect_array.append(pp.email.lower())
            prospect_dict[pp.email.lower()] = pp.timestamp
        
        uninvited = set(prospect_array) - set(invite_array)
        updated_prospect = {}
        for email in uninvited:
            updated_prospect[email] = prospect_dict[email]
        
        sorted_prospects = sorted(updated_prospect.iteritems(), key=operator.itemgetter(1))
        
        if profiletab == 'prospects':
            """generate list of users still waiting (name, waiting how long)"""
            
            template = 'profile/admin/ajax/admin_prospects_snippet.html'
            data = {'prospect_objects':sorted_prospects}
        
        elif profiletab == 'invitees':
            invitee_pages = paginate_helper(i, page)
              
            template = 'profile/admin/ajax/admin_invitee_snippet.html'
            data = {'invitees':invitee_pages}
        
    return template, data


""" helper function pagination"""
def paginate_helper(object, page=1, count=100):
    """add pagination"""
    paginator = Paginator(object, count)
    
    try:
        obj_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        obj_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        obj_page = paginator.page(paginator.num_pages)
    
    return obj_page
    
"""view for managing users details"""
@user_passes_test(lambda u: u.is_staff)
def admin_manage_user_details(request,userid=None):
    u = User.objects.get(id=userid)
    up = u.get_profile()
    
    all_coupons = CouponCode.objects.filter(userprofile=up)      
    s = Subscription.objects.get(userprofile=up)
    
    if request.POST:
        logging.debug(request.POST)
        if 'subscription' in request.POST:
            form = SubscriptionForm(request.POST, instance=s)
            if form.is_valid():
                s_new = form.save(commit=False)
                s_new.userprofile = up
                s_new.save()
                messages.add_message(request, messages.SUCCESS, 'Subscription updated!')    
        if 'discount_percent' in request.POST:
            da = request.POST.get('discount_percent')
            discount = Decimal(da)
            new_code = "".join([random.choice(string.letters+string.digits) for x in range(1,9)])
            coupon_code = CouponCode(code=new_code, userprofile=up, discount_percent=discount, coupon_used=False, created_on=datetime.now())
            coupon_code.save()
     
    form = SubscriptionForm(instance=s)
    
    order_all = OrderHistory.objects.filter(userprofile=up).order_by('date')
    
    template = 'profile/admin/admin_profiles_details.html'
    data = {'order':order_all, 'subscription_form':form, 'all_coupons':all_coupons}
    
    return render_to_response(template, data,context_instance=RequestContext(request)) 
    