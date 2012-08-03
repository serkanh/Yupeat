from django.forms import ModelForm
from cdn.models import CDN

class ImageForm(ModelForm):
    error_css_class = 'error'
    class Meta:
        model = CDN
        fields = ('name', 'image')
        
