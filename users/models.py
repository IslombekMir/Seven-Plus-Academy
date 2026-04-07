from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import transaction
from django.utils.translation import gettext_lazy as _

class RoleCounter(models.Model):
    role = models.CharField(max_length=20, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.role}: {self.last_number}"

class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        editable=False 
    )

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        TEACHER = 'TEACHER', _('Teacher')
        STUDENT = 'STUDENT', _('Student')

    ROLE_PREFIXES = {
        Role.ADMIN: 'adm',
        Role.TEACHER: 'tch',
        Role.STUDENT: 'std',
    }

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone_number = models.CharField(max_length=15, blank=True)
    must_reset_password = models.BooleanField(default=True)

    def generate_username(self):
        prefix = self.ROLE_PREFIXES[self.role]

        # Wrap in a transaction to prevent race conditions
        with transaction.atomic():
            counter, _ = RoleCounter.objects.select_for_update().get_or_create(role=self.role)
            counter.last_number += 1
            counter.save()

            username = f"{prefix}{str(counter.last_number).zfill(4)}"

            return username


    def save(self, *args, **kwargs):
        if not self.pk and not self.username:
            self.username = self.generate_username()
            self.set_password(self.username)
        
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["first_name", "last_name", "role"], name="unique_full_name_per_role")
        ]

    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"

class UserSettings(models.Model):
    user = models.OneToOneField(User, related_name="settings", on_delete=models.CASCADE)
    
    class Theme(models.TextChoices):
        LIGHT = 'LIGHT', _('Light')
        DARK = 'DARK', _('Dark')
    
    class Language(models.TextChoices):
        UZBEK = 'UZBEK', _('Uzbek')
        ENGLISH = 'ENGLISH', _('English')
    
    theme = models.CharField(max_length=20, choices=Theme.choices, default=Theme.LIGHT)
    language = models.CharField(max_length=30, choices=Language.choices, default=Language.UZBEK)


class TeacherProfile(models.Model):
    teacher = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
        limit_choices_to={"role": User.Role.TEACHER},
    )
    bio = models.TextField(blank=True)
    picture = models.ImageField(upload_to="teacher_pictures/", blank=True, null=True)
    is_active_profile = models.BooleanField(default=True)

    def __str__(self):
        return f"TeacherProfile: {self.teacher.get_full_name() or self.teacher.username}"
