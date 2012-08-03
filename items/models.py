from django.db import models
from meals.models import Recipe 
from commerce.models import PromoSchedule

class Item(models.Model):
    name = models.CharField(max_length=300)
    quantity = models.CharField(max_length=30, blank=True, null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)

class ItemPriceHistory(models.Model):
    promo = models.ForeignKey(PromoSchedule, null=True, blank=True)
    item = models.ForeignKey(Item, null=True, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    

