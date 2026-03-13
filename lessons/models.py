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
        return self.name