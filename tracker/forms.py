from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import DailyEntry, UserProfile


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
