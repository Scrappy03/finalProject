from django.contrib import admin

from .models import DailyEntry, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "wellbeing_focus",
        "target_bedtime",
        "target_wake_time",
        "caffeine_cutoff",
        "weekly_exercise_goal",
        "updated_at",
    )
    list_filter = ("wellbeing_focus", "weekly_exercise_goal")
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    ordering = ("user__username",)


@admin.register(DailyEntry)
class DailyEntryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "entry_date",
        "sleep_quality",
        "energy_rating",
        "mood_rating",
        "exercise_completed",
        "caffeine_consumed",
        "created_at",
    )
    list_filter = (
        "exercise_completed",
        "caffeine_consumed",
        "evening_screen_time",
        "entry_date",
    )
    search_fields = ("user__username", "user__email", "notes")
    date_hierarchy = "entry_date"
    ordering = ("-entry_date", "-created_at")
