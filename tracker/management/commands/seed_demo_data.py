import math
import os
import random
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tracker.models import DailyEntry, UserProfile


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def time_from_minutes(minutes):
    minutes = minutes % (24 * 60)
    return time(minutes // 60, minutes % 60)


class Command(BaseCommand):
    help = "Create a demo user with realistic wellbeing data for assessment."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="Demo")
        parser.add_argument("--email", default="demo@example.com")
        parser.add_argument("--password", default=os.environ.get("DEMO_PASSWORD"))
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the demo user's existing DailyEntry rows before seeding.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError(
                "Provide a password with --password or set DEMO_PASSWORD in the environment."
            )

        days = options["days"]
        if days < 14:
            raise CommandError("--days must be at least 14 so trends have enough data.")

        user_model = get_user_model()
        username = options["username"]
        email = options["email"]

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": "Demo",
                "last_name": "Account",
            },
        )
        user.email = email
        user.first_name = "Demo"
        user.last_name = "Account"
        user.set_password(password)
        user.is_active = True
        user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "target_bedtime": time(22, 30),
                "target_wake_time": time(7, 0),
                "caffeine_cutoff": time(14, 0),
                "weekly_exercise_goal": 4,
                "wellbeing_focus": "sleep",
            },
        )

        if options["clear"]:
            DailyEntry.objects.filter(user=user).delete()

        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)
        random_generator = random.Random(42)
        created_count = 0
        updated_count = 0

        for index in range(days):
            entry_date = start_date + timedelta(days=index)
            weekday = entry_date.weekday()
            progress = index / max(days - 1, 1)
            habit_improvement = progress * 1.15

            late_caffeine = weekday in {2, 4} and random_generator.random() < 0.72 - (progress * 0.35)
            exercise_completed = weekday in {0, 2, 5} or (
                progress > 0.55 and weekday == 3 and random_generator.random() < 0.65
            )
            high_screen = weekday in {4, 5, 6} and random_generator.random() < 0.72 - (progress * 0.25)

            evening_screen_time = "30_60"
            if high_screen:
                evening_screen_time = random_generator.choice(["1_2", "2_plus"])
            elif random_generator.random() < 0.28 + (progress * 0.25):
                evening_screen_time = random_generator.choice(["none", "under_30"])

            bedtime_minutes = 22 * 60 + 35
            wake_minutes = 7 * 60

            bedtime_minutes += int(math.sin(index / 5) * 18)
            bedtime_minutes += random_generator.randint(-18, 22)
            wake_minutes += random_generator.randint(-14, 20)

            if high_screen:
                bedtime_minutes += random_generator.randint(35, 85)
            if late_caffeine:
                bedtime_minutes += random_generator.randint(20, 55)
            if exercise_completed:
                bedtime_minutes -= random_generator.randint(5, 25)
            if progress > 0.65:
                bedtime_minutes -= 20
                wake_minutes -= 8

            bedtime = time_from_minutes(bedtime_minutes)
            wake_time = time_from_minutes(wake_minutes)

            sleep_minutes = (wake_minutes + 24 * 60) - bedtime_minutes
            if sleep_minutes > 13 * 60:
                sleep_minutes -= 24 * 60

            quality = 7.0
            quality += habit_improvement
            quality += 0.75 if exercise_completed else -0.25
            quality -= 1.25 if late_caffeine else 0
            quality -= 0.9 if high_screen else 0
            quality -= 0.7 if sleep_minutes < 7 * 60 else 0
            quality += random_generator.uniform(-0.55, 0.55)
            sleep_quality = round(clamp(quality, 2, 10))

            energy = sleep_quality + (1 if exercise_completed else 0)
            energy -= 1 if late_caffeine else 0
            energy += random_generator.choice([-1, 0, 0, 1])
            energy_rating = round(clamp(energy, 2, 10))

            mood = (sleep_quality + energy_rating) / 2
            mood += 0.6 if exercise_completed else 0
            mood -= 0.35 if high_screen else 0
            mood += random_generator.uniform(-0.7, 0.7)
            mood_rating = round(clamp(mood, 2, 10))

            latest_caffeine_time = None
            caffeine_consumed = random_generator.random() < 0.82
            if late_caffeine:
                caffeine_consumed = True
                latest_caffeine_time = time_from_minutes(15 * 60 + random_generator.randint(15, 150))
            elif caffeine_consumed:
                latest_caffeine_time = time_from_minutes(11 * 60 + random_generator.randint(0, 150))

            notes = self.note_for_entry(
                entry_date,
                sleep_quality,
                energy_rating,
                mood_rating,
                exercise_completed,
                late_caffeine,
                high_screen,
                progress,
            )

            entry, was_created = DailyEntry.objects.update_or_create(
                user=user,
                entry_date=entry_date,
                defaults={
                    "bedtime": bedtime,
                    "wake_time": wake_time,
                    "sleep_quality": sleep_quality,
                    "evening_screen_time": evening_screen_time,
                    "caffeine_consumed": caffeine_consumed,
                    "latest_caffeine_time": latest_caffeine_time,
                    "exercise_completed": exercise_completed,
                    "energy_rating": energy_rating,
                    "mood_rating": mood_rating,
                    "notes": notes,
                },
            )
            entry.full_clean()

            if was_created:
                created_count += 1
            else:
                updated_count += 1

        status = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{status} demo user '{username}' with {created_count} new and "
                f"{updated_count} updated daily entries."
            )
        )
        self.stdout.write(f"Login with username/email '{username}' / '{email}'.")

    def note_for_entry(
        self,
        entry_date: date,
        sleep_quality: int,
        energy_rating: int,
        mood_rating: int,
        exercise_completed: bool,
        late_caffeine: bool,
        high_screen: bool,
        progress: float,
    ):
        if progress > 0.75 and sleep_quality >= 8:
            return "Kept a calmer evening routine and woke up feeling more settled."
        if late_caffeine and high_screen:
            return "Later caffeine and extra screen time made it harder to switch off."
        if exercise_completed and energy_rating >= 8:
            return "Exercise helped energy stay steady through the afternoon."
        if mood_rating <= 5:
            return "Felt a bit flat today, so keeping the evening routine simple."
        if entry_date.weekday() in {5, 6}:
            return "Weekend routine was a little looser but still tracked the basics."
        return "A fairly typical day with useful signals for the weekly pattern."
