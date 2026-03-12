from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path("subjects_list/", views.subjects_list, name="subjects_list"),
    path("create_subject/", views.create_subject, name="create_subject"),
    path("<int:subject_id>/edit/", views.edit_subject, name="edit_subject"),
    path("<int:subject_id>/delete/", views.delete_subject, name="delete_subject"),
]
