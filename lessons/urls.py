from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path("subjects_list/", views.subjects_list, name="subjects_list"),
    path("subjects/create/", views.create_subject, name="create_subject"),
    path("subjects/<int:subject_id>/edit/", views.edit_subject, name="edit_subject"),
    path("subjects/<int:subject_id>/delete/", views.delete_subject, name="delete_subject"),

    path("groups/", views.group_list, name="group_list"),
    path("groups/removed/", views.removed_groups, name="removed_groups"),
    path("groups/<int:pk>/", views.group_detail, name="group_detail"),
    path("groups/create/", views.group_create, name="group_create"),
    path("groups/<int:pk>/remove/", views.remove_group, name="remove_group"),
    path("groups/<int:pk>/restore/", views.restore_group, name="restore_group"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),
    path("groups/<int:pk>/edit/", views.group_edit, name="group_edit"),

    path("enrollments/<int:pk>/edit/", views.enrollment_edit, name="enrollment_edit"),
    path("enrollments/<int:pk>/delete/", views.enrollment_delete, name="enrollment_delete"),

    path("groups/<int:group_id>/exams/", views.exam_list, name="exam_list"),
    path("groups/<int:group_id>/exams/create/", views.exam_create, name="exam_create"),

    path("exams/<int:pk>/edit/", views.exam_edit, name="exam_edit"),
    path("exams/<int:pk>/delete/", views.exam_delete, name="exam_delete"),
    path("exams/<int:pk>/", views.exam_detail, name="exam_detail"),
    path("marks/<int:pk>/delete/", views.mark_delete, name="mark_delete"),

    path("marks/dashboard/", views.mark_dashboard, name="mark_dashboard"),
]
