from django.urls import path
from . import views

app_name = "quizzes"

urlpatterns = [
    path("", views.quiz_list, name="list"),
    path("create/", views.quiz_create, name="create"),
    path("<int:pk>/", views.quiz_detail, name="detail"),
    path("<int:pk>/edit/", views.quiz_edit, name="edit"),
    path("<int:pk>/take/", views.quiz_take, name="take"),
    path("result/<int:attempt_id>/", views.quiz_result, name="result"),
    path("<int:pk>/delete/", views.quiz_delete, name="delete"),
]