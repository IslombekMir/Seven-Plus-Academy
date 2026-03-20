from django.db import models
from lessons.models import Enrollment, Group
from users.models import User


class Payment(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.RESTRICT,
        related_name="payments",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="payments",
        limit_choices_to={"role": User.Role.STUDENT},
        editable=False,
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.RESTRICT,
        related_name="payments",
        editable=False,
    )
    expected_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        editable=False,
    )
    paid_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.student = self.enrollment.student
        self.group = self.enrollment.group
        self.expected_amount = self.enrollment.payment_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.group} - {self.paid_amount}"
