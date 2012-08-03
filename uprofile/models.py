from meals.models import Recipe
from items.models import Item
from commerce.models import Store, PromoSchedule

from django.db import models
from django.contrib.auth.models import User

STATUS_OPTIONS = (
      ("U", "Undecided"),
      ("Y", "Yes, count me in"),
      ("N", "No, can't make it"),
  )


class Invitation(models.Model):
    email = models.CharField(max_length=50, blank=True, null=True)
    user = models.ForeignKey(User)
    default_store = models.ForeignKey(Store, blank=True, null=True)
    token = models.CharField(max_length=50, blank=True, null=True)
    used = models.BooleanField()
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)
    
class UserProfile(models.Model):
    user = models.ForeignKey(User)
    stripeprofile = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=100, blank=True, null=True)
    address_line2 = models.CharField(max_length=100, blank=True, null=True)
    address_city = models.CharField(max_length=100, blank=True, null=True)
    address_state = models.CharField(max_length=10, blank=True, null=True)
    address_zip = models.CharField(max_length=20, blank=True, null=True)
    default_store = models.ForeignKey(Store, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True) 
    
class Subscription(models.Model):
    userprofile = models.ForeignKey(UserProfile)
    subscription = models.BooleanField()
    subscription_type = models.CharField(max_length=100, blank=True, null=True)
    subscribtion_date = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)
    
class CouponCode(models.Model):
    userprofile = models.ForeignKey(UserProfile, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, null=True) 
    coupon_used = models.BooleanField()
    created_on = models.DateTimeField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)

"""START - NOT IN USE"""   
class DinnerParty(models.Model):
    promo = models.ForeignKey(PromoSchedule, blank=True, null=True)
    host = models.ForeignKey(User, blank=True, null=True)
    message = models.TextField(max_length=2500, blank=True, null=True)
    stripetoken = models.CharField(max_length=100, blank=True, null=True)
    
class DinnerPartyList(models.Model):
    dinnerparty = models.ForeignKey(DinnerParty, blank=True, null=True)
    guest = models.ForeignKey(User, blank=True, null=True)
    status = models.CharField(max_length=1, blank=True, null=True, choices=STATUS_OPTIONS)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)    

"""END - NOT IN USE"""

class Vote(models.Model):
    name = models.CharField(max_length=500)
    url = models.CharField(max_length=1000,blank=True, null=True)
    count = models.IntegerField(blank=True, null=True)
    contributor = models.ForeignKey(UserProfile, blank=True, null=True)
    featured = models.BooleanField()
    created_on = models.DateTimeField(blank=True, null=True)

class VoteHistory(models.Model):
    vote = models.ForeignKey(Vote)
    userprofile = models.ForeignKey(UserProfile)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)

class OrderHistory(models.Model):
    userprofile = models.ForeignKey(UserProfile)
    meal = models.ForeignKey(Recipe)
    charge = models.CharField(max_length=100, blank=True, null=True)
    promo = models.ForeignKey(PromoSchedule, blank=True, null=True)
    amount = models.DecimalField(max_digits=64, decimal_places=2, default=0, blank=True, null=True) 
    date = models.DateTimeField(blank=True, null=True)
    pickuptime = models.CharField(max_length=100, blank=True, null=True)
    pickupstore = models.ForeignKey(Store, blank=True, null=True)

class Order(models.Model):
    orderhistory = models.ForeignKey(OrderHistory)
    item = models.ForeignKey(Item)

class SavedTransaction(models.Model):
    user = models.ForeignKey(User)
    charge = models.CharField(max_length=100, blank=True, null=True)
    data = models.TextField(max_length=1500, blank=True, null=True)
    custom = models.TextField(max_length=1500, blank=True, null=True)
    complete = models.BooleanField()

class FriendInvites(models.Model):
    user = models.ForeignKey(User)
    invitation = models.ForeignKey(Invitation)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)

class Favorite(models.Model):
    user = models.ForeignKey(User)
    recipe = models.ForeignKey(Recipe)