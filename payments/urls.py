from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("enrollments/<int:enrollment_id>/create/", views.payment_create, name="payment_create"),
    path("<int:pk>/edit/", views.payment_edit, name="payment_edit"),
    path("<int:pk>/delete/", views.payment_delete, name="payment_delete"),
]
