from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Payment


MONTH_CHOICES = [
    (1, _("January")),
    (2, _("February")),
    (3, _("March")),
    (4, _("April")),
    (5, _("May")),
    (6, _("June")),
    (7, _("July")),
    (8, _("August")),
    (9, _("September")),
    (10, _("October")),
    (11, _("November")),
    (12, _("December")),
]

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["paid_amount", "payment_month", "payment_year"]
        labels = {
            "paid_amount": _("Paid amount"),
            "payment_month": _("Payment month"),
            "payment_year": _("Payment year"),
        }
        widgets = {
            "payment_month": forms.Select(choices=MONTH_CHOICES),
            "payment_year": forms.NumberInput(attrs={"min": 2000}),
        }
