from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

from django.views.decorators.csrf import csrf_exempt

from django.conf import settings

from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from django.views.generic.simple import direct_to_template
from filetransfers.api import serve_file, public_download_url

from google.appengine.api import images

from uprofile.forms import MyUserCreationForm, UserProfileForm, VoteForm 
from uprofile.models import UserProfile, Subscription, Vote, VoteHistory
from uprofile.views import getUser

from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from prospects.forms import ProspectForm
from commerce.views import order, createMap, createMapMulti, isWeekend, getMeal
from commerce.models import Store, PromoSchedule, OrderEligibleSite

from django.contrib.auth.models import User

from mediagenerator.templatetags.media import media_url, include_media

from mailsnake import MailSnake
from pytz import timezone
from datetime import datetime
 
import logging
import urllib2
import django.utils.simplejson as json

import base64

"""
Used to display main '/' page
"""
def main(request):
    user = getUser(request)
    
    meal_on = True
    if isWeekend():
        meal_on = False
    
    """Get expiration"""
    pacific = timezone('US/Pacific')
    pa_time = datetime.now(pacific)
    pa = pa_time.strftime('%d,%m,%Y,%B,%A')
    date_array = pa.split(',')
    
    day_as_num = int(date_array[0])
    month_as_num = int(date_array[1]) - 1
    year = date_array[2]
    
    """Get meal"""
    id=None
    store=None
    selected_recipes, item_dict, total = getMeal('sanfrancisco', store, id)
    
    url = None
    r_name = None
    r_attr = None
    if selected_recipes:
        r = selected_recipes[0]
        r_name = r.name
        r_attr = r.attribution
        image_key = str(r.image.file.blobstore_info.key())
        url = images.get_serving_url(image_key)
    else:
        meal_on = False
    
    if request.method == 'POST': 
        prospect = ProspectForm(request.POST) # A form bound to the POST data
        if prospect.is_valid():
            new_p = prospect.save()
            """Save location"""
            try:
                new_p.full_address = request.session['location']
            except KeyError:
                pass
            new_p.save()
            #logging.debug('New address: %s' % new_p.full_address)
            
            """Save referrer"""
            new_p.referrer = request.session['whereFrom']
            new_p.save()
            
            if 'referral' in request.GET:
                new_p.invite = request.GET.get('referral')
                new_p.save()
            
            return thanks_page(request, new_p)
    else:         
        prospect = ProspectForm()
    
    CITY_LIST = ['San Francisco', 'Other']
    
    request.session['whereFrom'] = request.META.get('HTTP_REFERER', '')
    template = 'home/home_current.html'
    
    data = {'user':user, 'form':prospect, 'year':year, 'date_today':pa_time, 'rname':r_name,
            'rattr':r_attr, 'image':url, 'dn':day_as_num, 'mn':month_as_num, 'city_list':CITY_LIST, 
            'meal_on':meal_on}
    
    return render_to_response(template, data,context_instance=RequestContext(request))

def what(request):
     user = getUser(request)
     template = 'home/navigation/what.html'
     data = {'user':user }
     return render_to_response(template, data,context_instance=RequestContext(request))
    
def aboutus(request):
     user = getUser(request)
     template = 'home/navigation/aboutus.html'
     data = {'user':user }
     return render_to_response(template, data,context_instance=RequestContext(request))

def buybutton(request):
     user = getUser(request)
     template = 'home/buybutton.html'
     
     all_sites = OrderEligibleSite.objects.all()
     js_source = media_url('bookmark.js')
     
     #domain = '127.0.0.1:8000'
     domain = '3.yupeat.appspot.com' 
     
     data = {'user':user, 'all_sites':all_sites, 'js_source':js_source, 'domain':domain}
     return render_to_response(template, data,context_instance=RequestContext(request))

def saveLocation(request):
    try:
        request.session['location'] = request.POST.get('address')
    except KeyError:
        pass
    #logging.debug('location information %s' % request.session['location'])
    
    return HttpResponse()

@csrf_exempt
def saveIP(request):
    key = "key=3d666e8b86b7d95c0409a582dd5d867b1be38f12f23f1e86e1c4c96d6f9452c4"
    url = "http://api.ipinfodb.com/v3/ip-city/?"
    format = 'format=json'
    
    ip = str(request.POST.get('ip'))
    
    req = urllib2.Request('%s%s&ip=%s&%s' % (url, key, ip, format))
    opener = urllib2.build_opener()
    f = opener.open(req)
    json = simplejson.load(f)
    
    city = json['cityName']
    state = json['regionName']
    zip =  json['zipCode']
    
    request.session['location'] = city+' '+state+' '+zip 
    #logging.debug('location information %s' % request.session['location'])
    return HttpResponse('Success',status=200)

def thanks_page(request, new_p):
    
    sendWelcomeEmail(new_p)
    sendAdminEmail(new_p)
    
    return HttpResponseRedirect('/thanks')

def sendWelcomeEmail(new_p):
    referral_url = 'https://yupeat.appspot.com/?referral='+new_p.referral_id
    
    ctx_dict = { 'referral_url': referral_url }
    subject = "Yupeat and You!"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/welcome_email.html',ctx_dict)
    text_message = render_to_string('email/welcome_email.txt',ctx_dict)
   
    msg = EmailMultiAlternatives(subject, text_message, from_email, [new_p.email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

def sendAdminEmail(new_p):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    text_message = 'New User: '+ str(new_p.email)
        
    msg = EmailMultiAlternatives(subject, text_message, from_email, ['ray@yupeat.com','jess@yupeat.com'])
    
    msg.send()
    
def signup(request, city):
    LOCATIONS = {'sanfrancisco':'San Francisco'}
    STATE = {'sanfrancisco':'CA'}
    
    store_city = LOCATIONS[city]
    store_state = STATE[city]
    
    store_all = Store.objects.filter(city=store_city, active=True)
    
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
            
            request.session['user'] = base64.b16encode(str(up.user.id))
            
            return HttpResponseRedirect('/profile/subscribe/sanfrancisco')
    
    new_signup = MyUserCreationForm()
    location_form = UserProfileForm()
    
    mapForm = createMapMulti(store_all, store_city, store_state, largeMap=True, zoomControl=True, panControl=True)
        
    template = 'profile/signup.html'
    data = {'new_signup':new_signup, 'store_all':store_all, 'city':city,
                'store_city':store_city, 'location_form':location_form, 'map':mapForm}
    
    return render_to_response(template, data,context_instance=RequestContext(request))


def sendSignupEmail(new_p, store):
    
    ctx_dict = {'store':store}
    subject = "Yupeat and You!"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    html_message = render_to_string('email/signup_email.html',ctx_dict)
    text_message = render_to_string('email/signup_email.txt',ctx_dict)
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, [new_p.email])
    msg.attach_alternative(html_message, "text/html")
    
    msg.send()

def sendSignupAdminEmail(new_p, store):
    subject = "New Sign-up on Yupeat"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    location = str(store.store_name) +' on ' + str(store.street1)
    text_message = 'New User: '+ str(new_p.email) + ' @ ' + location 
    
    #admins = ['ray@yupeat.com','jess@yupeat.com']
    admins = ['ray@yupeat.com']
    
    msg = EmailMultiAlternatives(subject, text_message, from_email, admins)
    
    msg.send()   
    
"""
Used to display main '/vote' page
"""
def vote(request):
    
    user = getUser(request)
    prev_votes = ''
    if user:
        up = user.get_profile()
        prev_votes = VoteHistory.objects.filter(userprofile=up)
    
    logged_in = False
    if user:
        logged_in = True
        
    if request.POST:
        form = VoteForm(request.POST)
        
        if request.user.is_authenticated():
            if form.is_valid():
                """Does URL exist?"""
                c_url = form.cleaned_data['url']
                v = Vote.objects.filter(url=c_url)
                if v:
                    vote = v[0]
                    """check for multiple submissions of the same url"""
                    vh = VoteHistory.objects.filter(vote=vote, userprofile=up)
                    if len(vh) == 0:
                        vote.count += 1
                        vote.save()
                else:
                    vote = form.save()
                    vote.count=1
                    vote.featured=False
                    vote.created_on=datetime.now()
                    vote.contributor = up
                    vote.save()
                    
                    sendVoteAdminEmail(vote, up)
                    
                    vh = VoteHistory(vote=vote,userprofile=up)
                    vh.save()
    else:
        form = VoteForm()
    
    pv_array = []
    for pv in prev_votes:
        pv_array.append(pv.vote.id)
         
    vote = Vote.objects.filter(featured=False).order_by('-count')
    
    data = {'form':form, 'logged_in':logged_in, 'user':user, 'vote':vote, 'prev_votes':pv_array}
    template = "home/vote.html"
    
    return render_to_response(template, data,context_instance=RequestContext(request))

def sendVoteAdminEmail(vote, up):
    subject = "New Meal Submission"
    from_email = "Yupeat <yupeat@yupeat.com>"
    
    text_message = 'New Vote: '+ vote.url + ' by ' + up.user.username 
        
    msg = EmailMultiAlternatives(subject, text_message, from_email, ['ray@yupeat.com','jess@yupeat.com'])
    
    msg.send()

"""
Used to handle votes sent via ajax
"""
@csrf_exempt
def ajax_vote(request):
    user = getUser(request)
    up = user.get_profile()
    
    vv = request.POST.get('vote_val')
    
    varray = vv.split('-')
    vote_id = varray[1]
    
    vote = Vote.objects.get(id=vote_id)
    
    vh = VoteHistory.objects.filter(vote=vote, userprofile=up)
    if len(vh) == 0:
        vote.count += 1
        vote.save()
        
        vh = VoteHistory(vote=vote,userprofile=up)
        vh.save()
        
    return HttpResponse('', status=200)

"""
Used to sort vote results
"""
@csrf_exempt
def ajax_vote_filter(request):
    user = getUser(request)
    prev_votes = ''
    
    if user:
        up = user.get_profile()
        prev_votes = VoteHistory.objects.filter(userprofile=up)
        contrib_votes = Vote.objects.filter(contributor=up)
    
    logged_in = False
    if user:
        logged_in = True
    
    filter_type = request.POST.get('filtertype')
    
    if filter_type == 'recent':
        vote = Vote.objects.filter(featured=False).order_by('-created_on')
    if filter_type == 'topvoted':
        vote = Vote.objects.filter(featured=False).order_by('-count')
    if filter_type == 'pastfeatured':
        vote = Vote.objects.filter(featured=True).order_by('-count')
    if filter_type == 'yourpicks':
        """TEMP - contributor > userprofile"""
        vote = contrib_votes
     
    pv_array = []
    for pv in prev_votes:
        pv_array.append(pv.vote.id)
           
    template = 'home/ajax/vote_list_snippet.html'
    data = {'logged_in':logged_in, 'user':user, 'vote':vote, 'prev_votes':pv_array}
    
    rendered = render_to_string(template,data)
    
    return HttpResponse(rendered, status=200)

def init_featured():
    v_array = []
    v_dict = {}
    
    v_all = Vote.objects.all()
    
    i=0
    for v in v_all:
        u = v.url
        v_array.append(u.strip()) 
        v_dict[i] = v.id
        i+=1
    
    p_all = PromoSchedule.objects.all()
    
    for ps in p_all:
        url_x = ps.recipe.attribution
        url = url_x.strip()
        
        if url in v_array:
            index = v_array.index(url)
            v = Vote.objects.get(id=v_dict[index])
            v.featured = True
            v.save()
        