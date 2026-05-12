from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserProfile(models.Model):
    WELLBEING_FOCUS_CHOICES = [
        ("sleep", "Better Sleep"),
        ("energy", "More Energy"),
        ("routine", "Better Routine"),
        ("mood", "Better Mood"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    target_bedtime = models.TimeField()
    target_wake_time = models.TimeField()
    caffeine_cutoff = models.TimeField()

    weekly_exercise_goal = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(7)]
    )

    wellbeing_focus = models.CharField(
        max_length=20,
        choices=WELLBEING_FOCUS_CHOICES,
        default="sleep"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class DailyEntry(models.Model):
    SCREEN_TIME_CHOICES = [
        ("none", "None"),
        ("under_30", "Under 30 minutes"),
        ("30_60", "30–60 minutes"),
        ("1_2", "1–2 hours"),
        ("2_plus", "2+ hours"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_entries"
    )

    entry_date = models.DateField()

    bedtime = models.TimeField()
    wake_time = models.TimeField()

    sleep_quality = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    evening_screen_time = models.CharField(
        max_length=20,
        choices=SCREEN_TIME_CHOICES
    )

    caffeine_consumed = models.BooleanField(default=False)
    latest_caffeine_time = models.TimeField(null=True, blank=True)

    exercise_completed = models.BooleanField(default=False)

    energy_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    mood_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-entry_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "entry_date"],
                name="unique_daily_entry_per_user"
            )
        ]

    def clean(self):
        if self.caffeine_consumed and not self.latest_caffeine_time:
            raise ValidationError({
                "latest_caffeine_time": "Enter the latest caffeine time if caffeine was consumed."
            })

        if not self.caffeine_consumed and self.latest_caffeine_time:
            raise ValidationError({
                "latest_caffeine_time": "Remove the caffeine time if caffeine was not consumed."
            })

    def __str__(self):
        return f"{self.user.username} - {self.entry_date}"