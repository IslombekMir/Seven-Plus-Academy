from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from .models import User, UserSettings, TeacherProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpResponse
from django.db.models import Q
from lessons.models import Group, Enrollment, Mark, Exam
from django.views.decorators.http import require_POST
from django.db import transaction
from datetime import date
from django.db.models.deletion import ProtectedError
from payments.models import Payment
from attendances.models import Attendance, AttendanceSession
from django.core.exceptions import ValidationError
from .forms import BulkUserMetaForm, BulkUserRowFormSet



from .forms import (
    LoginForm,
    TeacherProfileForm,
    UserCreateForm,
    UserEditForm,
)

from .forms import FirstLoginPasswordChangeForm
from django.contrib.auth import update_session_auth_hash


@login_required
def users_list(request):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot view this page.")

    if request.user.role == User.Role.TEACHER:
        users = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
        ).exclude(is_superuser=True)
    elif request.user.role == User.Role.ADMIN:
        users = User.objects.filter(is_active=True).exclude(is_superuser=True)
    else:
        users = User.objects.none()

    total_user_count = users.count()

    search_query = request.GET.get("q")
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    role_filter = request.GET.get("role")
    if role_filter:
        users = users.filter(role=role_filter)

    groups_qs = Group.objects.all()
    if request.user.role == User.Role.TEACHER:
        groups_qs = groups_qs.filter(teacher=request.user)

    group_filter = request.GET.get("group")
    if group_filter:
        users = users.filter(
            enrollments__group_id=group_filter,
            enrollments__is_active=True,
        ).distinct()

    filtered_user_count = users.count()

    return render(request, "users/users_list.html", {
        "users": users,
        "filtered_user_count": filtered_user_count,
        "total_user_count": total_user_count,
        "can_manage": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
        "groups": groups_qs,
        "selected_group": group_filter,
    })

@login_required
def removed_users(request):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot view this page.")

    if request.user.role == User.Role.TEACHER:
        users = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=False,
        ).exclude(is_superuser=True)
    elif request.user.role == User.Role.ADMIN:
        users = User.objects.filter(is_active=False).exclude(is_superuser=True)
    else:
        users = User.objects.none()

    total_user_count = users.count()

    search_query = request.GET.get("q")
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    role_filter = request.GET.get("role")
    if role_filter:
        users = users.filter(role=role_filter)

    groups_qs = Group.objects.all()
    if request.user.role == User.Role.TEACHER:
        groups_qs = groups_qs.filter(teacher=request.user)

    group_filter = request.GET.get("group")
    if group_filter:
        users = users.filter(
            enrollments__group_id=group_filter,
            enrollments__is_active=False,
        ).distinct()

    filtered_user_count = users.count()

    return render(request, "users/removed_users.html", {
        "users": users,
        "filtered_user_count": filtered_user_count,
        "total_user_count": total_user_count,
        "can_manage": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
        "groups": groups_qs,
        "selected_group": group_filter,
    })

@login_required
def remove_user(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot remove users.")

    user_obj = get_object_or_404(User, pk=user_id, is_active=True)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only remove student users.")
    
    if request.method == "POST":
        with transaction.atomic():
            user_obj.is_active = False
            user_obj.save(update_fields=["is_active"])

            Enrollment.objects.filter(student=user_obj, is_active=True).update(
                is_active=False,
                end_date=date.today(),
            )

        return redirect("users:users_list")

    return render(request, "users/confirm_remove.html", {"user": user_obj})

@login_required
def restore_user(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot restore users.")

    user_obj = get_object_or_404(User, pk=user_id, is_active=False)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only restore student users.")

    if request.method == "POST":
        user_obj.is_active = True
        user_obj.set_password(user_obj.username)
        user_obj.must_reset_password = True
        user_obj.save(update_fields=["is_active", "password", "must_reset_password"])
        return redirect("users:removed_users")

    return render(request, "users/confirm_restore.html", {"user": user_obj})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.must_reset_password:
                    return redirect("users:force_password_change")
                return redirect("core:index")
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = LoginForm()
    return render(request, "users/login.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    return redirect("users:login")

@login_required
def create_user(request):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot create users.")

    if request.method == "POST":
        form = UserCreateForm(request.POST, current_user=request.user)
        if form.is_valid():
            new_user = form.save(commit=False)

            if request.user.role == User.Role.TEACHER:
                new_user.role = User.Role.STUDENT

            new_user.save()
            return redirect("users:users_list")
    else:
        form = UserCreateForm(current_user=request.user)

    return render(request, "users/create_user.html", {"form": form})

@login_required
def bulk_create_users(request):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot create users.")

    if request.method == "POST":
        meta_form = BulkUserMetaForm(request.POST, current_user=request.user)
        formset = BulkUserRowFormSet(request.POST, prefix="rows")

        if meta_form.is_valid() and formset.is_valid():
            role = meta_form.cleaned_data["role"]
            group = meta_form.cleaned_data["group"]

            formset.validate_against_role(role)

            has_row_errors = any(form.errors for form in formset.forms)
            if has_row_errors or formset.non_form_errors():
                return render(request, "users/bulk_create_users.html", {
                    "meta_form": meta_form,
                    "formset": formset,
                })

            created_count = 0

            try:
                with transaction.atomic():
                    for row_form in formset:
                        first_name = row_form.cleaned_data.get("first_name")
                        last_name = row_form.cleaned_data.get("last_name")
                        phone_number = row_form.cleaned_data.get("phone_number")

                        if not any([first_name, last_name, phone_number]):
                            continue

                        user_obj = User(
                            first_name=first_name,
                            last_name=last_name,
                            phone_number=phone_number,
                            role=role,
                        )
                        user_obj.username = user_obj.generate_username()
                        user_obj.set_password(user_obj.username)
                        user_obj.full_clean()
                        user_obj.save()

                        if role == User.Role.STUDENT and group:
                            Enrollment.objects.create(
                                student=user_obj,
                                group=group,
                            )

                        created_count += 1

            except ValidationError as exc:
                if hasattr(exc, "message_dict"):
                    for field, errors in exc.message_dict.items():
                        for error in errors:
                            meta_form.add_error(None, f"{field}: {error}")
                else:
                    meta_form.add_error(None, "; ".join(exc.messages))
            else:
                messages.success(request, f"{created_count} user(s) created successfully.")
                return redirect("users:users_list")
    else:
        initial_role = User.Role.STUDENT if request.user.role == User.Role.TEACHER else User.Role.STUDENT
        meta_form = BulkUserMetaForm(
            initial={"role": initial_role},
            current_user=request.user,
        )
        formset = BulkUserRowFormSet(prefix="rows")

    return render(request, "users/bulk_create_users.html", {
        "meta_form": meta_form,
        "formset": formset,
    })

@login_required
def edit_user(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot edit users.")

    user_obj = get_object_or_404(User, pk=user_id)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only edit student users.")

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            return redirect("users:users_list")
    else:
        form = UserEditForm(instance=user_obj)


    return render(request, "users/create_user.html", {"form": form, "edit_mode": True})

def _can_permanently_delete_user(user_obj):
    has_attendance_history = (
        Attendance.objects.filter(student=user_obj).exists()
        or Attendance.objects.filter(enrollment__student=user_obj).exists()
    )
    has_payment_history = (
        Payment.objects.filter(student=user_obj).exists()
        or Payment.objects.filter(enrollment__student=user_obj).exists()
    )
    return not (has_attendance_history or has_payment_history)

@login_required
def delete_user(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot delete users.")

    user_obj = get_object_or_404(User, pk=user_id, is_active=False)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only delete student users.")

    if request.method == "POST":
        if not _can_permanently_delete_user(user_obj):
            messages.error(
                request,
                "This user has attendance or payment history and cannot be permanently deleted."
            )
            return redirect("users:removed_users")

        try:
            user_obj.delete()
            messages.success(request, "User was permanently deleted.")
        except ProtectedError:
            messages.error(
                request,
                "This user still has related records that prevent permanent deletion."
            )

        return redirect("users:removed_users")

    can_delete = _can_permanently_delete_user(user_obj)
    return render(request, "users/confirm_delete.html", {
        "user": user_obj,
        "can_delete": can_delete,
    })

@login_required
def reset_password(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot reset passwords.")

    user_obj = get_object_or_404(User, pk=user_id)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only reset student passwords.")

    user_obj.set_password(user_obj.username)
    user_obj.must_reset_password = True
    user_obj.save()

    return redirect("users:users_list")

### Profile
@login_required
def profile(request):
    user = request.user
    context = {
        "profile_user": user,
    }

    if user.role == User.Role.TEACHER:
        groups = (
            Group.objects
            .filter(teacher=user)
            .select_related("subject", "teacher")
            .prefetch_related("enrollments__student")
        )
        context["groups"] = groups

    elif user.role == User.Role.STUDENT:
        enrollments = (
            Enrollment.objects
            .filter(student=user)
            .select_related("group__subject", "group__teacher")
        )
        context["enrollments"] = enrollments

    return render(request, "users/profile.html", context)

### Theme
@login_required
@require_POST
def toggle_theme(request):
    settings = request.user.settings
    settings.theme = (
        UserSettings.Theme.DARK
        if settings.theme == UserSettings.Theme.LIGHT
        else UserSettings.Theme.LIGHT
    )
    settings.save(update_fields=["theme"])
    return redirect("users:profile")

### Teacher Profiles
def _can_edit_teacher_profile(user, teacher_user):
    return user.role == User.Role.ADMIN or user == teacher_user

@login_required
def teachers_list(request):
    teachers = User.objects.filter(role=User.Role.TEACHER).select_related("teacher_profile").order_by("first_name", "last_name", "username")

    if request.user.role == User.Role.STUDENT:
        teachers = teachers.filter(teacher_profile__is_active_profile=True)

    return render(request, "users/teachers_list.html", {
        "teachers": teachers,
    })

@login_required
def edit_teacher_profile(request, teacher_id):
    teacher = get_object_or_404(User, pk=teacher_id, role=User.Role.TEACHER)

    if not _can_edit_teacher_profile(request.user, teacher):
        return HttpResponseForbidden("You can only edit your own profile.")

    profile, _ = TeacherProfile.objects.get_or_create(teacher=teacher)
    form = TeacherProfileForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("users:teachers_list")

    return render(request, "users/edit_teacher_profile.html", {
        "teacher": teacher,
        "form": form,
    })

### Password Change
@login_required
def force_password_change(request):
    user = request.user

    form = FirstLoginPasswordChangeForm(user, request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        user.must_reset_password = False
        user.save()
        update_session_auth_hash(request, user)  # keep user logged in
        return redirect("core:index")

    return render(request, "users/force_password_change.html", {"form": form})

#### User profile with full wipeout option
def _can_delete_user_now(user_obj):
    if user_obj.role == User.Role.STUDENT:
        return not (
            Mark.objects.filter(enrollment__student=user_obj).exists()
            or Attendance.objects.filter(student=user_obj).exists()
            or Payment.objects.filter(student=user_obj).exists()
            or Enrollment.objects.filter(student=user_obj).exists()
        )

    if user_obj.role == User.Role.TEACHER:
        groups = Group.objects.filter(teacher=user_obj)
        return not (
            AttendanceSession.objects.filter(created_by=user_obj).exists()
            or Attendance.objects.filter(enrollment__group__in=groups).exists()
            or Payment.objects.filter(group__in=groups).exists()
            or Mark.objects.filter(enrollment__group__in=groups).exists()
            or Exam.objects.filter(group__in=groups).exists()
            or Enrollment.objects.filter(group__in=groups).exists()
            or AttendanceSession.objects.filter(group__in=groups).exists()
            or groups.exists()
        )

    if user_obj.role == User.Role.ADMIN:
        return not AttendanceSession.objects.filter(created_by=user_obj).exists()

    return False

def _build_user_deletion_context(user_obj):
    context = {
        "target_user": user_obj,
    }

    if user_obj.role == User.Role.STUDENT:
        enrollments = Enrollment.objects.filter(student=user_obj).select_related("group", "group__subject")
        marks = Mark.objects.filter(enrollment__student=user_obj).select_related("exam", "enrollment", "exam__group")
        attendances = Attendance.objects.filter(student=user_obj).select_related("session", "enrollment", "session__group")
        payments = Payment.objects.filter(student=user_obj).select_related("group", "enrollment")

        context.update({
            "deletion_steps": [
                ("Marks", "marks", marks),
                ("Attendances", "attendances", attendances),
                ("Payments", "payments", payments),
                ("Enrollments", "enrollments", enrollments),
            ],
            "marks": marks,
            "attendances": attendances,
            "payments": payments,
            "enrollments": enrollments,
        })

    elif user_obj.role == User.Role.TEACHER:
        groups = Group.objects.filter(teacher=user_obj).select_related("subject")
        attendance_sessions_by_creator = AttendanceSession.objects.filter(created_by=user_obj).select_related("group")

        group_ids = groups.values_list("id", flat=True)
        enrollments = Enrollment.objects.filter(group_id__in=group_ids).select_related("student", "group")
        exams = Exam.objects.filter(group_id__in=group_ids).select_related("group")
        marks = Mark.objects.filter(enrollment__group_id__in=group_ids).select_related("exam", "enrollment", "enrollment__student")
        attendances = Attendance.objects.filter(enrollment__group_id__in=group_ids).select_related("session", "student", "enrollment")
        group_sessions = AttendanceSession.objects.filter(group_id__in=group_ids).select_related("group", "created_by")
        payments = Payment.objects.filter(group_id__in=group_ids).select_related("student", "group", "enrollment")

        context.update({
            "deletion_steps": [
                ("Attendance Sessions Created By Teacher", "created_sessions", attendance_sessions_by_creator),
                ("Attendances In Teacher Groups", "attendances", attendances),
                ("Payments In Teacher Groups", "payments", payments),
                ("Marks In Teacher Groups", "marks", marks),
                ("Exams In Teacher Groups", "exams", exams),
                ("Enrollments In Teacher Groups", "enrollments", enrollments),
                ("Attendance Sessions For Teacher Groups", "group_sessions", group_sessions),
                ("Groups", "groups", groups),
            ],
            "groups": groups,
            "attendance_sessions_by_creator": attendance_sessions_by_creator,
            "group_sessions": group_sessions,
            "attendances": attendances,
            "payments": payments,
            "marks": marks,
            "exams": exams,
            "enrollments": enrollments,
        })

    else:  # ADMIN
        attendance_sessions_by_creator = AttendanceSession.objects.filter(created_by=user_obj).select_related("group")

        context.update({
            "deletion_steps": [
                ("Attendance Sessions Created By Admin", "created_sessions", attendance_sessions_by_creator),
            ],
            "attendance_sessions_by_creator": attendance_sessions_by_creator,
        })

    return context

@login_required
def user_detail(request, username):
    user_obj = get_object_or_404(User, username=username)

    if request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden("Only admins can view this page.")

    context = _build_user_deletion_context(user_obj)
    context["can_delete_user"] = all(not items for _, _, items in context["deletion_steps"])
    return render(request, "users/user_detail.html", context)

@login_required
@require_POST
def delete_user_related(request, username, section):
    user_obj = get_object_or_404(User, username=username)

    if request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden("Only admins can delete related data.")

    with transaction.atomic():
        if user_obj.role == User.Role.STUDENT:
            enrollments = Enrollment.objects.filter(student=user_obj)

            section_map = {
                "marks": lambda: Mark.objects.filter(enrollment__in=enrollments).delete(),
                "attendances": lambda: Attendance.objects.filter(student=user_obj).delete(),
                "payments": lambda: Payment.objects.filter(student=user_obj).delete(),
                "enrollments": lambda: enrollments.delete(),
            }

        elif user_obj.role == User.Role.TEACHER:
            groups = Group.objects.filter(teacher=user_obj)
            enrollments = Enrollment.objects.filter(group__in=groups)
            exams = Exam.objects.filter(group__in=groups)
            sessions = AttendanceSession.objects.filter(group__in=groups)

            section_map = {
                "created_sessions": lambda: AttendanceSession.objects.filter(created_by=user_obj).delete(),
                "attendances": lambda: Attendance.objects.filter(enrollment__in=enrollments).delete(),
                "payments": lambda: Payment.objects.filter(group__in=groups).delete(),
                "marks": lambda: Mark.objects.filter(enrollment__in=enrollments).delete(),
                "exams": lambda: exams.delete(),
                "enrollments": lambda: enrollments.delete(),
                "group_sessions": lambda: sessions.delete(),
                "groups": lambda: groups.delete(),
            }
        
        else:  # ADMIN
            section_map = {
                "created_sessions": lambda: AttendanceSession.objects.filter(created_by=user_obj).delete(),
            }

        action = section_map.get(section)
        if not action:
            messages.error(request, "Unknown delete section.")
            return redirect("users:user_detail", username=user_obj.username)

        try:
            action()
            messages.success(request, f"{section.replace('_', ' ').title()} deleted.")
        except ProtectedError:
            messages.error(request, "That section still has dependent records. Delete earlier steps first.")

    return redirect("users:user_detail", username=user_obj.username)

@login_required
@require_POST
def delete_user_only(request, username):
    user_obj = get_object_or_404(User, username=username)

    if request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden("Only admins can delete users.")

    if not _can_delete_user_now(user_obj):
        messages.error(request, "Delete blocking related data first.")
        return redirect("users:user_detail", username=user_obj.username)

    user_obj.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("users:users_list")

@login_required
def confirm_delete_user_related(request, username, section):
    user_obj = get_object_or_404(User, username=username)

    if request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden("Only admins can manage this page.")

    context = _build_user_deletion_context(user_obj)

    step = next((step for step in context["deletion_steps"] if step[1] == section), None)
    if not step:
        messages.error(request, "Unknown delete section.")
        return redirect("users:user_detail", username=user_obj.username)

    title, slug, items = step

    if request.method == "POST":
        return delete_user_related(request, username, section)

    return render(request, "users/confirm_delete_related.html", {
        "target_user": user_obj,
        "section_title": title,
        "section_slug": slug,
        "items": items,
    })

@login_required
def confirm_delete_user_only(request, username):
    user_obj = get_object_or_404(User, username=username)

    if request.user.role != User.Role.ADMIN:
        return HttpResponseForbidden("Only admins can manage this page.")

    context = _build_user_deletion_context(user_obj)
    can_delete_user = all(not items for _, _, items in context["deletion_steps"])

    if request.method == "POST":
        return delete_user_only(request, username)

    return render(request, "users/confirm_delete_user.html", {
        "target_user": user_obj,
        "can_delete_user": can_delete_user,
    })
