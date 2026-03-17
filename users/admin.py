from django.contrib import admin
from .models import User, RoleCounter, TeacherProfile, UserSettings

admin.site.register(User)
admin.site.register(RoleCounter)
admin.site.register(TeacherProfile)
admin.site.register(UserSettings)