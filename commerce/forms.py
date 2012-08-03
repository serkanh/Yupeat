from django import forms
from django.forms import ModelForm
from django.forms.widgets import RadioSelect

from meals.models import Recipe
from commerce.models import Store, CurrentPromo, PromoSchedule, PromoEmail, OrderEligibleSite
from commerce.fields import CreditCardField, ExpiryDateField, VerificationValueField
from countries import countries

class SoldoutForm(ModelForm):
    class Meta:
        model = PromoSchedule
        fields = ('soldout',)
        
class ScheduleRecipeForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ScheduleRecipeForm, self).__init__(*args, **kwargs)
        self.fields['meal'].choices = [('', '----------')] + [(recipe.id, recipe.name) for recipe in Recipe.objects.all()]
        self.fields['meal'].label = ""
        
    meal = forms.ChoiceField(widget=forms.Select())

class ManageForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ManageForm, self).__init__(*args, **kwargs)
        self.fields['store'].choices = [('', '----------')] + [(store.id, store.store_name+', '+store.city) for store in Store.objects.all()]
        self.fields['meal'].choices =  [(recipe.id, recipe.name) for recipe in Recipe.objects.all()]
    
    store = forms.ChoiceField(label = 'Store', widget=forms.Select())
    meal = forms.ChoiceField( widget=RadioSelect())
    
class OfferForm(ModelForm):
    error_css_class = 'error'
    ingrfull = forms.CharField(label='Ingredients', widget=forms.Textarea(attrs={'wrap': 'off'}))
    dirfull = forms.CharField(label='Directions', required=False, widget=forms.Textarea())
    attribution = forms.CharField(label='Attribution', required=False)
    serv = forms.IntegerField(label='Servings', required=False)
    
    class Meta:
        model = Recipe
        fields = ('name', 'image', 'serv', 'cooktime', 'items','ingrfull', 'dirfull', 'attribution', 'image_attribution')

class UpdateImageForm(ModelForm):
    error_css_class = 'error'
    items = forms.CharField(label='Items', widget=forms.HiddenInput())
    ingrfull = forms.CharField(label='Ingredients', widget=forms.HiddenInput())
    dirfull = forms.CharField(label='Directions', required=False, widget=forms.HiddenInput())
    attribution = forms.CharField(label='Attribution', required=False, widget=forms.HiddenInput())
    serv = forms.IntegerField(label='Servings', required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = Recipe
        fields = ('name', 'image', 'serv', 'cooktime', 'items','ingrfull', 'dirfull', 'attribution')

     
class PromoEmailForm(ModelForm):
    email_subject = forms.CharField(widget=forms.Textarea)
    meal_summary = forms.CharField(widget=forms.Textarea)
    
    class Meta:
        model = PromoEmail
        fields = ('campaign_name','email_subject', 'email_image','meal_summary', 'ingr_summary')

class StoreForm(ModelForm):
    error_css_class = 'error'
    class Meta:
        model = Store

class OrderEligibleSiteForm(ModelForm):
    error_css_class = 'error'
    url = forms.CharField(label='Eligible URLs', widget=forms.Textarea(attrs={'wrap': 'off'}))
    
    class Meta:
        model = OrderEligibleSite
        fields = ('url',)
    
CC_CARDS = (
             ("visa", "Visa"),
             ("mastercard", "MasterCard"),
             ("amex", "American Express"),
             ("discover", "Discover"),
             )

class PaymentForm(forms.Form):
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'size':'20', 'title':'First Name'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'size':'20', 'title':'First Name'}))
    street1 = forms.CharField(required=False, widget=forms.TextInput(attrs={'size':'45', 'title':'First Name'}))
    street2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'size':'45', 'title':'Apt, Suite, Bldg, (optional)'}))
    city=forms.CharField(required=True, widget=forms.TextInput(attrs={'size':'20', 'title':'City'}))
    state=forms.CharField(required=True, widget=forms.TextInput(attrs={'size':'5'}))
    postal_code=forms.CharField(required=True, widget=forms.TextInput(attrs={'size':'10', 'title':'Postal Code'}))
    country=forms.ChoiceField(choices=countries.COUNTRIES)
    credit_type = forms.ChoiceField(choices=CC_CARDS)
    card_number = CreditCardField(required=True, widget=forms.TextInput(attrs={'size':'38', 'title':'Credit Card Number'}))
    expiry_date = ExpiryDateField(required=True)
    card_code = VerificationValueField(required=True, widget=forms.TextInput(attrs={'size':'12', 'title':'Security Code'}))
    