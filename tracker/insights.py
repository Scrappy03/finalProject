from datetime import time, timedelta
from statistics import median

from django.utils import timezone

from .models import DailyEntry
from .utils import clamp_percent


RECENT_INSIGHT_LIMIT = 30
SLEEP_DURATION_LOOKBACK_DAYS = 7
ADULT_SLEEP_MINIMUM_HOURS = 7
INSIGHT_SIGNAL_THRESHOLD = 0.3
SUMMARY_SIGNAL_THRESHOLD = 0.2
SLEEP_QUALITY_THRESHOLD = 7
SLEEP_TIMING_WINDOW_MINUTES = 60
DEFAULT_CAFFEINE_CUTOFF = time(16, 0)
EARLY_SIGN_MIN_GROUP_SIZE = 2
CLEAR_PATTERN_MIN_GROUP_SIZE = 4


def get_confidence_label(*group_counts):
    if not group_counts or min(group_counts) == 0:
        return "Needs more data"
    if min(group_counts) >= CLEAR_PATTERN_MIN_GROUP_SIZE:
        return "Clear pattern"
    if min(group_counts) >= EARLY_SIGN_MIN_GROUP_SIZE:
        return "Early sign"
    return "Needs more data"


def average_field(entries, field_name):
    if not entries:
        return 0
    return sum(getattr(entry, field_name) for entry in entries) / len(entries)


def average(values):
    return sum(values) / len(values) if values else 0


def time_to_minutes(value):
    return value.hour * 60 + value.minute


def sleep_duration_hours(entry):
    bedtime_minutes = time_to_minutes(entry.bedtime)
    wake_minutes = time_to_minutes(entry.wake_time)
    duration_minutes = wake_minutes - bedtime_minutes
    if duration_minutes <= 0:
        duration_minutes += 24 * 60
    return duration_minutes / 60


def format_sleep_duration(hours):
    if not hours:
        return "--"

    total_minutes = round(hours * 60)
    duration_hours, duration_minutes = divmod(total_minutes, 60)
    return f"{duration_hours}h {duration_minutes:02d}m"


def format_minutes_as_time(total_minutes):
    hours, minutes = divmod(round(total_minutes) % (24 * 60), 60)
    return f"{hours:02d}:{minutes:02d}"


def bedtime_to_timeline_minutes(value):
    minutes = time_to_minutes(value)
    if minutes < 12 * 60:
        minutes += 24 * 60
    return minutes


def get_target_time_labels(user_profile):
    if not user_profile:
        return {
            "target_bedtime": "--",
            "target_wake_time": "--",
            "has_targets": False,
        }

    return {
        "target_bedtime": format_minutes_as_time(time_to_minutes(user_profile.target_bedtime)),
        "target_wake_time": format_minutes_as_time(time_to_minutes(user_profile.target_wake_time)),
        "has_targets": True,
    }


def build_sleep_duration_insight(entries):
    cutoff_date = timezone.localdate() - timedelta(days=SLEEP_DURATION_LOOKBACK_DAYS - 1)
    recent_entries = [
        entry
        for entry in entries
        if entry.entry_date >= cutoff_date
    ]
    average_duration = average([sleep_duration_hours(entry) for entry in recent_entries])
    is_below_guideline = bool(recent_entries and average_duration < ADULT_SLEEP_MINIMUM_HOURS)

    if not recent_entries:
        summary = "Log a few nights so Sanctuary can compare your sleep duration with adult sleep guidance."
        action_text = "Start by logging bedtime and wake time for the next few days."
        confidence_label = "Needs more data"
    elif is_below_guideline:
        summary = (
            f"Your average sleep over the last 7 days is {average_duration:.1f} hours, which is below the commonly "
            "recommended adult guideline of 7 or more hours per night."
        )
        action_text = (
            "Consider prioritising sleep duration before focusing on smaller lifestyle changes, such as by moving "
            "bedtime earlier in a realistic 15-minute step."
        )
        confidence_label = "Worth prioritising"
    else:
        summary = (
            f"Your average sleep over the last 7 days is {average_duration:.1f} hours, meeting the common adult "
            "guideline of 7 or more hours per night."
        )
        action_text = "Keep tracking duration alongside sleep quality so you can see whether enough sleep is also restorative."
        confidence_label = "On track"

    return {
        "entry_count": len(recent_entries),
        "average_duration": average_duration,
        "average_duration_label": format_sleep_duration(average_duration),
        "bar_percent": clamp_percent((average_duration / 10) * 100),
        "guideline_hours": ADULT_SLEEP_MINIMUM_HOURS,
        "is_below_guideline": is_below_guideline,
        "confidence_label": confidence_label,
        "summary": summary,
        "research_context": (
            "The American Academy of Sleep Medicine and Sleep Research Society recommend that adults sleep 7 or more "
            "hours per night on a regular basis to support health and wellbeing."
        ),
        "action_text": action_text,
    }


def build_late_caffeine_sleep_insight(entries, user_profile):
    caffeine_cutoff = user_profile.caffeine_cutoff if user_profile else DEFAULT_CAFFEINE_CUTOFF
    late_caffeine_entries = []
    no_or_early_caffeine_entries = []

    for entry in entries:
        is_late_caffeine = (
            entry.caffeine_consumed
            and entry.latest_caffeine_time
            and entry.latest_caffeine_time > caffeine_cutoff
        )
        if is_late_caffeine:
            late_caffeine_entries.append(entry)
        else:
            no_or_early_caffeine_entries.append(entry)

    late_average = average_field(late_caffeine_entries, "sleep_quality")
    no_or_early_average = average_field(no_or_early_caffeine_entries, "sleep_quality")
    average_difference = no_or_early_average - late_average
    has_comparison = bool(late_caffeine_entries and no_or_early_caffeine_entries)

    if has_comparison:
        if average_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"When caffeine stayed before {caffeine_cutoff.strftime('%H:%M')}, your sleep quality averaged "
                f"{average_difference:.1f} points higher."
            )
        elif average_difference < -SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                "Late caffeine days are currently averaging slightly higher sleep quality, so this pattern needs more "
                "entries before drawing a conclusion."
            )
        else:
            summary = (
                "Your sleep quality is currently similar across late-caffeine and no-or-early-caffeine days."
            )
    else:
        summary = (
            "Log at least one late-caffeine day and one no-or-early-caffeine day to compare this pattern."
        )

    return {
        "has_comparison": has_comparison,
        "cutoff_label": caffeine_cutoff.strftime("%H:%M"),
        "late_average": late_average,
        "no_or_early_average": no_or_early_average,
        "late_count": len(late_caffeine_entries),
        "no_or_early_count": len(no_or_early_caffeine_entries),
        "confidence_label": get_confidence_label(
            len(late_caffeine_entries),
            len(no_or_early_caffeine_entries),
        ),
        "late_bar_percent": clamp_percent((late_average / 10) * 100),
        "no_or_early_bar_percent": clamp_percent((no_or_early_average / 10) * 100),
        "average_difference": average_difference,
        "summary": summary,
        "research_context": (
            "Research suggests caffeine's effect on sleep depends on both dose and timing, with larger doses closer to "
            "bedtime having a stronger negative impact."
        ),
        "action_text": (
            "This does not prove caffeine caused the difference, but it may be a useful habit to test by keeping "
            "caffeine before your cutoff for the next few entries."
        ),
    }


def build_screen_time_sleep_insight(entries):
    low_screen_values = {"none", "under_30"}
    higher_screen_values = {"30_60", "1_2", "2_plus"}
    low_screen_entries = [
        entry
        for entry in entries
        if entry.evening_screen_time in low_screen_values
    ]
    higher_screen_entries = [
        entry
        for entry in entries
        if entry.evening_screen_time in higher_screen_values
    ]

    low_screen_average = average_field(low_screen_entries, "sleep_quality")
    higher_screen_average = average_field(higher_screen_entries, "sleep_quality")
    average_difference = low_screen_average - higher_screen_average
    has_comparison = bool(low_screen_entries and higher_screen_entries)

    if has_comparison:
        if average_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"On lower-screen evenings, your sleep quality averaged {average_difference:.1f} points higher than "
                "nights with 30 minutes or more of screen time."
            )
        elif average_difference < -SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                "Higher-screen evenings are currently averaging slightly better sleep quality, so this pattern needs "
                "more entries before drawing a conclusion."
            )
        else:
            summary = (
                "Your sleep quality is currently similar across lower-screen and higher-screen evenings."
            )
    else:
        summary = (
            "Log both lower-screen evenings and evenings with 30 minutes or more of screen time to compare this pattern."
        )

    return {
        "has_comparison": has_comparison,
        "higher_screen_average": higher_screen_average,
        "low_screen_average": low_screen_average,
        "higher_screen_count": len(higher_screen_entries),
        "low_screen_count": len(low_screen_entries),
        "confidence_label": get_confidence_label(
            len(higher_screen_entries),
            len(low_screen_entries),
        ),
        "higher_screen_bar_percent": clamp_percent((higher_screen_average / 10) * 100),
        "low_screen_bar_percent": clamp_percent((low_screen_average / 10) * 100),
        "average_difference": average_difference,
        "summary": summary,
        "research_context": (
            "Research has associated increased screen time with adverse sleep outcomes, while noting that more work is "
            "needed on causality and age-specific guidance."
        ),
        "action_text": (
            "Try treating lower screen use before bed as a practical sleep-supporting experiment rather than a strict rule."
        ),
    }


def build_exercise_energy_mood_insight(entries):
    exercise_entries = [entry for entry in entries if entry.exercise_completed]
    rest_entries = [entry for entry in entries if not entry.exercise_completed]

    exercise_energy_average = average_field(exercise_entries, "energy_rating")
    rest_energy_average = average_field(rest_entries, "energy_rating")
    exercise_mood_average = average_field(exercise_entries, "mood_rating")
    rest_mood_average = average_field(rest_entries, "mood_rating")
    energy_difference = exercise_energy_average - rest_energy_average
    mood_difference = exercise_mood_average - rest_mood_average
    has_comparison = bool(exercise_entries and rest_entries)
    exercise_vitality_average = (exercise_energy_average + exercise_mood_average) / 2
    rest_vitality_average = (rest_energy_average + rest_mood_average) / 2
    vitality_difference = exercise_vitality_average - rest_vitality_average

    if has_comparison:
        if energy_difference > SUMMARY_SIGNAL_THRESHOLD and mood_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"On exercise days, your average energy was {energy_difference:.1f} points higher and mood was "
                f"{mood_difference:.1f} points higher than non-exercise days."
            )
        elif energy_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"Exercise days currently show the clearest lift in energy, averaging {energy_difference:.1f} points "
                "higher than non-exercise days."
            )
        elif mood_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"Exercise days currently show the clearest lift in mood, averaging {mood_difference:.1f} points higher "
                "than non-exercise days."
            )
        elif energy_difference < -SUMMARY_SIGNAL_THRESHOLD or mood_difference < -SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                "Your exercise days are not currently averaging higher across energy and mood, so this pattern may need "
                "more entries or closer context."
            )
        else:
            summary = (
                "Your energy and mood are currently similar across exercise and non-exercise days."
            )
    else:
        summary = (
            "Log both exercise and non-exercise days to compare how movement relates to your energy and mood."
        )

    vitality_average = 0
    if entries:
        vitality_average = (
            average_field(entries, "energy_rating") + average_field(entries, "mood_rating")
        ) / 2

    return {
        "has_comparison": has_comparison,
        "exercise_count": len(exercise_entries),
        "rest_count": len(rest_entries),
        "confidence_label": get_confidence_label(
            len(exercise_entries),
            len(rest_entries),
        ),
        "exercise_energy_average": exercise_energy_average,
        "rest_energy_average": rest_energy_average,
        "exercise_mood_average": exercise_mood_average,
        "rest_mood_average": rest_mood_average,
        "exercise_energy_bar_percent": clamp_percent((exercise_energy_average / 10) * 100),
        "rest_energy_bar_percent": clamp_percent((rest_energy_average / 10) * 100),
        "exercise_mood_bar_percent": clamp_percent((exercise_mood_average / 10) * 100),
        "rest_mood_bar_percent": clamp_percent((rest_mood_average / 10) * 100),
        "vitality_average": vitality_average,
        "vitality_difference": vitality_difference,
        "summary": summary,
        "research_context": (
            "Research reviews generally link regular exercise with better sleep quality and reduced sleep disorder "
            "symptoms, although effects can vary by timing, duration, intensity, age, sex, and fitness level."
        ),
        "action_text": (
            "This is an association in your logs, so keep tracking movement alongside sleep, energy, and mood to see "
            "whether the pattern holds."
        ),
    }


def build_sleep_quality_mood_energy_insight(entries):
    high_sleep_entries = [entry for entry in entries if entry.sleep_quality >= SLEEP_QUALITY_THRESHOLD]
    lower_sleep_entries = [entry for entry in entries if entry.sleep_quality < SLEEP_QUALITY_THRESHOLD]

    high_sleep_energy_average = average_field(high_sleep_entries, "energy_rating")
    lower_sleep_energy_average = average_field(lower_sleep_entries, "energy_rating")
    high_sleep_mood_average = average_field(high_sleep_entries, "mood_rating")
    lower_sleep_mood_average = average_field(lower_sleep_entries, "mood_rating")
    energy_difference = high_sleep_energy_average - lower_sleep_energy_average
    mood_difference = high_sleep_mood_average - lower_sleep_mood_average
    wellbeing_difference = ((energy_difference + mood_difference) / 2)
    has_comparison = bool(high_sleep_entries and lower_sleep_entries)

    if has_comparison:
        if energy_difference > SUMMARY_SIGNAL_THRESHOLD and mood_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"On higher-quality sleep days, your energy averaged {energy_difference:.1f} points higher and mood "
                f"averaged {mood_difference:.1f} points higher."
            )
        elif energy_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"Higher-quality sleep days currently show the clearest lift in energy, averaging "
                f"{energy_difference:.1f} points higher."
            )
        elif mood_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"Higher-quality sleep days currently show the clearest lift in mood, averaging "
                f"{mood_difference:.1f} points higher."
            )
        elif energy_difference < -SUMMARY_SIGNAL_THRESHOLD or mood_difference < -SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                "Higher-quality sleep is not currently averaging higher across mood and energy, so this pattern needs "
                "more entries before drawing a conclusion."
            )
        else:
            summary = (
                "Your energy and mood are currently similar across higher and lower sleep-quality days."
            )
    else:
        summary = (
            "Log both higher and lower sleep-quality days to compare how sleep quality relates to energy and mood."
        )

    return {
        "has_comparison": has_comparison,
        "high_sleep_count": len(high_sleep_entries),
        "lower_sleep_count": len(lower_sleep_entries),
        "confidence_label": get_confidence_label(
            len(high_sleep_entries),
            len(lower_sleep_entries),
        ),
        "high_sleep_energy_average": high_sleep_energy_average,
        "lower_sleep_energy_average": lower_sleep_energy_average,
        "high_sleep_mood_average": high_sleep_mood_average,
        "lower_sleep_mood_average": lower_sleep_mood_average,
        "high_sleep_energy_bar_percent": clamp_percent((high_sleep_energy_average / 10) * 100),
        "lower_sleep_energy_bar_percent": clamp_percent((lower_sleep_energy_average / 10) * 100),
        "high_sleep_mood_bar_percent": clamp_percent((high_sleep_mood_average / 10) * 100),
        "lower_sleep_mood_bar_percent": clamp_percent((lower_sleep_mood_average / 10) * 100),
        "wellbeing_difference": wellbeing_difference,
        "summary": summary,
        "research_context": (
            "Sleep quality is closely connected with next-day functioning, so comparing it with energy and mood can help "
            "show whether recovery is supporting your wider wellbeing."
        ),
        "action_text": (
            "Use this as a prompt to test one sleep-supporting habit and watch whether energy or mood changes over time."
        ),
    }


def build_sleep_timing_consistency_insight(entries, user_profile):
    target_time_labels = get_target_time_labels(user_profile)

    if not entries:
        return {
            "has_comparison": False,
            "consistent_count": 0,
            "variable_count": 0,
            "confidence_label": "Needs more data",
            "consistent_average": 0,
            "variable_average": 0,
            "consistent_bar_percent": 0,
            "variable_bar_percent": 0,
            "consistency_percent": 0,
            "typical_bedtime": "--",
            "typical_wake_time": "--",
            **target_time_labels,
            "sleep_quality_difference": 0,
            "summary": "Log a few entries with bedtime and wake time to compare sleep timing consistency.",
            "research_context": (
                "Sleep regularity is increasingly recognised as an important health factor, not just a companion to "
                "sleep duration."
            ),
            "action_text": "Start by logging enough bedtime and wake-time entries to reveal your usual sleep window.",
        }

    typical_bedtime_minutes = median([bedtime_to_timeline_minutes(entry.bedtime) for entry in entries])
    typical_wake_minutes = median([time_to_minutes(entry.wake_time) for entry in entries])

    consistent_entries = []
    variable_entries = []
    for entry in entries:
        bedtime_difference = abs(bedtime_to_timeline_minutes(entry.bedtime) - typical_bedtime_minutes)
        wake_difference = abs(time_to_minutes(entry.wake_time) - typical_wake_minutes)
        if bedtime_difference <= SLEEP_TIMING_WINDOW_MINUTES and wake_difference <= SLEEP_TIMING_WINDOW_MINUTES:
            consistent_entries.append(entry)
        else:
            variable_entries.append(entry)

    consistent_average = average_field(consistent_entries, "sleep_quality")
    variable_average = average_field(variable_entries, "sleep_quality")
    sleep_quality_difference = consistent_average - variable_average
    has_comparison = bool(consistent_entries and variable_entries)
    consistency_percent = clamp_percent((len(consistent_entries) / len(entries)) * 100)

    if has_comparison:
        if sleep_quality_difference > SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                f"Your more consistent sleep-timing days averaged {sleep_quality_difference:.1f} points higher for "
                "sleep quality than more variable days."
            )
        elif sleep_quality_difference < -SUMMARY_SIGNAL_THRESHOLD:
            summary = (
                "Your variable sleep-timing days are currently averaging higher sleep quality, so this pattern needs "
                "more entries before drawing a conclusion."
            )
        else:
            summary = (
                "Your sleep quality is currently similar across consistent and variable sleep-timing days."
            )
    else:
        summary = (
            "Log both consistent and more variable sleep-timing days to compare how routine links to sleep quality."
        )

    return {
        "has_comparison": has_comparison,
        "consistent_count": len(consistent_entries),
        "variable_count": len(variable_entries),
        "confidence_label": get_confidence_label(
            len(consistent_entries),
            len(variable_entries),
        ),
        "consistent_average": consistent_average,
        "variable_average": variable_average,
        "consistent_bar_percent": clamp_percent((consistent_average / 10) * 100),
        "variable_bar_percent": clamp_percent((variable_average / 10) * 100),
        "consistency_percent": consistency_percent,
        "typical_bedtime": format_minutes_as_time(typical_bedtime_minutes),
        "typical_wake_time": format_minutes_as_time(typical_wake_minutes),
        **target_time_labels,
        "sleep_quality_difference": sleep_quality_difference,
        "summary": summary,
        "research_context": (
            "Research suggests sleep regularity is an important predictor of health outcomes, with one cohort study "
            "finding it was a stronger predictor of mortality risk than sleep duration."
        ),
        "action_text": (
            "Maintaining a steadier sleep window could be a useful focus, especially when consistent days also show "
            "better sleep quality in your own data."
        ),
    }


def build_reflective_suggestion(
    sleep_duration_insight,
    sleep_quality_mood_energy_insight,
    sleep_timing_consistency_insight,
):
    suggestions = []

    if sleep_duration_insight["is_below_guideline"]:
        suggestions.append({
            "score": ADULT_SLEEP_MINIMUM_HOURS - sleep_duration_insight["average_duration"] + 1,
            "icon": "bedtime",
            "title": "Prioritise enough sleep",
            "body": (
                f"Your recent average is {sleep_duration_insight['average_duration']:.1f} hours, below the common "
                "adult guideline of 7 or more hours. Try protecting a slightly longer sleep window tonight."
            ),
        })

    if (
        sleep_timing_consistency_insight["has_comparison"]
        and sleep_timing_consistency_insight["sleep_quality_difference"] >= INSIGHT_SIGNAL_THRESHOLD
    ):
        suggestions.append({
            "score": sleep_timing_consistency_insight["sleep_quality_difference"],
            "icon": "routine",
            "title": "Protect your usual sleep window",
            "body": (
                f"Your consistent sleep-timing days are averaging "
                f"{sleep_timing_consistency_insight['sleep_quality_difference']:.1f} points higher for sleep quality. "
                "Try staying close to your usual bed and wake times for the next few entries."
            ),
        })

    if (
        sleep_quality_mood_energy_insight["has_comparison"]
        and sleep_quality_mood_energy_insight["wellbeing_difference"] >= INSIGHT_SIGNAL_THRESHOLD
    ):
        suggestions.append({
            "score": sleep_quality_mood_energy_insight["wellbeing_difference"],
            "icon": "bedtime",
            "title": "Prioritise sleep quality tonight",
            "body": (
                f"Your higher-quality sleep days are averaging "
                f"{sleep_quality_mood_energy_insight['wellbeing_difference']:.1f} points higher across mood and energy. "
                "Choose one small sleep-supporting habit tonight and log how tomorrow feels."
            ),
        })

    if suggestions:
        suggestion = max(suggestions, key=lambda item: item["score"])
        suggestion["action_label"] = "Log Today"
        return suggestion

    return {
        "icon": "tips_and_updates",
        "title": "Keep building your pattern",
        "body": (
            "Keep logging for a few more days so Sanctuary can make a more confident suggestion from your sleep, "
            "energy, and mood patterns."
        ),
        "action_label": "Log Today",
    }


def build_insights_context(user, user_profile):
    recent_entries = list(
        DailyEntry.objects.filter(user=user).order_by("-entry_date")[:RECENT_INSIGHT_LIMIT]
    )
    sleep_duration_insight = build_sleep_duration_insight(recent_entries)
    caffeine_sleep_insight = build_late_caffeine_sleep_insight(recent_entries, user_profile)
    screen_time_sleep_insight = build_screen_time_sleep_insight(recent_entries)
    exercise_energy_mood_insight = build_exercise_energy_mood_insight(recent_entries)
    sleep_quality_mood_energy_insight = build_sleep_quality_mood_energy_insight(recent_entries)
    sleep_timing_consistency_insight = build_sleep_timing_consistency_insight(recent_entries, user_profile)

    return {
        "sleep_duration_insight": sleep_duration_insight,
        "caffeine_sleep_insight": caffeine_sleep_insight,
        "screen_time_sleep_insight": screen_time_sleep_insight,
        "exercise_energy_mood_insight": exercise_energy_mood_insight,
        "sleep_quality_mood_energy_insight": sleep_quality_mood_energy_insight,
        "sleep_timing_consistency_insight": sleep_timing_consistency_insight,
        "reflective_suggestion": build_reflective_suggestion(
            sleep_duration_insight,
            sleep_quality_mood_energy_insight,
            sleep_timing_consistency_insight,
        ),
    }
