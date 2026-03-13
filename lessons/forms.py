from django import forms
from .models import Subject, Group


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

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = [
            "name", "subject", "teacher", "homework_description",
            "default_payment_amount", "week_days",
            "start_time", "end_time", "start_date", "end_date"
        ]

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        if current_user and current_user.role == "TEACHER":
            # Hide teacher field for teachers
            self.fields.pop("teacher", None)
