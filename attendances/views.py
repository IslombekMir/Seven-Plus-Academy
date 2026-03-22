from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from lessons.models import Enrollment, Group
from users.models import User

from .forms import AttendanceBulkForm, AttendanceSessionForm
from .models import AttendanceSession


def can_manage_attendance(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user


from django.db.models import Count, Q
from .models import AttendanceSession, Attendance

@login_required
def attendance_dashboard(request):
    if request.user.role == User.Role.STUDENT:
        groups = Group.objects.filter(enrollments__student=request.user).distinct()
    elif request.user.role == User.Role.TEACHER:
        groups = Group.objects.filter(teacher=request.user)
    else:
        groups = Group.objects.all()

    groups = groups.select_related("subject", "teacher").prefetch_related("attendance_sessions")

    selected_teacher = request.GET.get("teacher", "")
    selected_group = request.GET.get("group", "")
    selected_status = request.GET.get("status", "")

    sessions = AttendanceSession.objects.select_related(
        "group", "group__subject", "group__teacher", "created_by"
    ).prefetch_related("attendances").order_by("-date", "-created_at")

    if request.user.role == User.Role.TEACHER:
        sessions = sessions.filter(group__teacher=request.user)
    elif request.user.role == User.Role.STUDENT:
        sessions = sessions.filter(group__enrollments__student=request.user).distinct()

    if selected_teacher:
        sessions = sessions.filter(group__teacher_id=selected_teacher)

    if selected_group:
        sessions = sessions.filter(group_id=selected_group)

    attendances = Attendance.objects.select_related(
        "session", "session__group", "student", "enrollment"
    )

    if request.user.role == User.Role.TEACHER:
        attendances = attendances.filter(session__group__teacher=request.user)
    elif request.user.role == User.Role.STUDENT:
        attendances = attendances.filter(student=request.user)

    if selected_teacher:
        attendances = attendances.filter(session__group__teacher_id=selected_teacher)

    if selected_group:
        attendances = attendances.filter(session__group_id=selected_group)

    if selected_status:
        attendances = attendances.filter(status=selected_status)

    totals = attendances.aggregate(
        total_records=Count("id"),
        total_present=Count("id", filter=Q(status=Attendance.Status.PRESENT)),
        total_absent=Count("id", filter=Q(status=Attendance.Status.ABSENT)),
        total_unknown=Count("id", filter=Q(status=Attendance.Status.UNKNOWN)),
    )

    total_records = totals["total_records"] or 0
    total_present = totals["total_present"] or 0
    total_absent = totals["total_absent"] or 0
    total_unknown = totals["total_unknown"] or 0
    attendance_percent = round((total_present / total_records) * 100, 1) if total_records else 0

    teacher_ids = sessions.values_list("group__teacher_id", flat=True).distinct()
    group_ids = sessions.values_list("group_id", flat=True).distinct()

    teachers = User.objects.filter(
        pk__in=teacher_ids,
        role=User.Role.TEACHER,
    ).order_by("first_name", "last_name", "username")

    dashboard_groups = Group.objects.filter(
        pk__in=group_ids,
    ).select_related("subject", "teacher").order_by("name")

    return render(request, "attendances/dashboard.html", {
        "groups": groups,  # keep your existing list untouched
        "sessions": sessions,
        "teachers": teachers,
        "dashboard_groups": dashboard_groups,
        "selected_teacher": selected_teacher,
        "selected_group": selected_group,
        "selected_status": selected_status,
        "total_records": total_records,
        "total_present": total_present,
        "total_absent": total_absent,
        "total_unknown": total_unknown,
        "attendance_percent": attendance_percent,
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
