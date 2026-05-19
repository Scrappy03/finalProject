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

    def test_signup_creates_user_profile_and_logs_user_in(self):
        response = self.client.post(reverse("tracker:signup"), {
            "full_name": "New User",
            "email": "newuser@example.com",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
            "wellbeing_focus": "routine",
            "target_bedtime": "22:15",
            "target_wake_time": "06:45",
            "caffeine_cutoff": "14:30",
            "weekly_exercise_goal": 4,
            "accept_terms": "on",
        })

        self.assertRedirects(response, reverse("tracker:dashboard"))
        user = get_user_model().objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertIn("_auth_user_id", self.client.session)
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.wellbeing_focus, "routine")
        self.assertEqual(profile.target_bedtime, time(22, 15))
        self.assertEqual(profile.target_wake_time, time(6, 45))
        self.assertEqual(profile.caffeine_cutoff, time(14, 30))
        self.assertEqual(profile.weekly_exercise_goal, 4)

    def test_signup_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing",
            email="newuser@example.com",
            password="pass12345",
        )

        response = self.client.post(reverse("tracker:signup"), {
            "full_name": "New User",
            "email": "newuser@example.com",
            "password1": "StrongPass123",
            "password2": "StrongPass123",
            "wellbeing_focus": "sleep",
            "target_bedtime": "22:30",
            "target_wake_time": "07:00",
            "caffeine_cutoff": "16:00",
            "weekly_exercise_goal": 3,
            "accept_terms": "on",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.assertFalse(get_user_model().objects.filter(username="newuser").exists())


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
        self.assertEqual(response.context["weekly_focus"]["title"], "Build your baseline")

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
        self.assertEqual(response.context["weekly_focus"]["title"], "Build your baseline")
        self.assertContains(response, "0/4")

    def test_dashboard_exercise_count_uses_current_calendar_week(self):
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=today.weekday())
        last_week = week_start - timezone.timedelta(days=1)

        UserProfile.objects.create(
            user=self.user,
            target_bedtime="22:30",
            target_wake_time="07:00",
            caffeine_cutoff="16:00",
            weekly_exercise_goal=4,
            wellbeing_focus="routine",
        )
        DailyEntry.objects.create(
            user=self.user,
            entry_date=last_week,
            bedtime="22:30",
            wake_time="07:00",
            sleep_quality=8,
            evening_screen_time="30_60",
            exercise_completed=True,
            energy_rating=7,
            mood_rating=8,
        )
        DailyEntry.objects.create(
            user=self.user,
            entry_date=today,
            bedtime="22:30",
            wake_time="07:00",
            sleep_quality=8,
            evening_screen_time="30_60",
            exercise_completed=True,
            energy_rating=7,
            mood_rating=8,
        )

        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(response.context["exercise_completed_count"], 1)
        self.assertContains(response, "1/4")

    def test_dashboard_weekly_focus_uses_exercise_goal_after_baseline(self):
        UserProfile.objects.create(
            user=self.user,
            target_bedtime="22:30",
            target_wake_time="07:00",
            caffeine_cutoff="16:00",
            weekly_exercise_goal=4,
            wellbeing_focus="routine",
        )
        for days_ago in range(3):
            DailyEntry.objects.create(
                user=self.user,
                entry_date=timezone.localdate() - timezone.timedelta(days=days_ago),
                bedtime="22:30",
                wake_time="07:00",
                sleep_quality=8,
                evening_screen_time="30_60",
                exercise_completed=False,
                energy_rating=7,
                mood_rating=8,
            )

        response = self.client.get(reverse("tracker:dashboard"))

        self.assertEqual(response.context["weekly_focus"]["title"], "Move toward your exercise goal")
        self.assertEqual(response.context["weekly_focus"]["progress_label"], "0/4 days")


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


class TrendsFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="trenduser",
            password="pass12345",
        )

    def test_trends_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("tracker:trends"))

        self.assertRedirects(
            response,
            f"{reverse('tracker:login')}?next={reverse('tracker:trends')}",
        )

    def test_trends_page_uses_logged_entries(self):
        self.client.force_login(self.user)
        DailyEntry.objects.create(
            user=self.user,
            entry_date=timezone.localdate(),
            bedtime="22:30",
            wake_time="06:30",
            sleep_quality=8,
            evening_screen_time="under_30",
            exercise_completed=True,
            energy_rating=7,
            mood_rating=9,
        )

        response = self.client.get(reverse("tracker:trends"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_range"], 7)
        self.assertEqual(response.context["entry_count"], 1)
        self.assertEqual(response.context["average_sleep_duration_label"], "8h 00m")
        self.assertEqual(response.context["exercise_count"], 1)
        self.assertAlmostEqual(response.context["logging_completion_percent"], 14.3, places=1)
        self.assertContains(response, "Wellbeing Trends")

    def test_trends_page_accepts_supported_range(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('tracker:trends')}?range=14")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_range"], 14)
