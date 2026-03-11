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

    return render(request, "users/users_list.html", {"users": users})


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