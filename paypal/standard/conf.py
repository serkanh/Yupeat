from django.conf import settings
import logging

class PayPalSettingsError(Exception):
    """Raised when settings be bad."""
    

TEST = getattr(settings, "PAYPAL_TEST", True)
PAYPAL_HOSTED = getattr(settings, "PAYPAL_HOSTED", False)


RECEIVER_EMAIL = settings.PAYPAL_RECEIVER_EMAIL


# API Endpoints.
POSTBACK_ENDPOINT = "https://www.paypal.com/cgi-bin/webscr"
SANDBOX_POSTBACK_ENDPOINT = "https://www.sandbox.paypal.com/cgi-bin/webscr"
# API Endpoints for hosted solution
HOSTED_POSTBACK_ENDPOINT = "https://securepayments.paypal.com/acquiringweb"
SANDBOX_HOSTED_POSTBACK_ENDPOINT = "https://securepayments.sandbox.paypal.com/acquiringweb?cmd=_hosted-payment"

# Images
IMAGE = getattr(settings, "PAYPAL_IMAGE", "http://images.paypal.com/images/x-click-but01.gif")
SUBSCRIPTION_IMAGE = getattr(settings, "PAYPAL_SUBSCRIPTION_IMAGE", "https://www.paypal.com/en_US/i/btn/btn_subscribeCC_LG.gif")
DONATION_IMAGE = getattr(settings, "PAYPAL_DONATION_IMAGE", "https://www.paypal.com/en_US/i/btn/btn_donateCC_LG.gif")
SANDBOX_IMAGE = getattr(settings, "PAYPAL_SANDBOX_IMAGE", "https://www.sandbox.paypal.com/en_US/i/btn/btn_buynowCC_LG.gif")
SUBSCRIPTION_SANDBOX_IMAGE = getattr(settings, "PAYPAL_SUBSCRIPTION_SANDBOX_IMAGE", "https://www.sandbox.paypal.com/en_US/i/btn/btn_subscribeCC_LG.gif")
DONATION_SANDBOX_IMAGE = getattr(settings, "PAYPAL_DONATION_SANDBOX_IMAGE", "https://www.sandbox.paypal.com/en_US/i/btn/btn_donateCC_LG.gif")

