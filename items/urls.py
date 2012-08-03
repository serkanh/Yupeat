from django.conf.urls.defaults import *
from items.views import *

urlpatterns = patterns('',
    url(r'^admin/edit/$',admin_items,name='edit_item'),
    url(r'^admin/all/$',admin_items_all,name='all_items'),
)