from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from lessons.models import Enrollment
from users.models import User
from .forms import PaymentForm


def can_manage_payments(user, enrollment):
    return user.role == User.Role.ADMIN or enrollment.group.teacher == user


@login_required
def payment_create(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "group", "group__teacher"),
        pk=enrollment_id,
    )

    if not can_manage_payments(request.user, enrollment):
        return HttpResponseForbidden("You do not have permission to create payments.")

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.enrollment = enrollment
            payment.save()
            return redirect("lessons:group_detail", pk=enrollment.group.pk)
    else:
        form = PaymentForm()

    return render(request, "payments/payment_form.html", {
        "form": form,
        "enrollment": enrollment,
    })

from .models import Payment


@login_required
def payment_edit(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("enrollment", "group", "student", "group__teacher"),
        pk=pk,
    )

    if not can_manage_payments(request.user, payment.enrollment):
        return HttpResponseForbidden("You do not have permission to edit payments.")

    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            return redirect("lessons:group_detail", pk=payment.group.pk)
    else:
        form = PaymentForm(instance=payment)

    return render(request, "payments/payment_form.html", {
        "form": form,
        "payment": payment,
        "enrollment": payment.enrollment,
    })


@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("enrollment", "group", "group__teacher"),
        pk=pk,
    )

    if not can_manage_payments(request.user, payment.enrollment):
        return HttpResponseForbidden("You do not have permission to delete payments.")

    if request.method == "POST":
        group_pk = payment.group.pk
        payment.delete()
        return redirect("lessons:group_detail", pk=group_pk)

    return render(request, "payments/payment_confirm_delete.html", {
        "payment": payment,
    })
