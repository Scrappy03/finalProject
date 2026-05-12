from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from datetime import timedelta

from .forms import DailyEntryForm
from .models import UserProfile, DailyEntry


def clamp_percent(value):
    """Keep progress bar widths within valid percentage bounds."""
    return max(0, min(100, value))


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


@login_required
def dashboard(request):
    """Display the main dashboard with wellbeing overview."""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        user_profile = None
    
    # Get today's entry
    today = timezone.localdate()
    today_entry = DailyEntry.objects.filter(user=request.user, entry_date=today).first()
    
    # Get last 7 days of entries
    seven_days_ago = today - timedelta(days=7)
    recent_entries = list(DailyEntry.objects.filter(
        user=request.user,
        entry_date__gte=seven_days_ago
    ).order_by('-entry_date')[:7])
    recent_entry_count = len(recent_entries)
    
    # Calculate progress percentages
    sleep_progress_percent = 0
    energy_label = "--"
    mood_label = "--"
    energy_bar_score = 0
    exercise_completed = False
    if today_entry:
        sleep_progress_percent = clamp_percent((today_entry.sleep_quality / 10) * 100)
        energy_label = get_energy_label(today_entry.energy_rating)
        mood_label = get_mood_label(today_entry.mood_rating)
        energy_bar_score = today_entry.energy_rating
        exercise_completed = today_entry.exercise_completed
    
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
        'recent_entries': recent_entries,
        'recent_entry_rows': recent_entry_rows,
        'recent_entry_count': recent_entry_count,
        'sleep_progress_percent': sleep_progress_percent,
        'entries_progress_percent': entries_progress_percent,
        'average_sleep_quality': average_sleep_quality,
        'average_energy_rating': average_energy_rating,
        'average_mood_rating': average_mood_rating,
        'exercise_completed_count': exercise_completed_count,
        'energy_label': energy_label,
        'mood_label': mood_label,
        'energy_bar_score': energy_bar_score,
        'exercise_completed': exercise_completed,
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
def report(request):
    """Display the wellbeing report page."""
    return render(request, 'tracker/report.html')
