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

class UserCreateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "phone_number"]

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        if self.current_user:
            if self.current_user.role == User.Role.TEACHER:
                # Remove the role field completely
                self.fields.pop("role", None)


