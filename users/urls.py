from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("create/", views.create_user, name="create_user"),
    path("users_list/", views.users_list, name="users_list"),
    path("edit/<int:user_id>/", views.edit_user, name="edit_user"),
    path("delete/<int:user_id>/", views.delete_user, name="delete_user"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]