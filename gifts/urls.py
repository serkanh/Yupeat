from django.conf.urls.defaults import *
from gifts.views import *

urlpatterns = patterns('',
    url(r'^$', gift_subscription, name='gift'),
    url(r'^redeem-now/$',redeem_now,name='redeem-now'),
)