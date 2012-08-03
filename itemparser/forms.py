from django import forms

class ParseForm(forms.Form):
    ingredients =  forms.CharField()