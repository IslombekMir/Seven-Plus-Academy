from django.shortcuts import render
from .models import Subject
from users.models import User

def subjects_list(request):
    subjects = Subject.objects.all()

    return render(request, "lessons/subjects_list.html", {
        "subjects": subjects,
        "can_manage": request.user.role in [User.Role.ADMIN, User.Role.TEACHER],
        })
