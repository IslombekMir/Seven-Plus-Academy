from django import forms

from lessons.models import Enrollment
from .models import Attendance, AttendanceSession
from django.forms import modelformset_factory



class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ["date"]
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
        }


class AttendanceBulkForm(forms.Form):
    def __init__(self, *args, session, enrollments, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.enrollments = enrollments

        for enrollment in enrollments:
            existing = session.attendances.filter(enrollment=enrollment).first()
            self.fields[f"enrollment_{enrollment.pk}"] = forms.ChoiceField(
                choices=Attendance.Status.choices,
                initial=existing.status if existing else Attendance.Status.UNKNOWN,
                required=True,
                label=enrollment.student.get_full_name() or enrollment.student.username,
            )

    def save(self):
        for enrollment in self.enrollments:
            status = self.cleaned_data[f"enrollment_{enrollment.pk}"]

            attendance, _ = Attendance.objects.get_or_create(
                session=self.session,
                enrollment=enrollment,
                defaults={
                    "student": enrollment.student,
                    "status": status,
                },
            )

            attendance.student = enrollment.student
            attendance.status = status
            attendance.save()

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ["status"]
        widgets = {
            "status": forms.Select(),
        }

AttendanceRecordFormSet = modelformset_factory(
    Attendance,
    form=AttendanceRecordForm,
    extra=0,
)
