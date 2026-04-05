from django import forms
from .models import User, TeacherProfile
from django.contrib.auth.password_validation import validate_password
from django.forms import formset_factory, BaseFormSet
from django.core.exceptions import ValidationError
from lessons.models import Group


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
    
### Bul create users
class BulkUserMetaForm(forms.Form):
    role = forms.ChoiceField(choices=User.Role.choices)
    group = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        empty_label="Select group",
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)

        groups_qs = Group.objects.filter(is_active=True).select_related("subject").order_by("name")
        if self.current_user and self.current_user.role == User.Role.TEACHER:
            groups_qs = groups_qs.filter(teacher=self.current_user)

        self.fields["group"].queryset = groups_qs

        if self.current_user and self.current_user.role == User.Role.TEACHER:
            self.fields["role"].initial = User.Role.STUDENT
            self.fields["role"].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()

        if self.current_user and self.current_user.role == User.Role.TEACHER:
            cleaned_data["role"] = User.Role.STUDENT

        return cleaned_data

class BulkUserRowForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=15, required=False)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["first_name"] = (cleaned_data.get("first_name") or "").strip()
        cleaned_data["last_name"] = (cleaned_data.get("last_name") or "").strip()
        cleaned_data["phone_number"] = (cleaned_data.get("phone_number") or "").strip()
        return cleaned_data


class BaseBulkUserRowFormSet(BaseFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        non_empty_rows = 0
        seen_name_keys = set()

        for form in self.forms:
            first_name = (form.cleaned_data.get("first_name") or "").strip()
            last_name = (form.cleaned_data.get("last_name") or "").strip()
            phone_number = (form.cleaned_data.get("phone_number") or "").strip()

            if not any([first_name, last_name, phone_number]):
                continue

            non_empty_rows += 1

            name_key = (first_name.lower(), last_name.lower())
            if name_key in seen_name_keys:
                raise forms.ValidationError(
                    "Duplicate first name + last name rows found in the bulk table."
                )
            seen_name_keys.add(name_key)

        if non_empty_rows == 0:
            raise forms.ValidationError("Add at least one user row.")

    def validate_against_role(self, role):
        for form in self.forms:
            first_name = (form.cleaned_data.get("first_name") or "").strip()
            last_name = (form.cleaned_data.get("last_name") or "").strip()
            phone_number = (form.cleaned_data.get("phone_number") or "").strip()

            if not any([first_name, last_name, phone_number]):
                continue

            if User.objects.filter(
                first_name=first_name,
                last_name=last_name,
                role=role,
            ).exists():
                form.add_error(
                    None,
                    "A user with this first name, last name, and role already exists."
                )

BulkUserRowFormSet = formset_factory(
    BulkUserRowForm,
    formset=BaseBulkUserRowFormSet,
    extra=10,
)
