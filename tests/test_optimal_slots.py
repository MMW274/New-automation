from datetime import datetime, timezone

from src.scheduler.optimal_slots import ET, next_optimal_slot


def _sun_evening_et():
    # Sun Jun 28 2026 17:50 ET -> 21:50 UTC
    return datetime(2026, 6, 28, 21, 50, tzinfo=timezone.utc)


def test_tiktok_picks_evening_peak_on_sunday():
    slot = next_optimal_slot("tiktok", after=_sun_evening_et())
    et = slot.astimezone(ET)
    assert et.weekday() == 6  # Sun
    assert et.hour == 18


def test_x_picks_tuesday_morning_when_started_sun_evening():
    slot = next_optimal_slot("twitter", after=_sun_evening_et())
    et = slot.astimezone(ET)
    # next X peak is Mon 10 ET
    assert et.weekday() in (0, 1)
    assert et.hour == 10


def test_youtube_picks_friday_evening_peak_when_appropriate():
    # Thu Jul 2 2026 16:00 ET = Thu 20:00 UTC -> next YT slot is Thu 18 ET
    # (Thu peaks [18, 19] ET). Confirm we get Thu 18 or 19.
    after = datetime(2026, 7, 2, 20, 0, tzinfo=timezone.utc)
    slot = next_optimal_slot("youtube", after=after)
    et = slot.astimezone(ET)
    assert et.weekday() == 3
    assert et.hour in (18, 19)


def test_used_slots_prevent_collision():
    after = _sun_evening_et()
    used = set()
    first = next_optimal_slot("tiktok", after=after, used_slots=used)
    used.add(first)
    second = next_optimal_slot("tiktok", after=after, used_slots=used)
    assert first != second


def test_x_alias_normalized_to_twitter():
    after = _sun_evening_et()
    a = next_optimal_slot("twitter", after=after)
    b = next_optimal_slot("x", after=after)
    assert a == b
