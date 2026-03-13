from django.shortcuts import render, redirect, get_object_or_404
from .models import Subject, Group
from users.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .forms import SubjectCreateForm, GroupForm

### Subject
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

def group_list(request):
    groups = Group.objects.all()
    return render(request, "lessons/group_list.html", {"groups": groups})

@login_required
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)
    return render(request, "lessons/group_detail.html", {"group": group})

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
        group.delete()
        return redirect("lessons:group_list")
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
