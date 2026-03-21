from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from lessons.models import Enrollment, Group
from users.models import User


class AttendanceSession(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.RESTRICT,
        related_name="attendance_sessions",
    )
    date = models.DateField(default=date.today)
    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="created_attendance_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "date"],
                name="unique_attendance_session_per_group_date",
            )
        ]
        ordering = ["-date", "-created_at"]

    def clean(self):
        if self.created_by_id and self.created_by.role == User.Role.STUDENT:
            raise ValidationError("Students cannot create attendance sessions.")

        if (
            self.group_id
            and self.created_by_id
            and self.created_by.role == User.Role.TEACHER
            and self.group.teacher_id != self.created_by_id
        ):
            raise ValidationError("Teachers can only create sessions for their own groups.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group} - {self.date}"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        UNKNOWN = "UNKNOWN", "Unknown"

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.RESTRICT,
        related_name="attendances",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="attendances",
        limit_choices_to={"role": User.Role.STUDENT},
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNKNOWN,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrollment"],
                name="unique_attendance_per_session_enrollment",
            ),
            models.UniqueConstraint(
                fields=["session", "student"],
                name="unique_attendance_per_session_student",
            ),
        ]
        ordering = ["session__date", "student__first_name", "student__last_name"]

    def clean(self):
        if self.enrollment_id and self.student_id:
            if self.enrollment.student_id != self.student_id:
                raise ValidationError("Student must match the enrollment student.")

        if self.session_id and self.enrollment_id:
            if self.session.group_id != self.enrollment.group_id:
                raise ValidationError("Enrollment must belong to the session group.")

    def save(self, *args, **kwargs):
        if self.enrollment_id and not self.student_id:
            self.student = self.enrollment.student

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.session} - {self.student} - {self.get_status_display()}"
