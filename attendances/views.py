from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from lessons.models import Enrollment, Group
from users.models import User

from .forms import AttendanceSessionForm, AttendanceBulkForm

from django.db.models import Count, Q
from .models import AttendanceSession, Attendance
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def can_manage_attendance(user, group):
    return user.role == User.Role.ADMIN or group.teacher == user

@login_required
def attendance_dashboard(request):
    selected_student = request.GET.get("student", "")
    selected_teacher = request.GET.get("teacher", "")
    selected_group = request.GET.get("group", "")
    selected_status = request.GET.get("status", "")
    selected_date = request.GET.get("date", "")

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
    
    if selected_date:
        attendances = attendances.filter(session__date=selected_date)
    
    students = User.objects.filter(
        pk__in=attendances.values_list("student_id", flat=True).distinct(),
        role=User.Role.STUDENT,
    ).order_by("first_name", "last_name", "username")

    if selected_student:
        attendances = attendances.filter(student_id=selected_student)

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

    teacher_ids = attendances.values_list("session__group__teacher_id", flat=True).distinct()
    group_ids = attendances.values_list("session__group_id", flat=True).distinct()
    student_ids = attendances.values_list("student_id", flat=True).distinct()

    students = User.objects.filter(
        pk__in=student_ids,
        role=User.Role.STUDENT,
    ).order_by("first_name", "last_name", "username")

    teachers = User.objects.filter(
        pk__in=teacher_ids,
        role=User.Role.TEACHER,
    ).order_by("first_name", "last_name", "username")

    dashboard_groups = Group.objects.filter(
        pk__in=group_ids,
    ).select_related("subject", "teacher").order_by("name")

    return render(request, "attendances/dashboard.html", {
        "attendances": attendances.order_by("-session__date", "-updated_at"),
        "students": students,
        "selected_student": selected_student,
        "teachers": teachers,
        "dashboard_groups": dashboard_groups,
        "selected_teacher": selected_teacher,
        "selected_group": selected_group,
        "selected_status": selected_status,
        "selected_date": selected_date,
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
            return HttpResponseForbidden(_("You do not have permission to view this attendance page."))
    elif request.user.role == User.Role.TEACHER and group.teacher_id != request.user.id:
        return HttpResponseForbidden(_("Teachers can only view attendance for their own groups."))

    sessions = group.attendance_sessions.select_related("created_by").prefetch_related("attendances").order_by("-date", "-created_at")

    if can_manage_attendance(request.user, group):
        if request.method == "POST":
            form = AttendanceSessionForm(request.POST)
            if form.is_valid():
                session = form.save(commit=False)
                session.group = group
                session.created_by = request.user

                try:
                    session.save()
                except ValidationError as exc:
                    form.add_error(None, exc)
                else:
                    enrollments = Enrollment.objects.filter(
                        group=group,
                        is_active=True,
                    ).select_related("student")

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

    selected_date = request.GET.get("date", "")

    sessions = group.attendance_sessions.select_related("created_by").prefetch_related(
        "attendances"
    ).order_by("-date", "-created_at")

    if selected_date:
        sessions = sessions.filter(date=selected_date)




    return render(request, "attendances/group_detail.html", {
        "group": group,
        "sessions": sessions,
        "form": form,
        "can_manage": can_manage_attendance(request.user, group),
        "selected_date": selected_date,
    })

@login_required
def attendance_session_detail(request, pk):
    session = get_object_or_404(
        AttendanceSession.objects.select_related("group", "group__teacher", "created_by"),
        pk=pk,
    )
    group = session.group

    if request.user.role == User.Role.STUDENT:
        if not session.attendances.filter(student=request.user).exists():
            return HttpResponseForbidden(_("You do not have permission to view this session."))
    elif request.user.role == User.Role.TEACHER and group.teacher_id != request.user.id:
        return HttpResponseForbidden(_("Teachers can only view attendance for their own groups."))

    attendances = session.attendances.select_related(
        "student", "enrollment"
    ).order_by("student__first_name", "student__last_name")

    if request.user.role == User.Role.STUDENT:
        attendances = attendances.filter(student=request.user)

    historical_enrollment_ids = session.attendances.values_list("enrollment_id", flat=True)

    editable_enrollments = Enrollment.objects.filter(
        Q(group=group, is_active=True) | Q(pk__in=historical_enrollment_ids)
    ).select_related("student").distinct().order_by(
        "student__first_name",
        "student__last_name",
    )

    if request.user.role == User.Role.STUDENT:
        editable_enrollments = editable_enrollments.filter(student=request.user)

    if request.method == "POST":
        if not can_manage_attendance(request.user, group):
            return HttpResponseForbidden(_("You do not have permission to update attendance."))

        form = AttendanceBulkForm(
            request.POST,
            session=session,
            enrollments=editable_enrollments,
        )
        if form.is_valid():
            form.save()
            return redirect("attendances:session_detail", pk=session.pk)
    else:
        form = AttendanceBulkForm(
            session=session,
            enrollments=editable_enrollments,
        )

    return render(request, "attendances/session_detail.html", {
        "session": session,
        "group": group,
        "form": form,
        "attendances": attendances,
        "can_manage": can_manage_attendance(request.user, group),
    })
