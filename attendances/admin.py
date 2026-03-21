from django.contrib import admin

from .models import Attendance, AttendanceSession


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("group", "date", "created_by", "created_at")
    list_filter = ("date", "group")
    search_fields = ("group__name", "created_by__first_name", "created_by__last_name", "created_by__username")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "updated_at")
    list_filter = ("status", "session__group", "session__date")
    search_fields = ("student__first_name", "student__last_name", "student__username", "session__group__name")
