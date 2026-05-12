from django import forms

from .models import DailyEntry


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
