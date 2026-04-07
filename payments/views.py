from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from lessons.models import Enrollment, Group
from users.models import User
from .forms import PaymentForm, MONTH_CHOICES

from datetime import date
from decimal import Decimal
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce

from .models import Payment
from django.urls import reverse

from django.utils import timezone
from django.db.models import DecimalField, F, Sum, Value
from django.utils.translation import gettext as _

def can_manage_payments(user, enrollment):
    return user.role == User.Role.ADMIN or enrollment.group.teacher == user


def can_view_group_payments(user, group):
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.TEACHER:
        return group.teacher == user
    if user.role == User.Role.STUDENT:
        return group.enrollments.filter(student=user, is_active=True).exists()
    return False

@login_required
def payment_group_detail(request, group_id):
    group = get_object_or_404(
        Group.objects.select_related("subject", "teacher"),
        pk=group_id,
    )

    if not can_view_group_payments(request.user, group):
        return HttpResponseForbidden(_("You do not have permission to view this payments page."))

    enrollments = group.enrollments.filter(is_active=True).select_related("student")
    if request.user.role == User.Role.STUDENT:
        enrollments = enrollments.filter(student=request.user)

    current_date = timezone.now()
    selected_month = request.GET.get("month") or str(current_date.month)
    selected_year = request.GET.get("year") or str(current_date.year)

    payments = (
        group.payments
        .select_related("student", "enrollment")
        .order_by("-payment_year", "-payment_month", "-created_at")
    )

    if request.user.role == User.Role.STUDENT:
        payments = payments.filter(student=request.user)

    if selected_month:
        payments = payments.filter(payment_month=selected_month)

    if selected_year:
        payments = payments.filter(payment_year=selected_year)

    available_years = (
        Payment.objects
        .filter(group=group)
        .order_by("-payment_year")
        .values_list("payment_year", flat=True)
        .distinct()
    )

    if not available_years:
        available_years = [current_date.year]

    return render(request, "payments/group_detail.html", {
        "group": group,
        "enrollments": enrollments,
        "payments": payments,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "months": MONTH_CHOICES,
        "years": available_years,
        "can_manage_payments": request.user.role == User.Role.ADMIN or group.teacher == request.user,
    })

@login_required
def payment_create(request, enrollment_id):
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("student", "group", "group__teacher"),
        pk=enrollment_id,
        is_active=True,
    )

    if not can_manage_payments(request.user, enrollment):
        return HttpResponseForbidden(_("You do not have permission to create payments."))

    initial = {}
    selected_month = request.GET.get("month")
    selected_year = request.GET.get("year")

    if selected_month:
        initial["payment_month"] = selected_month
    if selected_year:
        initial["payment_year"] = selected_year

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.enrollment = enrollment
            payment.save()
            return redirect(
                f"{reverse('payments:group_detail', kwargs={'group_id': enrollment.group.pk})}"
                f"?month={payment.payment_month}&year={payment.payment_year}"
            )

    else:
        form = PaymentForm(initial=initial)

    return render(request, "payments/payment_form.html", {
        "form": form,
        "enrollment": enrollment,
    })

@login_required
def payment_edit(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related("enrollment", "group", "student", "group__teacher"),
        pk=pk,
    )

    if not can_manage_payments(request.user, payment.enrollment):
        return HttpResponseForbidden(_("You do not have permission to edit payments."))

    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            return redirect(
                f"{reverse('payments:group_detail', kwargs={'group_id': payment.group.pk})}"
                f"?month={payment.payment_month}&year={payment.payment_year}"
            )

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
        return HttpResponseForbidden(_("You do not have permission to delete payments."))

    if request.method == "POST":
        group_pk = payment.group.pk
        payment.delete()
        return redirect("payments:group_detail", group_id=group_pk)

    return render(request, "payments/payment_confirm_delete.html", {
        "payment": payment,
    })

@login_required
def payment_dashboard(request):
    scoped_payments = (
        Payment.objects
        .select_related("student", "group", "group__teacher", "enrollment")
        .order_by("-payment_year", "-payment_month", "-created_at")
    )

    if request.user.role == User.Role.TEACHER:
        scoped_payments = scoped_payments.filter(group__teacher=request.user)
    elif request.user.role == User.Role.STUDENT:
        scoped_payments = scoped_payments.filter(student=request.user)

    selected_student = request.GET.get("student", "")
    selected_month = request.GET.get("month", "")
    selected_teacher = request.GET.get("teacher", "")
    selected_group = request.GET.get("group", "")
    selected_payment_status = request.GET.get("payment_status", "")

    payments = scoped_payments

    if selected_student:
        payments = payments.filter(student_id=selected_student)

    if selected_month:
        try:
            year_str, month_str = selected_month.split("-")
            payments = payments.filter(
                payment_year=int(year_str),
                payment_month=int(month_str),
            )
        except ValueError:
            pass

    if selected_teacher:
        payments = payments.filter(group__teacher_id=selected_teacher)

    if selected_group:
        payments = payments.filter(group_id=selected_group)
    
    if selected_payment_status == "fully_paid":
        payments = payments.filter(paid_amount__gte=F("expected_amount"))
    elif selected_payment_status == "not_fully_paid":
        payments = payments.filter(paid_amount__lt=F("expected_amount"))


    money_field = DecimalField(max_digits=12, decimal_places=2)
    totals = payments.aggregate(
        total_paid=Coalesce(
            Sum("paid_amount"),
            Value(Decimal("0.00")),
            output_field=money_field,
        ),
        total_expected=Coalesce(
            Sum("expected_amount"),
            Value(Decimal("0.00")),
            output_field=money_field,
        ),
    )

    total_paid = totals["total_paid"]
    total_expected = totals["total_expected"]
    collection_percent = round((total_paid / total_expected) * 100, 1) if total_expected else 0

    student_ids = scoped_payments.values_list("student_id", flat=True).distinct()
    teacher_ids = scoped_payments.values_list("group__teacher_id", flat=True).distinct()
    group_ids = scoped_payments.values_list("group_id", flat=True).distinct()

    students = User.objects.filter(
        pk__in=student_ids,
        role=User.Role.STUDENT,
    ).order_by("first_name", "last_name", "username")

    teachers = User.objects.filter(
        pk__in=teacher_ids,
        role=User.Role.TEACHER,
    ).order_by("first_name", "last_name", "username")

    groups = Group.objects.filter(
        pk__in=group_ids,
    ).select_related("subject", "teacher").order_by("name")

    month_rows = (
        scoped_payments
        .values("payment_year", "payment_month")
        .distinct()
        .order_by("-payment_year", "-payment_month")
    )
    month_labels = dict(MONTH_CHOICES)
    month_choices = [
        {
            "value": f"{row['payment_year']}-{row['payment_month']:02d}",
            "label": f"{month_labels[row['payment_month']]} {row['payment_year']}",
        }
        for row in month_rows
    ]

    return render(request, "payments/payment_dashboard.html", {
        "payments": payments,
        "students": students,
        "teachers": teachers,
        "groups": groups,
        "month_choices": month_choices,
        "selected_month": selected_month,
        "selected_student": selected_student,
        "selected_teacher": selected_teacher,
        "selected_group": selected_group,
        "total_paid": total_paid,
        "total_expected": total_expected,
        "collection_percent": collection_percent,
        "can_edit_rows": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
        "selected_payment_status": selected_payment_status,
    })
