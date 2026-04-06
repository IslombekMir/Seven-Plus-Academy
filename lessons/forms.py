from django import forms
from .models import Subject, Group, Enrollment, Exam, Mark
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
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        group = kwargs.pop("group", None)
        super().__init__(*args, **kwargs)

        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].input_formats = ["%Y-%m-%d"]

        qs = User.objects.filter(role=User.Role.STUDENT, is_active=True)
        if group:
            qs = qs.exclude(enrollments__group=group, enrollments__is_active=True)

        if self.instance and self.instance.pk and self.instance.student_id:
            qs = qs | User.objects.filter(pk=self.instance.student_id)
            self.fields["student"].disabled = True

        self.fields["student"].queryset = qs.distinct()
        self.fields["start_date"].required = False
        self.fields["student"].empty_label = "Select student"
        self.fields["student"].widget.attrs.update({"class": "searchable-select"})


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

# lessons/forms.py
class MarkForm(forms.ModelForm):
    class Meta:
        model = Mark
        fields = ["enrollment", "mark"]

    def __init__(self, *args, exam=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exam = exam

        if exam:
            available_enrollments = Enrollment.objects.filter(
                group=exam.group,
                is_active=True,
            ).exclude(
                marks__exam=exam
            )


            self.fields["enrollment"].queryset = available_enrollments
            self.fields["enrollment"].label_from_instance = (
                lambda enrollment: enrollment.student.get_full_name() or enrollment.student.username
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.exam = self.exam

        if commit:
            instance.save()
        return instance
