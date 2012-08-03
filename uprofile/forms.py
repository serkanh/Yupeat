from django.contrib.auth.forms import UserChangeForm, SetPasswordForm, UserCreationForm, AuthenticationForm
from django import forms

from uprofile.models import UserProfile, Invitation, DinnerParty, DinnerPartyList, Subscription, Vote
from commerce.models import Store 

class MyAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Email"

class MyUserChangeForm(UserChangeForm):

  def __init__(self, *args, **kwargs):
    super(MyUserChangeForm, self).__init__(*args, **kwargs)
    self.fields.pop('username')
    
  class Meta(UserChangeForm.Meta):
    fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['default_store'].choices = [('', '----------')] + [(store.id, store.store_name+', '+store.street1) for store in Store.objects.exclude(active=False)]
        self.fields['default_store'].help_text = "Modify location anytime via user 'Account' page"
        
    default_store = forms.ChoiceField(label = 'Preferred Pick-up Location', widget=forms.Select())
    
    class Meta:
        model = UserProfile
        fields = ('default_store',)

class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['subscription','subscription_type']

class InvitationForm(forms.ModelForm):
    store = forms.ModelChoiceField(queryset=Store.objects.all())
    class Meta:
        model = Invitation
        fields = ['email','store']
    
class DinnerPartyForm(forms.ModelForm):
    class Meta:
        model = DinnerParty
        fields = ['message']

class PartyGuestForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email']

class MyUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = "Email"
        self.fields['username'].help_text = ""
        self.fields['password2'].label = "Confirm your password"

class FriendInvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ['email']
        
class VoteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(VoteForm, self).__init__(*args, **kwargs)
        self.fields['url'].label = "Link"
        self.fields['name'].label = "Title"
        
    class Meta:
        model = Vote
        fields = ['name','url']