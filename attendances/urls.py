from django.urls import path
from . import views

app_name = "attendances"

urlpatterns = [
    path("", views.attendance_dashboard, name="dashboard"),
    path("groups/<int:group_id>/", views.attendance_group_detail, name="group_detail"),
    path("sessions/<int:pk>/", views.attendance_session_detail, name="session_detail"),
]
