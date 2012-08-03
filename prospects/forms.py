from django.forms import ModelForm
from prospects.models import Prospect
# Create the form class.

class ProspectForm(ModelForm):
    class Meta:
        model = Prospect
        fields = ('email','postal_code')


