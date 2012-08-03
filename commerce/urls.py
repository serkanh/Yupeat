from django.conf.urls.defaults import *
from commerce.views import *

urlpatterns = patterns('',
    url(r'^admin/all/$',admin_all,name='edit_all'),
    url(r'^admin/schedule/$',admin_promo_schedule,name='promo_schedule'),
    url(r'^admin/schedule/(?P<store_id>\d+)/(?P<date>\S+)/$',admin_promo_schedule,name='promo_schedule'),
    url(r'^admin/schedule/(?P<store_id>\d+)/$',admin_promo_schedule,name='promo_schedule'),
    url(r'^admin/promoemail/(?P<promo_id>\d+)/$',admin_promo_email,name='promo_email'),
    url(r'^admin/promoemail/(?P<promo_id>\d+)/(?P<email_form_id>\d+)/$',admin_promo_email,name='promo_email'),
    url(r'^admin/promoemail/sendzip/(?P<promo_email_id>\d+)/$',admin_sendzip_chimp,name='send_zip'),
    url(r'^admin/remote_fetch_zip/(?P<promo_email_id>\d+)/$', remote_fetch_zip, name='fetch_zip'),
    url(r'^admin/coupon/$',admin_generate_code,name='generate_coupon'),
    
    url(r'^admin/track/$',admin_track_orders,name='track'),
    url(r'^admin/track/(?P<store_id>\d+)/$',admin_track_orders,name='track'),
    url(r'^admin/soldout/$',admin_soldout,name='soldout'),
    url(r'^admin/soldout/(?P<store_id>\d+)/$',admin_soldout,name='soldout'),
    url(r'^admin/manage/$',admin_manage,name='manage'),
    url(r'^admin/new/$',new_meal,name='new_meal'),
    url(r'^admin/edit/(?P<recipe_id>\d+)/$',edit_meal,name='edit_meal'),
    url(r'^admin/delete/(?P<recipe_id>\d+)/$',delete_meal,name='delete_meal'),
    url(r'^admin/store/$',admin_store,name='edit_store'),
    url(r'^admin/store/all/$',admin_store_all,name='store_all'),
    url(r'^admin/store/edit/(?P<store_id>\d+)/$',admin_store_edit,name='edit_store'),
    url(r'^admin/store/delete/(?P<store_id>\d+)/$',admin_store_delete,name='delete_store'),
    
    url(r'^admin/buynow-urls/$',admin_order_eligiblesite,name='track'),
    
    #url(r'^rsvp/$', dinner_party_rsvp, name='rsvp'),
    
    url(r'^ajax/change-location/$',ajax_change_location,name='ajax_change_location'),
    url(r'^ajax/apply-coupon/$',ajax_apply_coupon,name='ajax_apply_coupon'),
    url(r'^ajax/remove-coupon/$',ajax_remove_coupon,name='ajax_remove_coupon'),
    
    url(r'^$', select_city, name='order'),
    url(r'^soldout/$', order_soldout, name='order_soldout'),
    url(r'^complete/$', order_complete, name='order_complete'),
    url(r'^cancel/$', order_cancel, name='order_complete'),
    url(r'^popup/$', order_popup, name='order_popup'),
    
    url(r'^(?P<city>\w+)/(?P<id>\d+)/$', order, name='order'),
    url(r'^(?P<city>\w+)/$', order, name='order'),
       
)