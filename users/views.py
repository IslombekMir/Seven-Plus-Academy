from django.shortcuts import render, redirect
from .forms import UserCreateForm
from django.http import HttpResponseForbidden
from .models import User
from django.contrib.auth.decorators import login_required

@login_required
def create_user(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, current_user=request.user)
        if form.is_valid():
            if request.user.role == User.Role.TEACHER:
                if form.cleaned_data["role"] != User.Role.STUDENT:
                    return HttpResponseForbidden()
            form.save()
            return redirect("users:list")
    else:
        form = UserCreateForm(current_user=request.user)
    return render(request, "users/create.html", {"form": form})