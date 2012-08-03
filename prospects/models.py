from django.db import models

def pkgen():
    from base64 import b32encode
    from hashlib import sha1
    from random import random
    rude = ('lol',)
    bad_pk = True
    while bad_pk:
        pk = b32encode(sha1(str(random())).digest()).lower()[:6]
        bad_pk = False
        for rw in rude:
            if pk.find(rw) >= 0: bad_pk = True
    return pk

class Prospect(models.Model):
    email = models.EmailField()
    postal_code=models.CharField(max_length=9, blank=True, null=True)
    full_address=models.CharField(max_length=100, blank=True, null=True)
    referral_id = models.CharField(max_length=6, primary_key=True, default=pkgen)
    invite = models.CharField(max_length=6, blank=True, null=True)
    referrer = models.CharField(max_length=50, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return self.email
        