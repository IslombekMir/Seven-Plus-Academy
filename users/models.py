from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import transaction

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
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

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

    def __str__(self):
        return f"{self.username} - {self.get_full_name()}"

class UserSettings(models.Model):
    user = models.OneToOneField(User, related_name="settings", on_delete=models.CASCADE)
    
    class Theme(models.TextChoices):
        LIGHT = 'LIGHT', 'Light'
        DARK = 'DARK', 'Dark'
    
    class Language(models.TextChoices):
        UZBEK = 'UZBEK', 'Uzbek'
        ENGLISH = 'ENGLISH', 'English'
    
    theme = models.CharField(max_length=20, choices=Theme.choices, default=Theme.LIGHT)
    language = models.CharField(max_length=30, choices=Language.choices, default=Language.UZBEK)