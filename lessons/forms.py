from django import forms
from .models import Subject, Group, Enrollment, Exam
from users.models import User


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
            self.fields.pop("teacher", None)

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "start_date", "end_date", "payment_amount"]

    def __init__(self, *args, **kwargs):
        group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)

        qs = User.objects.filter(role=User.Role.STUDENT)
        if group:
            qs = qs.exclude(enrollments__group=group)
        self.fields["student"].queryset = qs

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["name", "description", "date", "full_mark"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter exam name",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter exam description",
                "rows": 4,
            }),
            "date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "full_mark": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter full mark",
                "min": 1,
            }),
        }

