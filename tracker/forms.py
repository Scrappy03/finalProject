from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .models import DailyEntry


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
