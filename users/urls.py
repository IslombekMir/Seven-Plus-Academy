from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("create/", views.create_user, name="create_user"),
    path("bulk-create/", views.bulk_create_users, name="bulk_create_users"),
    path("users_list/", views.users_list, name="users_list"),
    path("users_list/removed_users/", views.removed_users, name="removed_users"),
    path("edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("remove/<int:user_id>/", views.remove_user, name="remove_user"),
    path("restore/<int:user_id>/", views.restore_user, name="restore_user"),
    path("delete/<int:user_id>/", views.delete_user, name="delete_user"),
    path("reset_password/<int:user_id>/", views.reset_password, name="reset_password"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("profile/", views.profile, name="profile"),
    path('toggle-theme/', views.toggle_theme, name='toggle_theme'),

    path("teachers/", views.teachers_list, name="teachers_list"),
    path("teachers/<int:teacher_id>/edit/", views.edit_teacher_profile, name="edit_teacher_profile"),

    path("force-password-change/", views.force_password_change, name="force_password_change"),

    path("detail/<str:username>/", views.user_detail, name="user_detail"),
    path("detail/<str:username>/delete-related/<str:section>/", views.delete_user_related, name="delete_user_related"),
    path("detail/<str:username>/delete-user/", views.delete_user_only, name="delete_user_only"),
    path("detail/<str:username>/confirm-delete/<str:section>/", views.confirm_delete_user_related, name="confirm_delete_user_related"),
    path("detail/<str:username>/confirm-delete-user/", views.confirm_delete_user_only, name="confirm_delete_user_only"),
]
