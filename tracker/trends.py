from datetime import timedelta
from statistics import median

from django.utils import timezone

from .models import DailyEntry
from .utils import clamp_percent


RANGE_OPTIONS = {
    7: "Last 7 Days",
    14: "Last 14 Days",
    30: "Last 30 Days",
}
SLEEP_DURATION_TARGET_HOURS = 8
SLEEP_DURATION_CHART_MAX_HOURS = 10
CONSISTENCY_WINDOW_MINUTES = 60


def get_selected_range(raw_range):
    try:
        selected_range = int(raw_range)
    except (TypeError, ValueError):
        return 7

    return selected_range if selected_range in RANGE_OPTIONS else 7


def time_to_minutes(value):
    return value.hour * 60 + value.minute


def bedtime_to_timeline_minutes(value):
    minutes = time_to_minutes(value)
    if minutes < 12 * 60:
        minutes += 24 * 60
    return minutes


def sleep_duration_hours(entry):
    bedtime_minutes = time_to_minutes(entry.bedtime)
    wake_minutes = time_to_minutes(entry.wake_time)
    duration_minutes = wake_minutes - bedtime_minutes
    if duration_minutes <= 0:
        duration_minutes += 24 * 60
    return duration_minutes / 60


def average(values):
    return sum(values) / len(values) if values else 0


def format_sleep_duration(hours):
    if not hours:
        return "--"

    total_minutes = round(hours * 60)
    duration_hours, duration_minutes = divmod(total_minutes, 60)
    return f"{duration_hours}h {duration_minutes:02d}m"


def build_consistency_stats(entries):
    if not entries:
        return {
            "percent": 0,
            "label": "--",
            "body": "Log entries to see how steady your bedtime and wake time are.",
        }

    typical_bedtime = median([bedtime_to_timeline_minutes(entry.bedtime) for entry in entries])
    typical_wake = median([time_to_minutes(entry.wake_time) for entry in entries])
    consistent_count = 0

    for entry in entries:
        bedtime_difference = abs(bedtime_to_timeline_minutes(entry.bedtime) - typical_bedtime)
        wake_difference = abs(time_to_minutes(entry.wake_time) - typical_wake)
        if bedtime_difference <= CONSISTENCY_WINDOW_MINUTES and wake_difference <= CONSISTENCY_WINDOW_MINUTES:
            consistent_count += 1

    consistency_percent = clamp_percent((consistent_count / len(entries)) * 100)
    if consistency_percent >= 80:
        body = "Your sleep timing has been steady across this range."
    elif consistency_percent >= 50:
        body = "Your sleep timing is partly consistent, with a few more variable days."
    else:
        body = "Your sleep timing has varied quite a bit across this range."

    return {
        "percent": consistency_percent,
        "label": f"{consistency_percent:.0f}%",
        "body": body,
    }


def build_trend_summary(entries, average_sleep_quality, average_energy, average_mood, consistency_stats):
    if not entries:
        return {
            "title": "Start your trend line",
            "body": "Log a few daily entries to see how sleep, energy, mood, exercise, caffeine, and screen time move over time.",
        }

    strongest_metric = max(
        [
            ("sleep quality", average_sleep_quality),
            ("energy", average_energy),
            ("mood", average_mood),
        ],
        key=lambda item: item[1],
    )

    if consistency_stats["percent"] >= 70:
        return {
            "title": "Your routine is taking shape",
            "body": (
                f"Your sleep timing was consistent on {consistency_stats['label']} of logged days, "
                f"with {strongest_metric[0]} currently averaging {strongest_metric[1]:.1f}/10."
            ),
        }

    return {
        "title": "Look for steadier rhythm",
        "body": (
            f"Your strongest recent score is {strongest_metric[0]} at {strongest_metric[1]:.1f}/10. "
            "Use the charts to see which habits tend to sit around your better days."
        ),
    }


def format_week_label(start_date, end_date):
    if start_date.month == end_date.month:
        return f"{start_date.strftime('%d')}-{end_date.strftime('%d %b')}"
    return f"{start_date.strftime('%d %b')}-{end_date.strftime('%d %b')}"


def build_sleep_chart_rows(date_range, entries_by_date, selected_range):
    if selected_range <= 14:
        rows = []
        for current_date in date_range:
            entry = entries_by_date.get(current_date)
            label = current_date.strftime("%a")

            if entry:
                duration = sleep_duration_hours(entry)
                rows.append({
                    "label": label,
                    "axis_label": label,
                    "value": f"{duration:.1f}h",
                    "height_percent": clamp_percent((duration / SLEEP_DURATION_CHART_MAX_HOURS) * 100),
                    "is_target": duration >= SLEEP_DURATION_TARGET_HOURS,
                })
            else:
                rows.append({
                    "label": label,
                    "axis_label": label,
                    "value": "--",
                    "height_percent": 4,
                    "is_target": False,
                })
        return rows

    rows = []
    for chunk_start in range(0, len(date_range), 7):
        chunk_dates = date_range[chunk_start:chunk_start + 7]
        chunk_entries = [
            entries_by_date[current_date]
            for current_date in chunk_dates
            if current_date in entries_by_date
        ]
        label = format_week_label(chunk_dates[0], chunk_dates[-1])

        if chunk_entries:
            average_duration = average([sleep_duration_hours(entry) for entry in chunk_entries])
            rows.append({
                "label": label,
                "axis_label": label,
                "value": f"{average_duration:.1f}h avg",
                "height_percent": clamp_percent(
                    (average_duration / SLEEP_DURATION_CHART_MAX_HOURS) * 100
                ),
                "is_target": average_duration >= SLEEP_DURATION_TARGET_HOURS,
            })
        else:
            rows.append({
                "label": label,
                "axis_label": label,
                "value": "--",
                "height_percent": 4,
                "is_target": False,
            })
    return rows


def build_logging_heatmap_rows(date_range, entries_by_date):
    rows = []
    for chunk_start in range(0, len(date_range), 7):
        week_dates = date_range[chunk_start:chunk_start + 7]
        rows.append([
            {
                "label": current_date.strftime("%a %d %b"),
                "day_label": current_date.strftime("%d"),
                "weekday_label": current_date.strftime("%a"),
                "has_entry": current_date in entries_by_date,
            }
            for current_date in week_dates
        ])
    return rows


def build_trends_context(user, raw_range):
    selected_range = get_selected_range(raw_range)
    today = timezone.localdate()
    start_date = today - timedelta(days=selected_range - 1)
    entries = list(
        DailyEntry.objects.filter(
            user=user,
            entry_date__gte=start_date,
            entry_date__lte=today,
        ).order_by("entry_date")
    )
    entries_by_date = {entry.entry_date: entry for entry in entries}
    date_range = [start_date + timedelta(days=offset) for offset in range(selected_range)]

    sleep_duration_values = [sleep_duration_hours(entry) for entry in entries]
    average_sleep_duration = average(sleep_duration_values)
    average_sleep_quality = average([entry.sleep_quality for entry in entries])
    average_energy = average([entry.energy_rating for entry in entries])
    average_mood = average([entry.mood_rating for entry in entries])
    consistency_stats = build_consistency_stats(entries)
    exercise_count = sum(1 for entry in entries if entry.exercise_completed)
    caffeine_count = sum(1 for entry in entries if entry.caffeine_consumed)
    low_screen_count = sum(1 for entry in entries if entry.evening_screen_time in {"none", "under_30"})
    logging_completion_percent = clamp_percent((len(entries) / selected_range) * 100)

    labels = []
    sleep_quality_chart_data = []
    mood_chart_data = []
    energy_chart_data = []

    sleep_chart_rows = build_sleep_chart_rows(date_range, entries_by_date, selected_range)

    for current_date in date_range:
        entry = entries_by_date.get(current_date)
        label = current_date.strftime("%a") if selected_range <= 14 else current_date.strftime("%d %b")
        labels.append(label)

        if entry:
            sleep_quality_chart_data.append(entry.sleep_quality)
            mood_chart_data.append(entry.mood_rating)
            energy_chart_data.append(entry.energy_rating)
        else:
            sleep_quality_chart_data.append(None)
            mood_chart_data.append(None)
            energy_chart_data.append(None)

    return {
        "range_options": RANGE_OPTIONS,
        "selected_range": selected_range,
        "entry_count": len(entries),
        "start_date": start_date,
        "end_date": today,
        "average_sleep_duration_label": format_sleep_duration(average_sleep_duration),
        "average_sleep_quality": average_sleep_quality,
        "average_energy": average_energy,
        "average_mood": average_mood,
        "consistency_stats": consistency_stats,
        "exercise_count": exercise_count,
        "caffeine_count": caffeine_count,
        "low_screen_count": low_screen_count,
        "logging_heatmap_rows": build_logging_heatmap_rows(date_range, entries_by_date),
        "logging_completion_percent": logging_completion_percent,
        "sleep_chart_rows": sleep_chart_rows,
        "sleep_chart_subtitle": (
            "Average hours slept per week." if selected_range == 30 else "Hours slept per logged night."
        ),
        "chart_labels": labels,
        "sleep_quality_chart_data": sleep_quality_chart_data,
        "mood_chart_data": mood_chart_data,
        "energy_chart_data": energy_chart_data,
        "trend_summary": build_trend_summary(
            entries,
            average_sleep_quality,
            average_energy,
            average_mood,
            consistency_stats,
        ),
    }
