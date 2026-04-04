from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from .models import User, UserSettings, TeacherProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpResponse
from django.db.models import Q
from lessons.models import Group
from lessons.models import Group, Enrollment
from django.views.decorators.http import require_POST
from django.db import transaction
from datetime import date
from django.db.models.deletion import ProtectedError
from payments.models import Payment
from attendances.models import Attendance

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

    return render(request, "users/removed_users.html", {
        "users": users,
        "can_manage": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
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