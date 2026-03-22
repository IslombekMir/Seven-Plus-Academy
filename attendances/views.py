from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from lessons.models import Enrollment, Group
from users.models import User

from .forms import AttendanceBulkForm, AttendanceSessionForm
from .models import AttendanceSession


def can_manage_attendance(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user


@login_required
def attendance_dashboard(request):
    if request.user.role == User.Role.STUDENT:
        groups = Group.objects.filter(enrollments__student=request.user).distinct()
    elif request.user.role == User.Role.TEACHER:
        groups = Group.objects.filter(teacher=request.user)
    else:
        groups = Group.objects.all()

    groups = groups.select_related("subject", "teacher").prefetch_related("attendance_sessions")

    return render(request, "attendances/dashboard.html", {
        "groups": groups,
    })


@login_required
def attendance_group_detail(request, group_id):
    group = get_object_or_404(
        Group.objects.select_related("subject", "teacher"),
        pk=group_id,
    )

    if request.user.role == User.Role.STUDENT:
        if not group.enrollments.filter(student=request.user).exists():
            return HttpResponseForbidden("You do not have permission to view this attendance page.")

    elif request.user.role == User.Role.TEACHER and group.teacher_id != request.user.id:
        return HttpResponseForbidden("Teachers can only view attendance for their own groups.")

    sessions = group.attendance_sessions.select_related("created_by").prefetch_related("attendances").order_by("-date", "-created_at")

    if can_manage_attendance(request.user, group):
        if request.method == "POST":
            form = AttendanceSessionForm(request.POST)
            if form.is_valid():
                session = form.save(commit=False)
                session.group = group
                session.created_by = request.user
                session.save()

                enrollments = Enrollment.objects.filter(group=group).select_related("student")
                for enrollment in enrollments:
                    session.attendances.get_or_create(
                        enrollment=enrollment,
                        defaults={
                            "student": enrollment.student,
                        },
                    )

                return redirect("attendances:session_detail", pk=session.pk)
        else:
            form = AttendanceSessionForm()
    else:
        form = None

    return render(request, "attendances/group_detail.html", {
        "group": group,
        "sessions": sessions,
        "form": form,
        "can_manage": can_manage_attendance(request.user, group),
    })


@login_required
def attendance_session_detail(request, pk):
    session = get_object_or_404(
        AttendanceSession.objects.select_related("group", "group__teacher", "created_by"),
        pk=pk,
    )
    group = session.group

    if request.user.role == User.Role.STUDENT:
        if not group.enrollments.filter(student=request.user).exists():
            return HttpResponseForbidden("You do not have permission to view this session.")
    elif request.user.role == User.Role.TEACHER and group.teacher_id != request.user.id:
        return HttpResponseForbidden("Teachers can only view attendance for their own groups.")

    enrollments = Enrollment.objects.filter(group=group).select_related("student").order_by("student__first_name", "student__last_name")

    # Students only see their own enrollment
    if request.user.role == User.Role.STUDENT:
        enrollments = enrollments.filter(student=request.user)

    if request.method == "POST":
        if not can_manage_attendance(request.user, group):
            return HttpResponseForbidden("You do not have permission to update attendance.")

        form = AttendanceBulkForm(request.POST, session=session, enrollments=enrollments)
        if form.is_valid():
            form.save()
            return redirect("attendances:session_detail", pk=session.pk)
    else:
        form = AttendanceBulkForm(session=session, enrollments=enrollments)

    attendances = session.attendances.select_related("student", "enrollment")

    if request.user.role == User.Role.STUDENT:
        attendances = attendances.filter(student=request.user)

    attendance_map = {
        attendance.enrollment_id: attendance
        for attendance in attendances
    }

    enrollment_attendance_pairs = [
        (enrollment, attendance_map.get(enrollment.pk))
        for enrollment in enrollments
    ]

    return render(request, "attendances/session_detail.html", {
        "session": session,
        "group": group,
        "form": form,
        "enrollment_attendance_pairs": enrollment_attendance_pairs,
        "can_manage": can_manage_attendance(request.user, group),
    })
