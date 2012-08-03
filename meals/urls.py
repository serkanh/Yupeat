from django.conf.urls.defaults import *
from meals.views import *

urlpatterns = patterns('',
    url(r'^details/(?P<recipe_id>\d+)/$', details, name='details'),
)