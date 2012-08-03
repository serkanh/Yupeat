# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *

import os

DATABASES['default']['HIGH_REPLICATION'] = True

SECRET_KEY = '${e\f(th0DH.JkDrWT^kD#eqooLuNbB/@qDic}q}GKLdh{mN39'

INSTALLED_APPS = (
#   'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'djangotoolbox',
    'mediagenerator',
    'filetransfers',
    'prospects',
    'meals',
    'commerce',
    'items',
    'uprofile',
    # djangoappengine should come last, so it can override a few manage.py commands
    'djangoappengine',
    'paypal.standard.ipn',
)

MIDDLEWARE_CLASSES = (
    'mediagenerator.middleware.MediaMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'subdomain.SubdomainMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
)

AUTOLOAD_SITECONF = 'dbindexes'

# This test runner captures stdout and associates tracebacks with their
# corresponding output. Helps a lot with print-debugging.
TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'

ADMIN_MEDIA_PREFIX = '/media/admin/'
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

ROOT_URLCONF = 'urls'

ROOT_MEDIA_FILTERS = {
    'js': 'mediagenerator.filters.closure.Closure',
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
}

YUICOMPRESSOR_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'pasobella/yuicompressor-2.4.2.jar')

CLOSURE_COMPILER_PATH =  os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'pasobella/compiler.jar')

MEDIA_DEV_MODE = DEBUG
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/media/'

GLOBAL_MEDIA_DIRS = (os.path.join(os.path.dirname(__file__), 'static'),)

_base_main_bundle = (
    'css/ye.css',
    'css/tipsy.css',
    'css/blueprint/src/reset.css',
    'css/blueprint/src/forms.css',
    'css/blueprint/src/grid.css',
    'css/blueprint/src/typography.css',
    'css/blueprint/plugins/buttons/screen.css',
)

MEDIA_BUNDLES = (
    ('main.css',)
        + _base_main_bundle,
    ('main-ie.css',)
        + _base_main_bundle
        + ('css/blueprint/src/ie.css',),
    #('mobile.css',
    #    'mobile/main.css',
    #    'mobile/Parts/Transitions.css',
    # ), 
    ('popup.css',)
        + ('css/ye_popup.css',),
    ('print.css',)
        + ('css/blueprint/src/print.css',),
    ('main.js',
        'js/jquery.js',
        'js/jquery.gmapi.js',
        'js/jquery.watermark.js',
        'js/jquery.store.js',
        'js/slides.min.jquery.js',
        'js/json2.js',
        'js/jquery.countdown.js',
        'js/jquery.xdomainajax.js',
        'js/jquery.tipsy.js',
        'js/ye.js',
    ),
    ('bookmark.js',
     'js/bookmarklet.js',
     ),
    #('mobile.js',
    #    'mobile/main.js',
    #    'mobile/Parts/parts.js',
    #    'mobile/Parts/core/external/sizzle_c.js',
    #),
)

#MEDIA_DEV_MODE = True

COPY_MEDIA_FILETYPES = ('gif', 'jpg', 'jpeg', 'png', 'svg', 'svgz','ico', 'swf', 'ttf', 'otf', 'eot')
GMAPI_MEDIA_PREFIX = '/gmapi/'
GOOGLE_MAPS_API_KEY = 'ABQIAAAA0cpX06xTSo-ogY4hTVCRiRSCXxtWHHj0-TrnDYn_NkVZD5aJiRSUX1Go8fAmyUHcEInZ7mZTB3F3Hw'


PREPARE_UPLOAD_BACKEND = 'filetransfers.backends.delegate.prepare_upload'
PUBLIC_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
PRIVATE_UPLOAD_BACKEND = 'djangoappengine.storage.prepare_upload'
SERVE_FILE_BACKEND = 'djangoappengine.storage.serve_file'

# Activate django-dbindexer if available
try:
    import dbindexer
    DATABASES['native'] = DATABASES['default']
    DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native'}
    INSTALLED_APPS += ('autoload', 'dbindexer',)
    AUTOLOAD_SITECONF = 'dbindexes'
    MIDDLEWARE_CLASSES = ('autoload.middleware.AutoloadMiddleware',) + \
                         MIDDLEWARE_CLASSES
except ImportError:
    pass

DBINDEXER_BACKENDS = (
    'dbindexer.backends.BaseResolver',
    'dbindexer.backends.FKNullFix',
    'dbindexer.backends.InMemoryJOINResolver',
)

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = '587'
EMAIL_HOST_USER = 'yupeat@yupeat.com'
EMAIL_HOST_PASSWORD = "99yuppies"
EMAIL_USE_TLS = 'True'
DEFAULT_FROM_EMAIL = 'yupeat@yupeat.com'

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
STRIPE_API_KEY = 'KcKfkSEQCvRQaffQRAUenU6ngpqrKauj'
#TEST STRIPE ACCOUNT
#STRIPE_API_KEY = '10JYTXhTwH3BDCl2aRClWWGyrwTJYswE'

AUTH_PROFILE_MODULE = 'uprofile.UserProfile'
AUTHENTICATION_BACKENDS = ('uprofile.backends.CaseInsensitiveModelBackend',)

PAYPAL_RECEIVER_EMAIL = "ray@yupeat.com"
#PAYPAL_RECEIVER_EMAIL = "ray_1307056564_biz@yupeat.com"

AUTOLOAD_SITECONF = 'dbindexes'
MAILCHIMP_API_KEY = 'eab1326e9b4a783269dc3f9c0db2e6e3-us2'

LOGIN_URL = '/profile/login/'