from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path("subjects_list/", views.subjects_list, name="subjects_list"),
]
