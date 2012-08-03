from django.conf.urls.defaults import *
from cdn.views import *

urlpatterns = patterns('',
    url(r'^upload/$',upload_to_cdn,name='cdn_upload')
)