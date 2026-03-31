from django import forms
from .models import User, TeacherProfile
from django.contrib.auth.password_validation import validate_password

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

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number"]

class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ["bio", "picture", "is_active_profile"]

class FirstLoginPasswordChangeForm(forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"placeholder": "Enter new password"}),
        validators=[validate_password],  # optional, Django’s validators
    )
    new_password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password"})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("new_password1")
        pw2 = cleaned_data.get("new_password2")

        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user