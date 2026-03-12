from django import forms
from .models import Subject


class SubjectCreateForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter subject name"
            })
        }