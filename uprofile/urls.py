from django.conf.urls.defaults import *
from uprofile.views import *
from django.contrib.auth.views import password_reset_confirm

urlpatterns = patterns('',
    url(r'^ajax/signup/$',ajax_signup,name='ajax_signup'),
    url(r'^ajax/prospect/other/$',ajax_prospect_other,name='ajax_prospect_other'),
    url(r'^ajax/prospect/$',ajax_prospect,name='ajax_prospect'),
    url(r'^ajax/login/$',ajax_login,name='ajax_login'),
    
    url(r'^ajax/admin/tab/$',ajax_admin_manage_users,name='admin_tab'),
    url(r'^ajax/admin/tablepage/$',ajax_admin_tablepage,name='admin_tablepage'),
    
    url(r'^admin/all/$',admin_user,name='view_edit_users'),
    url(r'^admin/invite/$',admin_invite,name='invite'),
    
    url(r'^admin/manage/details/(?P<userid>\d+)/$',admin_manage_user_details,name='manage_details'),
    url(r'^admin/manage/$',admin_manage_users,name='manage'),
    
    url(r'^login/$',login_view,name='login'),
    url(r'^logout/$',logout_view,name='logout'),
    url(r'^reset-password/$',reset_password,name='reset_password'),
    url(r'^new-password/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',password_reset_confirm,
        {'post_reset_redirect':'/order/sanfrancisco','template_name':'profile/reset_password_confirm.html'}
        ,name='new_password'),
    url(r'^set-password/$',set_password,name='set_password'),
    url(r'^order-history/$',order_history,name='order_history'),
    url(r'^invite-friend/$',invite_friends,name='invite_friend'),
    url(r'^manage/$',manage,name='profile'),
    
    url(r'^subscribe/(?P<city>\w+)/$',subscribe,name='subscribe'),
    url(r'^subscribe/$',subscribe,name='subscribe'),
    
    url(r'^subscribe/update-cancel/$',subscribe_update_cancel,name='cancel_subscribe'),
)