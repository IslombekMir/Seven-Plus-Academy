from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("create/", views.create_user, name="create_user"),
    path("users_list/", views.users_list, name="users_list"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
]