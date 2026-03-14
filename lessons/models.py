from django.db import models
from users.models import User
from datetime import date

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subject = models.ForeignKey(Subject, on_delete=models.RESTRICT, related_name="groups")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={"role": "TEACHER"}, related_name="teaching_groups")
    homework_description = models.TextField(blank=True, null=True)
    homework_updated_at = models.DateTimeField(blank=True, null=True)
    default_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    week_days = models.CharField(max_length=50, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f'{self.name} - {self.subject}'

### Enrollment
class Enrollment(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.RESTRICT,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="enrollments",
        limit_choices_to={"role": "STUDENT"},
    )
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["group", "student"], name="unique_group_student")
        ]
    
    def save(self, *args, **kwargs):
        if self.payment_amount is None:
            self.payment_amount = self.group.default_payment_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group} - {self.student}"
