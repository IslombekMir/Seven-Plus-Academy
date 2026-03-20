from django import forms
from .models import Payment


MONTH_CHOICES = [
    (1, "January"),
    (2, "February"),
    (3, "March"),
    (4, "April"),
    (5, "May"),
    (6, "June"),
    (7, "July"),
    (8, "August"),
    (9, "September"),
    (10, "October"),
    (11, "November"),
    (12, "December"),
]

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["paid_amount", "payment_month", "payment_year"]
        widgets = {
            "payment_month": forms.Select(choices=MONTH_CHOICES),
            "payment_year": forms.NumberInput(attrs={"min": 2000}),
        }

