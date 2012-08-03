from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse, Http404

from commerce.forms import PaymentForm
from commerce.views import Store

from gifts.models import GiftSubscription
from gifts.forms import GiftForm

from uprofile.views import get_rand_token, createStripeCustomer
from uprofile.models import UserProfile, Subscription

from django.contrib.auth.forms import *
from django.contrib.auth.models import User
from django.contrib import messages

from django.template.loader import render_to_string

from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives

import logging
import stripe
import base64

from django.conf import settings
from mailsnake import MailSnake
from datetime import datetime
"""
View for handling gift subscription

"""
def gift_subscription(request):
    init = {'country':'US'}
    
    if request.POST:
        gift = GiftForm(request.POST)
        if gift.is_valid():
            randtoken = get_rand_token()
            
            message = gift.cleaned_data['message']
            givername = gift.cleaned_data['givername']
            giveremail = gift.cleaned_data['giveremail']
            receivername = gift.cleaned_data['receivername']
            receiveremail = gift.cleaned_data['receiveremail']
            
            gs = GiftSubscription(givername=givername,giveremail=giveremail,message=message,
                             receivername=receivername, receiveremail=receiveremail, gifttoken=randtoken)
            gs.save()
            
            #create new user or check if user exists
            email = receiveremail.lower()
            
            #Check if new invite is already a user
            ck_u = User.objects.filter(email=email)
            if len(ck_u) > 0: 
                new_u = ck_u[0]
                up = new_u.get_profile()
            else:    
                new_u = User(username=email, password=randtoken, email=email)
                new_u.save()
                
                store = Store.objects.filter(city='San Francisco')[0]
                up = UserProfile(user=new_u, default_store=store)
                up.save()
                
            gs.giftuser = new_u
            gs.save()
            
            
            #subscribe user with profile
            address_line1 = ''
            address_line2 = ''
            address_city = ''
            address_state = ''
            address_zip = ''

            up_dict = {'name':receivername,
           'address_line1':address_line1,
           'address_line2':address_line2,
           'address_city': address_city,
           'address_state': address_state,
           'address_zip': address_zip }

            stripe.api_key = settings.STRIPE_API_KEY
            
            try:  
                """Check for saved version"""
                user_profile = new_u.get_profile()
                customer_id = user_profile.stripeprofile
                if customer_id:
                    customer = stripe.Customer.retrieve(customer_id)
                else:
                    customer = createStripeCustomer(request, new_u, up_dict, up_exists = True)
            except UserProfile.DoesNotExist:
                """Create new and save """
                customer = createStripeCustomer(request, new_u, up_dict, up_exists = False)
            
            #send gift subscription email
            token = request.POST.get('stripeToken')
            
            descrip = "Gift from %s" % givername
            
            try:
                stripe.Charge.create(
                                    amount=4999,
                                    currency="usd",
                                    card=token, # obtained with stripe.js
                                    description= descrip
                )
                valid=True
                
                """create default subscription"""
                sub = Subscription(userprofile=up, subscription=False, subscription_type='un-subscribed')
                sub.save()
                
                """email gifter & receiver"""
                gifter_receiver_email(giveremail, receiveremail, message, givername, receivername, randtoken)
                
                """email admin"""
                gift_admin_email(givername, giveremail, receivername, receiveremail)
                
                template = 'gifts/gift_subscription_thanks.html'

                data = {'receivername':receivername, 'receiveremail':receiveremail}
                return render_to_response(template, data,context_instance=RequestContext(request))
                
            except stripe.CardError, e: 
                messages.add_message(request, messages.ERROR, e)
                valid = False 
            except stripe.InvalidRequestError, e:
                messages.add_message(request, messages.ERROR, e)
                valid = False
        
        valid = False
        
        error_msg = "Oops. Looks like some of the info below is incorrect"
        messages.add_message(request, messages.INFO, error_msg)
        
        payForm = PaymentForm(initial=init)
        
        template = 'gifts/gift_subscription.html'
        data = {'gift':gift, 'payment':payForm}
        
        return render_to_response(template, data,context_instance=RequestContext(request))
            
    gift = GiftForm()
    payForm = PaymentForm(initial=init)
        
    template = 'gifts/gift_subscription.html'
        
    data = {'gift':gift, 'payment':payForm}
    return render_to_response(template, data,context_instance=RequestContext(request))

def redeem_now(request):
    user = None
    
    token = request.POST.get('token')
    if not token:
        token = request.GET.get('token')
    
    city = 'sanfrancisco'
    #if 'city' in request.GET:
    #    city = request.GET.get('city')
         
    try:
        gift = GiftSubscription.objects.get(gifttoken=token)
        user = gift.giftuser
        request.session['user'] = base64.b16encode(str(user.id))
    except GiftSubscription.DoesNotExist:
        raise Http404
    except:
        raise Http404
    
    if user:        
        if request.POST:
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                
                """Get users default city"""
                up = UserProfile.objects.filter(user=user)
                if up:
                    store = up[0].default_store
                    c = store.city
                    city = c.lower().replace(' ','')
                
                """update to gift subscription"""
                gift.giftused = True
                gift.save() 
                
                """update to gift subscription"""
                s_type = "4 month unlimited (gift subscription)"
                sub = Subscription.objects.filter(userprofile=up[0])
                
                if len(sub) > 0:
                    s = sub[0]
                    s.subscription_type = s_type
                    s.subscription = True 
                    s.save()
                else:
                    s = Subscription(userprofile=up, subscription=True, subscription_type=s_type)
                    s.save()
                    
                """subscribe user to daily email"""
                LIST_IDS = {'sflaunch_group':'eaa0a378ba'}
                l_id = LIST_IDS['sflaunch_group']
          
                ms = MailSnake(settings.MAILCHIMP_API_KEY)
                success = ms.listSubscribe(id=l_id, email_address=user.email, double_optin=False)
                
                data = {'user':user, 'city':city}
                template = "gifts/thanks_gift_redeemed.html"
                return render_to_response(template, data,context_instance=RequestContext(request))
        
        else:
            form = SetPasswordForm(user) 
        
        data = {'form':form, 'user':user, 'token':token, 'city':city}
        template = 'gifts/gift_redeem.html'
        
        return render_to_response(template, data, context_instance=RequestContext(request))    

"""Sends subscription email to admin"""
def gift_admin_email(giver, gemail, receiver, remail):
    subject = "New Yupeat GIFT SUBSCRIPTION"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    """send admin email"""
    text_message = 'Gift given by: %s (%s) to %s (%s)' % (str(giver), gemail, str(receiver), remail)
    
    admin_emails = ['ray@yupeat.com','jess@yupeat.com']
    #admin_emails = ['ray@yupeat.com']
    
    admin_msg = EmailMultiAlternatives(subject, text_message, from_email, admin_emails)
    admin_msg.send()

"""Sends subscription confirmation email to user"""
def gifter_receiver_email(giveremail, receiveremail, message, givername, receivername, token):
    url = 'https://yupeat.appspot.com/gifts/redeem-now/?token=%s' % (token)
    
    subject = "You've Received a Yupeat Gift Subscription - 4 Months of Unlimited Service"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    now = datetime.now()
    order_date = now 
    order_number = "%s-%s" % (now.strftime('%d%m%y%H%M'), token)
    
    data = {'receivername':receivername, 'givername':givername, 'message':message, 
            'receiveremail':receiveremail, 'giveremail':giveremail, 'url':url, 
            'order_date':order_date, 'order_number':order_number}
    
    """send recipient gift email"""
    html_message = render_to_string('email/gift_subscription_email.html',data)
    text_message = render_to_string('email/gift_subscription_email.txt',data)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [receiveremail])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()
    
    """send giver email"""
    html_message = render_to_string('email/gift_receipt_email.html',data)
    text_message = render_to_string('email/gift_receipt_email.txt',data)
    
    msg2 = EmailMultiAlternatives(subject, text_message, from_email, [giveremail])
    msg2.attach_alternative(html_message, "text/html")
    
    msg2.send()
    
    