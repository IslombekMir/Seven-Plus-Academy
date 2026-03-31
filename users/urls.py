from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("create/", views.create_user, name="create_user"),
    path("users_list/", views.users_list, name="users_list"),
    path("edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("reset_password/<int:user_id>/", views.reset_password, name="reset_password"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("profile/", views.profile, name="profile"),
    path('toggle-theme/', views.toggle_theme, name='toggle_theme'),

    path("teachers/", views.teachers_list, name="teachers_list"),
    path("teachers/<int:teacher_id>/edit/", views.edit_teacher_profile, name="edit_teacher_profile"),

    path("force-password-change/", views.force_password_change, name="force_password_change"),
]
