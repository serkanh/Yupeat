from django import forms
from django.forms import ModelForm

from gifts.models import GiftSubscription

class GiftForm(ModelForm):
    error_css_class = 'error'
    givername = forms.CharField(label='Your Name')
    giveremail = forms.CharField(label='Your Email')
    receivername = forms.CharField(label='Recipient Name')
    receiveremail = forms.CharField(label='Recipient Email')
    message = forms.CharField(label='Message (optional)', required=False, widget=forms.Textarea())
    
    class Meta:
        model = GiftSubscription
        fields = ('givername', 'giveremail', 'receivername', 'receiveremail', 'message')
 