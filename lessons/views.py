from django.shortcuts import render, redirect, get_object_or_404
from .models import Subject
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .forms import SubjectCreateForm

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
