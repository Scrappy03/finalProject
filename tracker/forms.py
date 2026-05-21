from datetime import time

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import DailyEntry, UserProfile


class AccountSettingsForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Full name",
        required=False,
        widget=forms.TextInput(attrs={
            "autocomplete": "name",
            "placeholder": "Enter your name",
        }),
    )

    class Meta:
        model = get_user_model()
        fields = ["full_name", "email", "username"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "autocomplete": "email",
                "placeholder": "name@example.com",
            }),
            "username": forms.TextInput(attrs={
                "autocomplete": "username",
                "placeholder": "Username",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["full_name"].initial = self.instance.get_full_name()

        field_class = (
            "w-full bg-transparent border-0 border-b border-outline-variant/50 "
            "focus:border-primary focus:ring-0 px-0 py-2 font-body-md text-body-md "
            "text-on-surface transition-colors focus:bg-surface-container-low "
            "focus:px-4 rounded-t-md"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = field_class

    def clean_email(self):
        email = self.cleaned_data["email"]
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"]
        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name_parts = self.cleaned_data.get("full_name", "").split()
        user.first_name = full_name_parts[0] if full_name_parts else ""
        user.last_name = " ".join(full_name_parts[1:])
        if commit:
            user.save()
        return user


class SanctuaryPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_class = (
            "w-full bg-surface-container-low border-0 border-b-2 border-outline-variant/30 "
            "focus:border-primary focus:ring-0 px-4 py-3 font-body-md text-body-md "
            "text-on-surface rounded-t-lg transition-colors"
        )
        placeholders = {
            "old_password": "Current password",
            "new_password1": "Enter new password",
            "new_password2": "Confirm new password",
        }
        for name, field in self.fields.items():
            field.widget.attrs["class"] = field_class
            field.widget.attrs["placeholder"] = placeholders.get(name, "")


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "placeholder": "Current password",
        }),
    )
    confirmation = forms.CharField(
        label='Type "DELETE"',
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "placeholder": "DELETE",
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        field_class = (
            "w-full bg-surface-container-low border-0 border-b-2 border-outline-variant/30 "
            "focus:border-error focus:ring-0 px-4 py-3 font-body-md text-body-md "
            "text-on-surface rounded-t-xl transition-colors"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = field_class

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Enter your current password.")
        return password

    def clean_confirmation(self):
        confirmation = self.cleaned_data["confirmation"]
        if confirmation != "DELETE":
            raise forms.ValidationError('Type "DELETE" to confirm account deletion.')
        return confirmation


class SanctuaryLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(attrs={
            "autocomplete": "username",
            "placeholder": "name@example.com",
        }),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "placeholder": "••••••••",
        }),
    )

    def clean(self):
        username_or_email = self.cleaned_data.get("username")
        if username_or_email and "@" in username_or_email:
            user = get_user_model().objects.filter(email__iexact=username_or_email).first()
            if user:
                self.cleaned_data["username"] = user.get_username()
        return super().clean()

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        field_class = (
            "w-full bg-transparent border-none py-3 px-1 text-on-surface "
            "placeholder:text-outline-variant focus:ring-0 outline-none font-body-md"
        )
        self.fields["username"].widget.attrs["class"] = field_class
        self.fields["password"].widget.attrs["class"] = field_class


class SanctuarySignupForm(forms.Form):
    full_name = forms.CharField(
        label="Full name",
        widget=forms.TextInput(attrs={
            "autocomplete": "name",
            "placeholder": "Enter your name",
        }),
    )
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(attrs={
            "autocomplete": "email",
            "placeholder": "name@example.com",
        }),
    )
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "Create a password",
        }),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "placeholder": "Confirm your password",
        }),
    )
    wellbeing_focus = forms.ChoiceField(
        label="Main wellbeing focus",
        choices=UserProfile.WELLBEING_FOCUS_CHOICES,
        initial="sleep",
    )
    target_bedtime = forms.TimeField(
        label="Target bedtime",
        input_formats=["%H:%M"],
        initial=time(22, 30),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    target_wake_time = forms.TimeField(
        label="Target wake time",
        input_formats=["%H:%M"],
        initial=time(7, 0),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    caffeine_cutoff = forms.TimeField(
        label="Caffeine cutoff",
        input_formats=["%H:%M"],
        initial=time(14, 0),
        widget=forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
    )
    weekly_exercise_goal = forms.IntegerField(
        label="Weekly exercise goal",
        min_value=0,
        max_value=7,
        initial=3,
        widget=forms.NumberInput(attrs={
            "min": 0,
            "max": 7,
            "placeholder": "Sessions/week",
        }),
    )
    accept_terms = forms.BooleanField(
        label="I agree to the Terms of Service and Privacy Policy",
        widget=forms.CheckboxInput(attrs={
            "class": (
                "mt-1 w-5 h-5 rounded border-outline-variant text-primary "
                "focus:ring-primary-container"
            ),
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_class = (
            "w-full bg-transparent border-none py-2 pl-9 pr-1 text-on-surface "
            "placeholder:text-outline-variant focus:ring-0 outline-none font-body-md"
        )
        for name, field in self.fields.items():
            if name != "accept_terms":
                field.widget.attrs["class"] = field_class

    def clean_email(self):
        email = self.cleaned_data["email"]
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two password fields did not match.")

        if password1:
            try:
                password_validation.validate_password(password1)
            except forms.ValidationError as error:
                self.add_error("password1", error)

        return cleaned_data

    def get_unique_username(self):
        email_prefix = self.cleaned_data["email"].split("@")[0]
        base_username = "".join(
            character for character in email_prefix if character.isalnum() or character in {"_", "-"}
        ) or "user"
        username = base_username
        counter = 1
        user_model = get_user_model()
        while user_model.objects.filter(username__iexact=username).exists():
            counter += 1
            username = f"{base_username}{counter}"
        return username

    def save(self):
        full_name_parts = self.cleaned_data["full_name"].split()
        first_name = full_name_parts[0]
        last_name = " ".join(full_name_parts[1:])
        user = get_user_model().objects.create_user(
            username=self.get_unique_username(),
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=first_name,
            last_name=last_name,
        )
        UserProfile.objects.create(
            user=user,
            target_bedtime=self.cleaned_data["target_bedtime"],
            target_wake_time=self.cleaned_data["target_wake_time"],
            caffeine_cutoff=self.cleaned_data["caffeine_cutoff"],
            weekly_exercise_goal=self.cleaned_data["weekly_exercise_goal"],
            wellbeing_focus=self.cleaned_data["wellbeing_focus"],
        )
        return user


class DailyEntryForm(forms.ModelForm):
    field_class = (
        "w-full rounded-lg border border-outline-variant bg-surface-container-lowest "
        "px-4 py-3 font-body-md text-body-md text-on-surface focus:ring-2 "
        "focus:ring-primary/20 focus:border-primary"
    )
    checkbox_class = "sr-only peer"

    class Meta:
        model = DailyEntry
        fields = [
            "entry_date",
            "bedtime",
            "wake_time",
            "sleep_quality",
            "evening_screen_time",
            "caffeine_consumed",
            "latest_caffeine_time",
            "exercise_completed",
            "energy_rating",
            "mood_rating",
            "notes",
        ]
        widgets = {
            "entry_date": forms.DateInput(attrs={"type": "date"}),
            "bedtime": forms.TimeInput(attrs={"type": "time"}),
            "wake_time": forms.TimeInput(attrs={"type": "time"}),
            "sleep_quality": forms.NumberInput(attrs={"type": "range"}),
            "energy_rating": forms.NumberInput(attrs={"type": "range"}),
            "mood_rating": forms.HiddenInput(),
            "latest_caffeine_time": forms.TimeInput(attrs={"type": "time"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = self.checkbox_class
            elif isinstance(field.widget, forms.HiddenInput):
                continue
            elif name in {"sleep_quality", "energy_rating"}:
                field.widget.attrs["class"] = "custom-slider my-4"
            else:
                field.widget.attrs["class"] = self.field_class

            if name in {"sleep_quality", "energy_rating", "mood_rating"}:
                field.widget.attrs.update({"min": 1, "max": 10})


class UserProfileForm(forms.ModelForm):
    field_class = (
        "w-full bg-surface-container-low border-none border-b-2 border-outline-variant "
        "focus:border-primary focus:ring-0 rounded-t-xl p-4 font-body-md text-body-md "
        "text-on-surface transition-all"
    )

    class Meta:
        model = UserProfile
        fields = [
            "wellbeing_focus",
            "target_bedtime",
            "target_wake_time",
            "caffeine_cutoff",
            "weekly_exercise_goal",
        ]
        widgets = {
            "target_bedtime": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "target_wake_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "caffeine_cutoff": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "weekly_exercise_goal": forms.NumberInput(attrs={"min": 0, "max": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_bedtime"].input_formats = ["%H:%M"]
        self.fields["target_wake_time"].input_formats = ["%H:%M"]
        self.fields["caffeine_cutoff"].input_formats = ["%H:%M"]

        for name, field in self.fields.items():
            field.widget.attrs["class"] = self.field_class
            if name == "weekly_exercise_goal":
                field.widget.attrs["class"] = (
                    "flex-1 min-w-0 bg-transparent border-none focus:ring-0 text-center "
                    "font-headline-sm text-headline-sm text-on-surface"
                )
