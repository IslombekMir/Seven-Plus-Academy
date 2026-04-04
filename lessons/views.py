from django.shortcuts import render, redirect, get_object_or_404
from .models import Subject, Group, Enrollment, Exam, Mark
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .forms import SubjectCreateForm, GroupForm, EnrollmentForm, ExamForm, MarkForm
from django.db.models import RestrictedError
from django.contrib import messages
from payments.models import Payment
from django.utils import timezone
from django.db.models import Avg
from django.db import transaction


### Subject
@login_required
def subjects_list(request):
    subjects = Subject.objects.all()

    search_query = request.GET.get("q")
    if search_query:
        subjects = subjects.filter(name__icontains=search_query)

    return render(request, "lessons/subjects_list.html", {
        "subjects": subjects,
        "can_manage": request.user.role in [User.Role.ADMIN],
        })

@login_required
def create_subject(request):
    if request.user.role != request.user.Role.ADMIN:
        return redirect("lessons:subjects_list")

    if request.method == "POST":
        form = SubjectCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("lessons:subjects_list")
    else:
        form = SubjectCreateForm()

    return render(request, "lessons/create_subject.html", {"form": form})

@login_required
def edit_subject(request, subject_id):
    if request.user.role != request.user.Role.ADMIN:
        return redirect("lessons:subjects_list")

    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        form = SubjectCreateForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            return redirect("lessons:subjects_list")
    else:
        form = SubjectCreateForm(instance=subject)

    return render(request, "lessons/create_subject.html", {"form": form})

@login_required
def delete_subject(request, subject_id):
    if request.user.role != request.user.Role.ADMIN:
        return redirect("lessons:subjects_list")

    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        subject.delete()
        return redirect("lessons:subjects_list")

    return render(request, "lessons/subject_confirm_delete.html", {"subject": subject})

### GROUP
@login_required
def group_list(request):
    groups = Group.objects.all()
    return render(request, "lessons/group_list.html", {"groups": groups})

@login_required
def group_create(request):
    if request.user.role == "STUDENT":
        return HttpResponseForbidden("Students cannot create groups.")

    if request.method == "POST":
        form = GroupForm(request.POST, current_user=request.user)
        if form.is_valid():
            group = form.save(commit=False)
            if request.user.role == "TEACHER":
                group.teacher = request.user
            group.save()
            return redirect("lessons:group_list")
    else:
        form = GroupForm(current_user=request.user)

    return render(request, "lessons/group_form.html", {"form": form})

@login_required
def group_delete(request, pk):
    if request.user.role == "STUDENT":
        return HttpResponseForbidden("Students cannot delete groups.")
    group = get_object_or_404(Group, pk=pk)
    if request.user.role == "TEACHER" and group.teacher_id != request.user.id:
        return HttpResponseForbidden("Teachers can only delete their own groups.")
    if request.method == "POST":
        try:
            group.delete()
            return redirect("lessons:group_list")
        except RestrictedError:
            messages.error(
                request,
                "Cannot delete this group — it still has active enrollments. "
                "Please remove all enrollments first."
            )
    return render(request, "lessons/group_confirm_delete.html", {"group": group})

@login_required
def group_edit(request, pk):
    if request.user.role == "STUDENT":
        return HttpResponseForbidden("Students cannot edit groups.")
    
    group = get_object_or_404(Group, pk=pk)
    
    if request.user.role == "TEACHER" and group.teacher_id != request.user.id:
        return HttpResponseForbidden("Teachers can only edit their own groups.")
    
    if request.method == "POST":
        form = GroupForm(request.POST, instance=group, current_user=request.user)
        if form.is_valid():
            form.save()
            return redirect("lessons:group_detail", pk=group.pk)
    else:
        form = GroupForm(instance=group, current_user=request.user)
    
    return render(request, "lessons/group_form.html", {"form": form})

@login_required
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)

    if can_manage_enrollments(request.user, group):
        if request.method == "POST":
            enrollment_form = EnrollmentForm(request.POST, group=group)
            if enrollment_form.is_valid():
                with transaction.atomic():
                    student = enrollment_form.cleaned_data["student"]
                    existing_enrollment = Enrollment.objects.filter(
                        group=group,
                        student=student,
                    ).first()

                    if existing_enrollment:
                        existing_enrollment.is_active = True
                        existing_enrollment.end_date = None
                        existing_enrollment.payment_amount = enrollment_form.cleaned_data["payment_amount"]
                        existing_enrollment.save(update_fields=["is_active", "end_date", "payment_amount"])
                    else:
                        enrollment = enrollment_form.save(commit=False)
                        enrollment.group = group
                        enrollment.is_active = True
                        enrollment.start_date = (
                            enrollment_form.cleaned_data["start_date"] or timezone.localdate()
                        )
                        enrollment.save()
                return redirect("lessons:group_detail", pk=group.pk)
        else:
            enrollment_form = EnrollmentForm(group=group)
    else:
        enrollment_form = None
    
    if request.user.role == User.Role.STUDENT:
        enrollments = group.enrollments.filter(
            student=request.user,
            is_active=True,
        ).select_related("student")
    elif request.user.role == User.Role.TEACHER and group.teacher_id != request.user.id:
        enrollments = Enrollment.objects.none()
    else:
        enrollments = group.enrollments.filter(is_active=True).select_related("student")


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

    return render(request, "lessons/group_detail.html", {
    "group": group,
    "enrollments": enrollments,
    "enrollment_form": enrollment_form,
})

### Enrollment
def can_manage_enrollments(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user

@login_required
def enrollment_edit(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    group = enrollment.group

    if not can_manage_enrollments(request.user, group):
        return HttpResponseForbidden("You do not have permission to edit enrollments.")

    if request.method == "POST":
        form = EnrollmentForm(request.POST, instance=enrollment, group=group)
        if form.is_valid():
            form.save()
            return redirect("lessons:group_detail", pk=group.pk)
    else:
        form = EnrollmentForm(instance=enrollment, group=group)

    return render(request, "lessons/enrollment_form.html", {
        "form": form,
        "group": group,
        "enrollment": enrollment,
    })

### Soft delete - more like remove
@login_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    group = enrollment.group

    if not can_manage_enrollments(request.user, group):
        return HttpResponseForbidden("You do not have permission to delete enrollments.")

    if request.method == "POST":
        enrollment.is_active = False

        if enrollment.end_date is None:
            enrollment.end_date = timezone.localdate()

        enrollment.save(update_fields=["is_active", "end_date"])
        return redirect("lessons:group_detail", pk=group.pk)

    return render(request, "lessons/enrollment_confirm_delete.html", {
        "enrollment": enrollment,
        "group": group,
    })


### Exam
def can_manage_exams(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user

def can_view_exams(user, group):
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.TEACHER:
        return group.teacher == user
    if user.role == User.Role.STUDENT:
        return group.enrollments.filter(student=user, is_active=True).exists()
    return False

@login_required
def exam_create(request, group_id):
    group = get_object_or_404(Group, pk=group_id)

    if not can_manage_exams(request.user, group):
        return HttpResponseForbidden("You do not have permission to create exams.")

    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.group = group
            exam.save()
            return redirect("lessons:exam_list", group_id=group.pk)
    else:
        form = ExamForm()

    return render(request, "lessons/exam_form.html", {
        "form": form,
        "group": group,
    })

@login_required
def exam_list(request, group_id):
    group = get_object_or_404(Group, pk=group_id)

    if not can_view_exams(request.user, group):
        return HttpResponseForbidden("You do not have permission to view exams.")

    exams = group.exams.all().order_by("-date")

    return render(request, "lessons/exam_list.html", {
        "group": group,
        "exams": exams,
    })

@login_required
def exam_detail(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    group = exam.group

    if not can_view_exams(request.user, group):
        return HttpResponseForbidden("You do not have permission to view this exam.")

    marks = exam.marks.select_related("enrollment__student").all()
    average_mark = marks.aggregate(avg=Avg("mark"))["avg"]

    if can_manage_marks(request.user, group):
        if request.method == "POST":
            form = MarkForm(request.POST, exam=exam)
            if form.is_valid():
                form.save()
                return redirect("lessons:exam_detail", pk=exam.pk)
        else:
            form = MarkForm(exam=exam)
    else:
        form = None

    return render(request, "lessons/exam_detail.html", {
        "exam": exam,
        "group": group,
        "marks": marks,
        "form": form,
        "average_mark": average_mark,
    })

@login_required
def exam_edit(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    group = exam.group

    if not can_manage_exams(request.user, group):
        return HttpResponseForbidden("You do not have permission to edit exams.")

    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            return redirect("lessons:exam_list", group_id=group.pk)
    else:
        form = ExamForm(instance=exam)

    return render(request, "lessons/exam_form.html", {
        "form": form,
        "group": group,
        "exam": exam,
    })

@login_required
def exam_delete(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    group = exam.group

    if not can_manage_exams(request.user, group):
        return HttpResponseForbidden("You do not have permission to delete exams.")

    if request.method == "POST":
        exam.delete()
        return redirect("lessons:exam_list", group_id=group.pk)

    return render(request, "lessons/exam_confirm_delete.html", {
        "exam": exam,
        "group": group,
    })

### Mark
def can_manage_marks(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user

@login_required
def mark_delete(request, pk):
    mark = get_object_or_404(Mark, pk=pk)
    group = mark.exam.group

    if not can_manage_marks(request.user, group):
        return HttpResponseForbidden("You do not have permission to delete marks.")

    if request.method == "POST":
        mark.delete()
        return redirect("lessons:exam_detail", pk=mark.exam.pk)

    return render(request, "lessons/mark_confirm_delete.html", {
        "mark": mark,
        "group": group,
    })