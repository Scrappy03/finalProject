from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta

from .forms import DailyEntryForm, SanctuaryLoginForm
from .insights import build_insights_context
from .models import UserProfile, DailyEntry
from .utils import clamp_percent


class SanctuaryLoginView(LoginView):
    authentication_form = SanctuaryLoginForm
    redirect_authenticated_user = True
    template_name = "tracker/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.POST.get("remember"):
            self.request.session.set_expiry(0)
        return response


class SanctuaryLogoutView(LogoutView):
    pass


def get_user_profile(user):
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None


def get_energy_label(energy_rating):
    if energy_rating >= 8:
        return "High"
    if energy_rating >= 5:
        return "Medium"
    return "Low"


def get_mood_label(mood_rating):
    if mood_rating >= 8:
        return "Great"
    if mood_rating >= 5:
        return "Good"
    return "Fair"


def get_energy_text_class(energy_rating):
    if energy_rating >= 8:
        return "text-primary"
    if energy_rating >= 5:
        return "text-secondary"
    return "text-error"


def format_average_time(entries, field_name):
    if not entries:
        return "--"

    total_minutes = sum(
        getattr(entry, field_name).hour * 60 + getattr(entry, field_name).minute
        for entry in entries
    )
    average_minutes = round(total_minutes / len(entries))
    hours, minutes = divmod(average_minutes, 60)
    return f"{hours % 24:02d}:{minutes:02d}"


@login_required
def dashboard(request):
    """Display the main dashboard with wellbeing overview."""
    user_profile = get_user_profile(request.user)
    
    # Keep today's entry available for update logic, but dashboard cards use recent averages.
    today = timezone.localdate()
    today_entry = DailyEntry.objects.filter(user=request.user, entry_date=today).first()
    
    # Get last 7 days of entries
    seven_days_ago = today - timedelta(days=7)
    recent_entries = list(DailyEntry.objects.filter(
        user=request.user,
        entry_date__gte=seven_days_ago
    ).order_by('-entry_date')[:7])
    recent_entry_count = len(recent_entries)
    
    latest_entry = recent_entries[0] if recent_entries else None
    last_logged_entry = DailyEntry.objects.filter(user=request.user).order_by("-created_at").first()

    # Calculate 7-day overview values
    sleep_progress_percent = 0
    energy_label = "--"
    mood_label = "--"
    energy_bar_score = 0
    average_wake_time = "--"
    
    entries_progress_percent = 0
    if recent_entry_count > 0:
        entries_progress_percent = clamp_percent((recent_entry_count / 7) * 100)

    average_sleep_quality = 0
    average_energy_rating = 0
    average_mood_rating = 0
    exercise_completed_count = 0
    if recent_entry_count > 0:
        average_sleep_quality = sum(entry.sleep_quality for entry in recent_entries) / recent_entry_count
        average_energy_rating = sum(entry.energy_rating for entry in recent_entries) / recent_entry_count
        average_mood_rating = sum(entry.mood_rating for entry in recent_entries) / recent_entry_count
        exercise_completed_count = sum(1 for entry in recent_entries if entry.exercise_completed)
        average_wake_time = format_average_time(recent_entries, "wake_time")
        sleep_progress_percent = clamp_percent((average_sleep_quality / 10) * 100)
        energy_label = get_energy_label(average_energy_rating)
        mood_label = get_mood_label(average_mood_rating)
        energy_bar_score = round(average_energy_rating)

    recent_entry_rows = [
        {
            "entry": entry,
            "energy_label": get_energy_label(entry.energy_rating),
            "energy_text_class": get_energy_text_class(entry.energy_rating),
        }
        for entry in recent_entries
    ]
    chart_entries = list(reversed(recent_entries))
    chart_labels = [entry.entry_date.strftime("%a") for entry in chart_entries]
    sleep_chart_data = [entry.sleep_quality for entry in chart_entries]
    mood_chart_data = [entry.mood_rating for entry in chart_entries]

    context = {
        'user_profile': user_profile,
        'today_entry': today_entry,
        'latest_entry': latest_entry,
        'last_logged_entry': last_logged_entry,
        'recent_entries': recent_entries,
        'recent_entry_rows': recent_entry_rows,
        'recent_entry_count': recent_entry_count,
        'sleep_progress_percent': sleep_progress_percent,
        'entries_progress_percent': entries_progress_percent,
        'average_sleep_quality': average_sleep_quality,
        'average_energy_rating': average_energy_rating,
        'average_mood_rating': average_mood_rating,
        'exercise_completed_count': exercise_completed_count,
        'average_wake_time': average_wake_time,
        'energy_label': energy_label,
        'mood_label': mood_label,
        'energy_bar_score': energy_bar_score,
        'chart_labels': chart_labels,
        'sleep_chart_data': sleep_chart_data,
        'mood_chart_data': mood_chart_data,
    }
    
    return render(request, 'tracker/dashboard.html', context)


@login_required
def entry_create(request):
    """Create or update a daily wellbeing entry for the signed-in user."""
    today = timezone.localdate()
    entry = DailyEntry.objects.filter(user=request.user, entry_date=today).first()

    if request.method == "POST":
        posted_entry_date = request.POST.get("entry_date")
        entry = None
        if posted_entry_date:
            entry = DailyEntry.objects.filter(user=request.user, entry_date=posted_entry_date).first()
        form = DailyEntryForm(request.POST, instance=entry)
        if form.is_valid():
            daily_entry = form.save(commit=False)
            daily_entry.user = request.user
            daily_entry.save()
            return redirect("tracker:dashboard")
    else:
        form = DailyEntryForm(instance=entry, initial={"entry_date": today})

    return render(request, 'tracker/entry_form.html', {"form": form, "entry": entry})


@login_required
def insights(request):
    """Display the personal insights page."""
    user_profile = get_user_profile(request.user)
    context = build_insights_context(request.user, user_profile)
    return render(request, 'tracker/insights.html', context)


@login_required
def report(request):
    """Display the wellbeing report page."""
    return render(request, 'tracker/report.html')
