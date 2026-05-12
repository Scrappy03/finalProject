from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DailyEntry


class DailyEntryFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="pass12345",
        )
        self.client.force_login(self.user)

    def valid_entry_data(self):
        return {
            "entry_date": timezone.localdate(),
            "bedtime": "22:30",
            "wake_time": "07:00",
            "sleep_quality": 8,
            "evening_screen_time": "30_60",
            "energy_rating": 7,
            "mood_rating": 8,
            "notes": "Felt good after a steady routine.",
        }

    def test_entry_form_creates_daily_entry_for_logged_in_user(self):
        response = self.client.post(reverse("tracker:entry_create"), self.valid_entry_data())

        self.assertRedirects(response, reverse("tracker:dashboard"))
        entry = DailyEntry.objects.get(user=self.user)
        self.assertEqual(entry.sleep_quality, 8)
        self.assertEqual(entry.energy_rating, 7)
        self.assertEqual(entry.mood_rating, 8)

    def test_dashboard_uses_saved_daily_entries(self):
        DailyEntry.objects.create(
            user=self.user,
            entry_date=timezone.localdate(),
            bedtime="22:30",
            wake_time="07:00",
            sleep_quality=8,
            evening_screen_time="30_60",
            energy_rating=7,
            mood_rating=8,
        )

        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["recent_entry_count"], 1)
        self.assertEqual(response.context["today_entry"].sleep_quality, 8)
