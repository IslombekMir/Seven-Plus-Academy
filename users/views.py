from django.shortcuts import render, redirect, get_object_or_404
from .forms import UserCreateForm
from django.http import HttpResponseForbidden
from .models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from .forms import LoginForm

@login_required
def users_list(request):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot view this page.")

    if request.user.role == User.Role.TEACHER:
        users = User.objects.filter(role=User.Role.STUDENT)
    elif request.user.role == User.Role.ADMIN:
        users = User.objects.all()
    else:
        users = []

    return render(request, "users/users_list.html", {
        "users": users,
        "can_manage": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
        })


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
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
        form = UserCreateForm(request.POST, instance=user_obj, current_user=request.user)
        if form.is_valid():
            form.save()
            return redirect("users:users_list")
    else:
        form = UserCreateForm(instance=user_obj, current_user=request.user)

    return render(request, "users/create_user.html", {"form": form, "edit_mode": True})

@login_required
def delete_user(request, user_id):
    if request.user.role == User.Role.STUDENT:
        return HttpResponseForbidden("Students cannot delete users.")

    user_obj = get_object_or_404(User, pk=user_id)

    if request.user.role == User.Role.TEACHER and user_obj.role != User.Role.STUDENT:
        return HttpResponseForbidden("Teachers can only delete student users.")

    if request.method == "POST":
        user_obj.delete()
        return redirect("users:users_list")

    return render(request, "users/confirm_delete.html", {"user": user_obj})

