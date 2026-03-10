from django import forms
from .models import User

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter username"})
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"placeholder": "Enter password"})
    )

from django import forms
from .models import User

class UserCreateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "phone_number"]

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        # Restrict role choices based on current user
        if self.current_user:
            if self.current_user.role == User.Role.TEACHER:
                self.fields["role"].choices = [(User.Role.STUDENT, "Student")]
            elif self.current_user.role == User.Role.STUDENT:
                # Students shouldn't even see the form
                self.fields["role"].choices = []
