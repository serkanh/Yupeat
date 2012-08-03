from django.db import models
from meals.models import Recipe 
from datetime import datetime
from djangotoolbox.fields import BlobField  
from django.contrib.auth.models import User

TIME_CHOICES = (
    (datetime(2011,1,1,16), '4pm'),
    (datetime(2011,1,1,17), '5pm'),
)

class Store(models.Model):
    store_name = models.CharField(max_length=100, unique=True)
    store_description = models.TextField(blank=True, null=True)
    store_email = models.EmailField(blank=True, null=True, max_length=75)
    street1=models.CharField(max_length=50, blank=True, null=True)
    street2=models.CharField(max_length=50, blank=True, null=True)
    city=models.CharField(max_length=50, blank=True, null=True)
    state=models.CharField(max_length=30, blank=True, null=True)
    postal_code=models.CharField(blank=True, null=True, max_length=9)
    country=models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(blank=True, null=True, max_length=30) 
    pickup_time = models.DateTimeField(blank=True, null=True, choices=TIME_CHOICES)
    active = models.BooleanField()
    lat = models.CharField(max_length=30, blank=True, null=True)
    lng = models.CharField(max_length=30, blank=True, null=True)
    
    def __unicode__(self):
        return self.store_name + ', '+ self.city

class PromoSchedule(models.Model):
    store = models.ForeignKey(Store, null=True, blank=True)
    date =  models.DateTimeField(blank=True, null=True)
    recipe = models.ForeignKey(Recipe, null=True, blank=True)
    soldout = models.BooleanField()
    
    def __unicode__(self):
        return self.recipe.name

class PromoEmail(models.Model):
    promoschedule = models.ForeignKey(PromoSchedule, null=True, blank=True)
    campaign_name = models.CharField(max_length=2000)
    campaign_id = models.CharField(max_length=50)
    email_subject = models.CharField(max_length=2000)
    meal_summary = models.TextField(max_length=10000)
    ingr_summary = models.CharField(max_length=500)
    zip_file_key = models.CharField(max_length=1000)
    email_image = BlobField()
    
     
class CurrentPromo(models.Model):
    store = models.ForeignKey(Store, null=True, blank=True)
    promo = models.ForeignKey(Recipe, null=True, blank=True)
    
class CustomPromo(PromoSchedule):
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)

class OrderEligibleSite(models.Model):
    url = models.CharField(max_length=1000,blank=True, null=True)
    active = models.BooleanField()
    dateadded =  models.DateTimeField(auto_now=True, blank=True, null=True)
    
    
