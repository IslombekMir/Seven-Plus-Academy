from django import forms
from .models import User


class UserCreateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number", "role"]

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        if self.current_user and self.current_user.role == User.Role.TEACHER:
            self.fields["role"].choices = [
                (User.Role.STUDENT, "Student")
            ]