from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DailyEntry, UserProfile


class AuthFlowTests(TestCase):
    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("tracker:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('tracker:login')}?next={reverse('tracker:dashboard')}",
        )

    def test_login_accepts_user_email(self):
        get_user_model().objects.create_user(
            username="emailuser",
            email="emailuser@example.com",
            password="pass12345",
        )

        response = self.client.post(reverse("tracker:login"), {
            "username": "emailuser@example.com",
            "password": "pass12345",
        })

        self.assertRedirects(response, reverse("tracker:dashboard"))
        self.assertIn("_auth_user_id", self.client.session)


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

    def test_dashboard_uses_profile_exercise_goal(self):
        UserProfile.objects.create(
            user=self.user,
            target_bedtime="22:30",
            target_wake_time="07:00",
            caffeine_cutoff="16:00",
            weekly_exercise_goal=4,
            wellbeing_focus="routine",
        )

        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["exercise_completed_count"], 0)
        self.assertEqual(response.context["weekly_exercise_goal"], 4)
        self.assertContains(response, "0/4")


class GoalsFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="goaluser",
            password="pass12345",
        )
        self.client.force_login(self.user)

    def test_goals_page_creates_profile_when_missing(self):
        response = self.client.get(reverse("tracker:goals"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())
        self.assertEqual(response.context["user_profile"].target_bedtime, time(22, 30))

    def test_goals_page_updates_user_profile(self):
        UserProfile.objects.create(
            user=self.user,
            target_bedtime="22:30",
            target_wake_time="07:00",
            caffeine_cutoff="16:00",
            weekly_exercise_goal=3,
            wellbeing_focus="sleep",
        )

        response = self.client.post(reverse("tracker:goals"), {
            "wellbeing_focus": "energy",
            "target_bedtime": "23:00",
            "target_wake_time": "06:45",
            "caffeine_cutoff": "14:30",
            "weekly_exercise_goal": 4,
        })

        self.assertRedirects(response, reverse("tracker:goals"))
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.wellbeing_focus, "energy")
        self.assertEqual(profile.target_bedtime, time(23, 0))
        self.assertEqual(profile.target_wake_time, time(6, 45))
        self.assertEqual(profile.caffeine_cutoff, time(14, 30))
        self.assertEqual(profile.weekly_exercise_goal, 4)
