from django.db import models
from uprofile.models import UserProfile
from django.contrib.auth.models import User

class GiftSubscription(models.Model):
    givername = models.CharField(max_length=500)
    giveremail = models.EmailField(max_length=500)
    receivername = models.CharField(max_length=500)
    receiveremail = models.EmailField(max_length=500)
    giftuser = models.ForeignKey(User, blank=True, null=True)
    giftused =  models.BooleanField()
    gifttoken = models.CharField(max_length=50, blank=True, null=True)
    message = models.TextField(max_length=5000, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True, blank=True, null=True)