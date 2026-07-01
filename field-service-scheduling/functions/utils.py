import calendar
from datetime import date, datetime, timedelta
from itertools import groupby
from typing import Optional
from zoneinfo import ZoneInfo

from _gen import *  # <AUTO GENERATED>

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _fmt_time(t: str) -> str:
    h, m = map(int, t.split(":"))
    period = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"


def _fmt_hours(hours: str) -> str:
    start, end = hours.split("-")
    return f"{_fmt_time(start)} to {_fmt_time(end)}"


def _fmt_day_range(days: list[str]) -> str:
    if len(days) == 1:
        return days[0].capitalize()
    return f"{days[0].capitalize()} through {days[-1].capitalize()}"


def opening_hours_utterance(opening_hours: dict) -> str:
    """Convert an opening_hours config dict into a spoken utterance.

    Expects a dict mapping day names to "HH:MM-HH:MM" strings (or "closed").
    Consecutive days with the same hours are grouped into ranges. Closed days
    break a range so that e.g. Mon+Wed open with Tue closed won't produce
    "Monday through Wednesday".

    Example: {"monday": "07:00-19:00", "tuesday": "07:00-19:00", "saturday": "07:00-16:00"}
    -> "We're available Monday through Tuesday 7am to 7pm, and Saturday 7am to 4pm central time."

    Returns empty string when no opening hours are configured.
    """
    daily = {k: v for k, v in opening_hours.items() if isinstance(v, str)}

    # Build schedule including closed days so groupby breaks on them
    schedule = [(d, daily.get(d, "closed")) for d in DAYS]

    groups = []
    for hours, items in groupby(schedule, key=lambda x: x[1]):
        if hours.strip().lower() == "closed":
            continue
        days = [d for d, _ in items]
        groups.append((days, hours))

    if not groups:
        return ""

    parts = [f"{_fmt_day_range(days)} {_fmt_hours(hours)}" for days, hours in groups]

    if len(parts) == 1:
        return f"We're available {parts[0]} central time."
    if len(parts) == 2:
        return f"We're available {parts[0]}, and {parts[1]} central time."
    return f"We're available {', '.join(parts[:-1])}, and {parts[-1]} central time."


def get_prompt_for_appointment_timeframe_readback(appointment: dict, call_intent: str) -> str:
    start = remove_seconds(appointment["start"])
    end = remove_seconds(appointment["end"])

    prompt = ""

    if start == "08:00" and end == "20:00":  # AT
        prompt += "(don't say anything about service time unless asked, as service time is between 8am and sunset)"
    elif start == "08:00" and end == "13:00":  # AM
        prompt += " - the field expert is currently scheduled to arrive at your property in the morning to early afternoon, between 8am and 1pm"
    elif start == "13:00" and end == "20:00":  # PM
        prompt += " - the field expert is currently scheduled to arrive at your property in the afternoon to early evening, between 1pm and sunset"
    else:  # Timed
        prompt += f" - the field expert is currently scheduled to arrive at your property between {start} and {end}"

    prompt += get_prompt_for_interior_vs_exterior_readback(appointment["doInterior"] == "2")

    if call_intent == "reschedule":
        prompt += " - shall we go ahead with finding a new time for your appointment?"
    elif call_intent == "cancel":
        prompt += " - is that the appointment you wanted to cancel?"
    else:
        prompt += " - is that all okay?"

    return prompt


def get_prompt_for_interior_vs_exterior_readback(interior_needed: bool) -> str:
    if interior_needed:
        return " - since this includes indoor work, someone will need to be home to let the technician in"
    else:
        return ""


def get_prompt_for_new_appointment_timeframe_readback(start: str, end: str) -> str:
    prompt = ""

    if start == "08:00" and end == "20:00":  # AT
        prompt += "(don't say anything about service time unless asked, as service time is between 8am and sunset)"
    elif start == "08:00" and end == "13:00":  # AM
        prompt += " - in the morning to early afternoon, between 8am and 1pm"
    elif start == "13:00" and end == "20:00":  # PM
        prompt += " - in the afternoon to early evening, between 1pm and sunset"
    else:  # Timed
        prompt += f" - between {start} and {end}"

    return prompt


def get_start_and_end_date_for_search(requested_date: str, current_date: str) -> dict:
    """
    Given a requested_date and a current_date (both in "YYYY-MM-DD" format),
    this function returns a dictionary with "start_date" and "end_date" where:

      - start_date is no earlier than current_date + 1 day.
      - The ideal start_date is requested_date - 7 days.
      - The actual start_date is the later of the two dates above.
      - The end_date is exactly 14 days after the chosen start_date.
    """
    date_format = "%Y-%m-%d"
    requested_dt = datetime.strptime(requested_date, date_format).date()
    current_dt = datetime.strptime(current_date, date_format).date()

    # current_date + 1 day is the minimum allowed start date.
    min_start = current_dt + timedelta(days=1)

    # Ideally, we want the start_date to be 7 days before the requested_date.
    ideal_start = requested_dt - timedelta(days=7)

    # Choose the later date to ensure start_date is valid.
    chosen_start = max(ideal_start, min_start)

    # The range is exactly 14 days, so end_date is 14 days after start_date.
    end_date = chosen_start + timedelta(days=14)

    return {
        "start_date": chosen_start.strftime(date_format),
        "end_date": end_date.strftime(date_format),
    }


def increment_date_by_one(date_str: str) -> str:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    next_day = date_obj + timedelta(days=1)
    return next_day.isoformat()


def is_within_duration(start_time_str: str, check_time_str: str, duration_minutes: str) -> bool:
    """
    Check if the check_time is within duration_minutes after start_time.
    Both times are in "HH:MM" format.
    """
    time_format = "%H:%M"
    start_time = datetime.strptime(start_time_str, time_format)
    check_time = datetime.strptime(check_time_str, time_format)
    duration = timedelta(minutes=int(duration_minutes))
    return start_time < check_time < start_time + duration


def get_time_window_type(start_time_str: str, end_time_str: str) -> str:
    if start_time_str == "08:00" and end_time_str == "20:00":
        return "AT"
    elif start_time_str == "08:00" and end_time_str == "13:00":
        return "AM"
    elif start_time_str == "13:00" and end_time_str == "20:00":
        return "PM"
    else:
        return "Timed"


def choose_best_route(candidates, current_date_str, alpha=0.6):
    """
    candidates: list of dicts, using following keys:
        - averageDistance (float, miles)
        - date (string in "YYYY-MM-DD" format)
    current_date_str: string, e.g. "2025-06-12"
    alpha: weight for temporal proximity (0 to 1). The rest is distance. Closer to 0 means more priority for distance.

    Returns: the best candidate dict
    """
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")

    # Extract values
    days_from_now = [
        (datetime.strptime(c["date"], "%Y-%m-%d") - current_date).days for c in candidates
    ]
    distances = [c["averageDistance"] for c in candidates]

    min_days, max_days = min(days_from_now), max(days_from_now)
    min_dist, max_dist = min(distances), max(distances)

    def normalise(val, min_val, max_val):
        return (val - min_val) / (max_val - min_val) if max_val != min_val else 0.5

    best_score = float("inf")
    best_candidate = None

    for candidate, days in zip(candidates, days_from_now, strict=False):
        norm_days = normalise(days, min_days, max_days)
        norm_dist = normalise(candidate["averageDistance"], min_dist, max_dist)

        score = alpha * norm_days + (1 - alpha) * norm_dist

        if score < best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate


def get_potential_slot(
    conv: Conversation,
    spots: list[dict],
    routes: list[dict],
    appointments: list[dict],
    duration: str,
    max_distance_to_previous_spot_in_miles: int,
    max_distance_to_closest_spot_in_miles: int,
    service_type_id_for_warranty_reservice: str,
    current_date: str,
    requested_date: Optional[str],  # expected format "YYYY-MM-DD"
    requested_start_time: Optional[str],  # expected format "HH:MM"
    requested_end_time: Optional[str],  # expected format "HH:MM"
    existing_appointment_date: Optional[str] = "",  # expected format "YYYY-MM-DD"
) -> Optional[dict]:
    """
    TODO
    """
    conv.log.info(
        "get_potential_slot args",
        duration=duration,
        max_distance_to_previous_spot_in_miles=max_distance_to_previous_spot_in_miles,
        max_distance_to_closest_spot_in_miles=max_distance_to_closest_spot_in_miles,
        service_type_id_for_warranty_reservice=service_type_id_for_warranty_reservice,
        current_date=current_date,
        requested_date=requested_date,
        requested_start_time=requested_start_time,
        requested_end_time=requested_end_time,
        existing_appointment_date=existing_appointment_date,
    )

    # Sort routes by average distance to customer
    routes = sorted(
        routes,
        key=lambda r: float(r["averageDistance"]) if r.get("averageDistance") is not None else 0,
    )

    spot_candidates = []

    for route in routes:
        if (
            requested_date
            and requested_date != existing_appointment_date
            and existing_appointment_date == route["date"]
        ):
            continue  # https://poly-ai.atlassian.net/browse/UTIL-2505

        route_spots = []
        free_route_spots = []
        for spot in spots:
            if route["routeID"] == spot["routeID"]:
                route_spots.append(spot)
                if spot["open"] != "1":
                    continue
                free_route_spots.append(spot)

        route_appointments = []
        warranty_reservice_appointment_count = 0
        timed_appointment_count = 0  # timed appointments are all appointments that don't start exactly at 8am and end exactly at 8pm aka "anytime" or "AT" appointments
        for appointment in appointments:
            if route["routeID"] == appointment["routeID"]:
                route_appointments.append(appointment)

                start = remove_seconds(appointment["start"])
                end = remove_seconds(appointment["end"])
                if not (start == "08:00" and end == "20:00"):
                    timed_appointment_count += 1

                if appointment["type"] == service_type_id_for_warranty_reservice:
                    warranty_reservice_appointment_count += 1

        has_enough_free_spots = sum(
            [int(spot["spotCapacity"]) + 1 for spot in free_route_spots]
        ) >= int(duration)

        if (
            has_enough_free_spots
            and len(route_appointments) < 18
            and warranty_reservice_appointment_count < 7
        ):
            distance_to_closest_spot = max_distance_to_closest_spot_in_miles
            has_overlap_with_another_timed_appointment = False
            too_far_from_previous_timed_appointment = False

            requested_time_window_type = ""
            if requested_start_time and requested_end_time:
                requested_time_window_type = get_time_window_type(
                    requested_start_time, requested_end_time
                )

            am_appointments = 0
            pm_appointments = 0
            for spot in route_spots:
                spot_appointment: dict = next(
                    (
                        appt
                        for appt in route_appointments
                        if spot.get("currentAppointment") == appt["appointmentID"]
                    ),
                    {},
                )
                if not spot_appointment:
                    continue

                distance_to_previous = float(spot["distanceToPrevious"])

                start = remove_seconds(spot_appointment["start"])
                end = remove_seconds(spot_appointment["end"])
                if start == "08:00" and end == "20:00":  # AT
                    pass
                elif start == "08:00" and end == "13:00":  # AM
                    am_appointments += 1
                elif start == "13:00" and end == "20:00":  # PM
                    pm_appointments += 1
                elif (requested_start_time and requested_end_time) and get_time_window_type(
                    start, end
                ) == "Timed":  # Timed
                    if time_ranges_overlap(start, end, requested_start_time, requested_end_time):
                        has_overlap_with_another_timed_appointment = True

                    if (
                        is_within_duration(end, requested_start_time, "1")
                        and distance_to_previous > max_distance_to_previous_spot_in_miles
                    ):
                        too_far_from_previous_timed_appointment = True

                if distance_to_previous < distance_to_closest_spot:
                    distance_to_closest_spot = distance_to_previous

            has_potential_time_conflict = (
                (requested_time_window_type == "AM" and am_appointments > 1)
                or (requested_time_window_type == "PM" and pm_appointments > 2)
                or (
                    requested_time_window_type == "Timed"
                    and has_overlap_with_another_timed_appointment
                )
            )

            if (
                (
                    (requested_start_time and requested_end_time)
                    and (
                        too_far_from_previous_timed_appointment
                        or has_potential_time_conflict
                        or timed_appointment_count >= 7
                    )
                )
                or (
                    distance_to_closest_spot
                    == max_distance_to_closest_spot_in_miles  # ie that there are no spots closer than the max distance
                )
                or (float(route["averageDistance"]) > 20)
            ):
                continue

            candidate = {
                "spotID": free_route_spots[0]["spotID"],
                "routeID": route["routeID"],
                "averageDistance": float(route["averageDistance"]),
                "distanceToClosestSpot": distance_to_closest_spot,
                "date": route["date"],
                "day_of_week": datetime.strptime(route["date"], "%Y-%m-%d").strftime("%A"),
            }

            if requested_start_time:
                candidate["start"] = requested_start_time

            if requested_end_time:
                candidate["end"] = requested_end_time

            spot_candidates.append(candidate)

    conv.log.info("spot candidates", spot_candidates=spot_candidates)

    if not spot_candidates:
        return None

    # If no requested date, return spot on "best" route, weighted by average distance and soon-ness
    if not requested_date:
        return choose_best_route(spot_candidates, current_date)

    # Convert the requested date into a date object.
    requested_dt = datetime.strptime(requested_date, "%Y-%m-%d")
    requested_date_obj = requested_dt.date()

    # Group the candidate spots by date.
    grouped_spot_candidates: dict[date, list[dict]] = {}
    for candidate in spot_candidates:
        d = datetime.strptime(candidate["date"], "%Y-%m-%d").date()
        grouped_spot_candidates.setdefault(d, []).append(candidate)

    # 1. Try the requested day first.
    if requested_date_obj in grouped_spot_candidates:
        spot_candidates_on_date = grouped_spot_candidates[requested_date_obj]
        if len(spot_candidates_on_date) > 0:
            candidate = spot_candidates_on_date[0]
            return candidate

    # 2. Then check earlier days in descending order.
    earlier_dates = sorted(
        [d for d in grouped_spot_candidates.keys() if d < requested_date_obj], reverse=True
    )
    for d in earlier_dates:
        spot_candidates_on_date = grouped_spot_candidates[d]
        if len(spot_candidates_on_date) > 0:
            candidate = spot_candidates_on_date[0]
            return candidate

    # 3. Finally, check future days in ascending order.
    later_dates = sorted([d for d in grouped_spot_candidates.keys() if d > requested_date_obj])
    for d in later_dates:
        spot_candidates_on_date = grouped_spot_candidates[d]
        if len(spot_candidates_on_date) > 0:
            candidate = spot_candidates_on_date[0]
            return candidate

    return None


def remove_seconds(time_str: str) -> str:
    t = datetime.strptime(time_str, "%H:%M:%S").time()
    return t.strftime("%H:%M")


def time_ranges_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    fmt = "%H:%M"
    s1 = datetime.strptime(start1, fmt)
    e1 = datetime.strptime(end1, fmt)
    s2 = datetime.strptime(start2, fmt)
    e2 = datetime.strptime(end2, fmt)

    # No overlap if one ends before or exactly when the other starts
    return not (e1 <= s2 or e2 <= s1)


def dates_in_same_month(date1_str: str, date2_str: str) -> bool:
    date_format = "%Y-%m-%d"
    date1 = datetime.strptime(date1_str, date_format)
    date2 = datetime.strptime(date2_str, date_format)

    return date1.year == date2.year and date1.month == date2.month


def is_within_days(date1_str: str, date2_str: str, days: int) -> bool:
    """
    Return True if date1 and date2 are less than `days` days apart

    - date1_str, date2_str: dates as strings in the given format.
    - days: threshold (strictly less than).
    - date_format: format of the input strings (default "%Y-%m-%d").
    """
    date_format = "%Y-%m-%d"
    d1 = datetime.strptime(date1_str, date_format).date()
    d2 = datetime.strptime(date2_str, date_format).date()

    return abs((d2 - d1).days) < days


def get_most_recent_date(date_list: list[str]) -> Optional[str]:
    if not date_list:
        return None
    return max(date_list, key=lambda d: datetime.strptime(d, "%Y-%m-%d"))


def is_more_than_months_ago(date_str: str, current_date_str: str, months: int) -> bool:
    """
    Return True if date_str is more than `months` calendar months before current_date_str.
    """
    date_format = "%Y-%m-%d"
    d = datetime.strptime(date_str, date_format).date()
    current = datetime.strptime(current_date_str, date_format).date()

    threshold_month = current.month - months
    threshold_year = current.year
    while threshold_month <= 0:
        threshold_month += 12
        threshold_year -= 1

    max_day = calendar.monthrange(threshold_year, threshold_month)[1]
    threshold = current.replace(
        year=threshold_year, month=threshold_month, day=min(current.day, max_day)
    )
    return d < threshold


# Defaulting for EST
def format_to_timezone(utc_time_str, time_zone_str) -> str:
    utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
    # Convert to target timezone
    local_time = utc_time.astimezone(ZoneInfo(time_zone_str))
    base_time = local_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    offset = local_time.strftime("%z")
    # Insert colon in timezone offset
    formatted_offset = f"{offset[:3]}:{offset[3:]}"
    return f"{base_time}{formatted_offset}"


def convert_timestamp_to_est_timezone(utc_iso_timestamp: str):
    utc_datetime = datetime.fromisoformat(utc_iso_timestamp)
    target_timezone = ZoneInfo("America/New_York")
    converted_datetime = utc_datetime.astimezone(target_timezone)
    return converted_datetime.strftime("%Y-%m-%d %H:%M:%S")


@func_description("utils")
def utils(conv: Conversation):
    # Add your function definition here.
    # You can optionally return a string that will be fed back to the LLM.
    pass
