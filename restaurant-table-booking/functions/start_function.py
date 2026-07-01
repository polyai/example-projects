import datetime as dt
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import plog
from _gen import *  # <AUTO GENERATED>
from functions.opentable_api import get_restaurant_api
from functions.try_transfer_call import is_restaurant_ooh, try_transfer_call


def calculate_easter(year):
    # Meeus/Jones/Butcher Gregorian algorithm
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def get_nth_weekday(year, month, weekday, n):
    """Get the date of the nth weekday (0=Monday) in a given month"""
    count = 0
    for day in range(31):
        try:
            current = dt.date(year, month, day + 1)
        except ValueError:
            break
        if current.weekday() == weekday:
            count += 1
            if count == n:
                return current
    return None


def get_last_weekday(year, month, weekday):
    """Get the last weekday (0=Monday) in a given month"""
    last_day = (
        dt.date(year, month + 1, 1) - dt.timedelta(days=1) if month < 12 else dt.date(year, 12, 31)
    )
    while last_day.weekday() != weekday:
        last_day -= dt.timedelta(days=1)
    return last_day


def _ordinal_suffix(day: int) -> str:
    """Return ordinal suffix only: 'st', 'nd', 'rd', or 'th' (e.g. for 1→st, 2→nd)."""
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def get_named_dates(conv, country):
    today = dt.datetime.now(ZoneInfo(conv.variant.timezone)).date()
    year = today.year
    next_year = year + 1

    def include(d):
        return d >= today

    def fixed(m, d, y):
        return dt.date(y, m, d)

    def format(d, name):
        ordinal = f"{d.day}{_ordinal_suffix(d.day)}"
        iso_date = d.strftime("%Y-%m-%d")
        # ISO date first so the model uses it in function calls; human-readable for utterances
        entry = f"{iso_date} {name} ({ordinal} of {d.strftime('%B %Y')})"
        return f"[{entry}]"

    def holidays_for_country(y, country):
        easter = calculate_easter(y)
        good_friday = easter - dt.timedelta(days=2)
        easter_monday = easter + dt.timedelta(days=1)

        if country.lower() == "us":
            return [
                (fixed(1, 1, y), "New Year’s Day"),
                (get_nth_weekday(y, 1, 0, 3), "Martin Luther King Jr. Day"),
                (fixed(2, 14, y), "Valentine’s Day"),
                (get_nth_weekday(y, 2, 0, 3), "Presidents’ Day"),
                (fixed(3, 17, y), "St. Patrick’s Day"),
                (good_friday, "Good Friday"),
                (easter, "Easter Sunday"),
                (get_nth_weekday(y, 5, 6, 2), "Mother’s Day"),
                (get_last_weekday(y, 5, 0), "Memorial Day"),
                (fixed(6, 19, y), "Juneteenth"),
                (get_nth_weekday(y, 6, 6, 3), "Father’s Day"),
                (fixed(7, 4, y), "Independence Day"),
                (get_nth_weekday(y, 9, 0, 1), "Labor Day"),
                (get_nth_weekday(y, 10, 0, 2), "Columbus/Indigenous Peoples’ Day"),
                (fixed(10, 31, y), "Halloween"),
                (fixed(11, 11, y), "Veterans Day"),
                (get_nth_weekday(y, 11, 3, 4), "Thanksgiving"),
                (fixed(12, 24, y), "Christmas Eve"),
                (fixed(12, 25, y), "Christmas Day"),
                (fixed(12, 31, y), "New Year’s Eve"),
            ]

        elif country.lower() == "uk":
            mothers_day = easter - dt.timedelta(weeks=3)
            fathers_day = get_nth_weekday(y, 6, 6, 3)
            return [
                (good_friday, "Good Friday"),
                (easter, "Easter Sunday"),
                (easter_monday, "Easter Monday"),
                (mothers_day, "Mother’s Day"),
                (get_nth_weekday(y, 5, 0, 1), "Early May Bank Holiday"),
                (get_last_weekday(y, 5, 0), "Spring Bank Holiday"),
                (fathers_day, "Father’s Day"),
                (get_last_weekday(y, 8, 0), "Summer Bank Holiday"),
                (fixed(12, 25, y), "Christmas Day"),
                (fixed(12, 26, y), "Boxing Day"),
                (fixed(1, 1, y + 1), "New Year’s Day"),
            ]

        elif country.lower() in ["australia", "aus"]:
            anzac_day = fixed(4, 25, y)
            mothers_day = get_nth_weekday(y, 5, 6, 2)
            fathers_day = get_nth_weekday(y, 9, 6, 1)
            queens_birthday = get_nth_weekday(y, 6, 0, 2)
            return [
                (fixed(1, 1, y), "New Year’s Day"),
                (fixed(1, 26, y), "Australia Day"),
                (good_friday, "Good Friday"),
                (easter, "Easter Sunday"),
                (easter_monday, "Easter Monday"),
                (anzac_day, "ANZAC Day"),
                (mothers_day, "Mother’s Day"),
                (queens_birthday, "Queen’s Birthday"),
                (fathers_day, "Father’s Day"),
                (fixed(12, 25, y), "Christmas Day"),
                (fixed(12, 26, y), "Boxing Day"),
            ]

        elif country.lower() == "ie":
            mothers_day = easter - dt.timedelta(weeks=3)  # Same as UK Mother’s Day
            fathers_day = get_nth_weekday(y, 6, 6, 3)  # 3rd Sunday in June
            return [
                (fixed(1, 1, y), "New Year’s Day"),
                (fixed(2, 14, y), "Valentine’s Day"),
                (fixed(3, 17, y), "St Patrick’s Day"),
                (good_friday, "Good Friday"),
                (easter, "Easter Sunday"),
                (easter_monday, "Easter Monday"),
                (mothers_day, "Mother’s Day"),
                (
                    get_nth_weekday(y, 5, 0, 1),
                    "May Day Bank Holiday",
                ),  # First Monday in May
                (
                    get_nth_weekday(y, 6, 0, 1),
                    "June Bank Holiday",
                ),  # First Monday in June
                (fathers_day, "Father’s Day"),
                (
                    get_nth_weekday(y, 8, 0, 1),
                    "August Bank Holiday",
                ),  # First Monday in August
                (fixed(10, 31, y), "Halloween"),
                (
                    get_last_weekday(y, 10, 0),
                    "October Bank Holiday",
                ),  # Last Monday in October
                (fixed(12, 24, y), "Christmas Eve"),
                (fixed(12, 25, y), "Christmas Day"),
                (fixed(12, 26, y), "St Stephen’s Day"),
                (fixed(12, 31, y), "New Year’s Eve"),
            ]

        else:
            raise ValueError(f"Unsupported country: {country}")

    # Aggregate holidays for both years, sort by date (chronological), then format
    holidays = []
    for y in [year, next_year]:
        holidays += holidays_for_country(y, country)

    holidays = [(d, name) for d, name in holidays if include(d)]
    holidays.sort(key=lambda x: x[0])
    return ", ".join(format(d, name) for d, name in holidays)


def set_datetime(conv: Conversation):
    now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    conv.state.now = now.isoformat()
    conv.state.current_date = now.strftime("%A %d-%m-%Y")
    conv.state.current_weekday = now.strftime("%A")
    conv.state.current_time = now.strftime("%H:%M")
    conv.state.formatted_date_time = now.strftime("%A, %B %d, %Y at %I:%M %p")


def ordinal_suffix(day):
    """Return full ordinal string for a day (e.g. 1st, 2nd, 21st)."""
    return f"{day}{_ordinal_suffix(day)}"


def parse_special_dates(site):
    """
    Parse special dates from site data into a dictionary for easy lookup by date.

    Returns:
        Dict[str, dict] -> { "2025-09-24": {"hours": "17:00-00:00", "reason": "...", "greeting_message": "..."} }
    """
    special_dates_list = site.get("01_opening_hours", {}).get("08_special_dates", [])
    special_dates_dict = {}

    for item in special_dates_list:
        date_str = item.get("date")
        if date_str:
            # copy all relevant info except "date"
            info = {k: v for k, v in item.items() if k != "date"}
            special_dates_dict[date_str] = info

    return special_dates_dict


def parse_hours_from_text(hours_text):
    """
    Parse a string of opening hours into a dictionary mapping weekday → hours string.

    Example input:
    '''
    Monday: closed
    Tuesday: 11:00-22:00
    Wednesday: 11:00-22:00
    Thursday: 11:00-22:00
    Friday: 11:00-00:00
    Saturday: 11:00-22:00
    Sunday: 11:00-22:00
    '''

    Output:
    {
        "Monday": "closed",
        "Tuesday": "11:00-22:00",
        "Wednesday": "11:00-22:00",
        "Thursday": "11:00-22:00",
        "Friday": "11:00-00:00",
        "Saturday": "11:00-22:00",
        "Sunday": "11:00-22:00",
    }
    """
    hours_dict = {}
    for line in hours_text.strip().splitlines():
        if not line.strip():
            continue
        try:
            day, hours = line.split(":", 1)
            hours_dict[day.strip()] = hours.strip()
        except ValueError:
            # Skip malformed lines
            continue
    # NOTE: settings this default for now - might want to remove later
    if not hours_dict:
        hours_dict = {
            "Monday": "closed",
            "Tuesday": "11:00-22:00",
            "Wednesday": "11:00-22:00",
            "Thursday": "11:00-22:00",
            "Friday": "11:00-00:00",
            "Saturday": "11:00-22:00",
            "Sunday": "11:00-22:00",
        }
    return hours_dict


def parse_hours(site, type_of_hours):
    """
    Parse opening hours into a dictionary mapping weekday → hours string.

    site: Real Time config data for the site
    type_of_hours: Type of hours to return. Can be 'kitchen', 'bar', or 'staffed'.
    """
    opening_hours = site.get("01_opening_hours", {})

    weekdays_map = {
        "01_monday": "Monday",
        "02_tuesday": "Tuesday",
        "03_wednesday": "Wednesday",
        "04_thursday": "Thursday",
        "05_friday": "Friday",
        "06_saturday": "Saturday",
        "07_sunday": "Sunday",
    }

    hours_dict = {}
    for day_key, weekday in weekdays_map.items():
        day_info = opening_hours.get(day_key, {})
        hours = day_info.get(type_of_hours)
        if hours:
            hours_dict[weekday] = hours

    return hours_dict


def load_site_real_time_config(conv):
    """Load site configuration into the conversation state, including opening hours and special dates."""

    config = conv.real_time_config
    site_hours = config.get("site_hours", [])

    for site in site_hours:
        if site.get("00_name", "") == conv.variant_name:
            conv.state.site_opening_hours = parse_hours(site, "opening")
            plog.info(f"Opening Hours: {conv.state.site_opening_hours}")
            if config.get("show_bar_hours"):
                conv.state.site_bar_hours = parse_hours(site, "bar")
            if config.get("show_kitchen_hours"):
                conv.state.site_kitchen_hours = parse_hours(site, "kitchen")
            if config.get("show_staffed_hours"):
                conv.state.site_staffed_hours = parse_hours(site, "staffed")

            # Save all special dates for later checks
            conv.state.special_dates = parse_special_dates(site)
            plog.info(f"Special dates: {conv.state.special_dates}")
            return

    # If RTC does not contain site_hour, fallback to variant attribute
    if conv.variant.opening_hours:
        conv.state.site_opening_hours = parse_hours_from_text(conv.variant.opening_hours)
        conv.state.special_dates = {}
        plog.info(f"Opening Hours: {conv.state.site_opening_hours} from variant attributes")
        return

    raise ValueError(f"Real-time config not found for site '{conv.variant_name}'")


def walk_in_only(conv):
    # if we don't have RID (if RID is not numeric), disable bookings
    return not conv.variant.rid.strip().isdigit()


def get_disambiguations(conv: Conversation):
    """Check if dismabigaution needed"""
    disamb_list: list = conv.real_time_config.get("disambiguation", [])
    disamb_dict = {}
    # Convert list to dictionary for faster lookups
    for site in disamb_list:
        disamb_dict[site.get("dnis", "")] = {
            "site_names": site["site_names"],
            "disambiguation_utterance": site["disambiguation_utterance"],
        }

    return disamb_dict


def start_function(conv: Conversation):
    try:
        ZoneInfo(conv.variant.timezone)
    except ZoneInfoNotFoundError:
        conv.variant.timezone = "America/New_York"
        # Use a default timezone if no valid one was set
        conv.log.warning(
            "Using default timezone because the variant attribute is not valid.",
            timezone=conv.variant.timezone,
        )

    conv.state.special_date_greeting_message = ""

    # save delay utterance for start_check_availability function
    conv.state.start_checking_availability_delay_utterance = (
        "Let me just check what space we have..."
    )

    # SET UP FEATURE FLAGS
    conv.state.include_experiences = conv.real_time_config.get("experiences_enabled", True)
    conv.state.table_type_selection_enabled = True

    # Disable bookings for walk-ins only restaurant
    conv.state.disable_booking = walk_in_only(conv)

    # Always return a string for GPT to process or your function will not work
    conv.state.user_bookings = None
    conv.state.available_times = None
    conv.state.phone_number = None
    conv.state.check_if_date_exists_delay_utterance = "Just a second."

    set_datetime(conv)
    conv.state.named_days = get_named_dates(conv, "us")

    # Set opening/kitchen/bar/staffed hours
    load_site_real_time_config(conv)

    # Save special date info for today
    today_str = conv.state.now
    conv.state.special_date_greeting_message = ""
    if special_date := conv.state.special_dates.get(today_str):
        # save greeting message for special date
        conv.state.special_date_greeting_message = special_date.get("greeting_message") or ""

    if conv.caller_number:
        conv.state.phone_number = conv.caller_number
    from_header = conv.sip_headers.get("From", "")
    match = re.search("sip:(.+?)@", from_header)
    if match:
        conv.state.phone_number = match.group(1)

    conv.write_metric("RESTAURANT_ID", conv.variant.rid, write_once=True)
    conv.write_metric("RESTAURANT_NAME", conv.variant_name, write_once=True)

    now = dt.datetime.fromisoformat(conv.state.now)
    conv.state.next_few_days = "\n".join(
        [
            (now + dt.timedelta(days=i)).strftime(
                f"- %A {ordinal_suffix((now + dt.timedelta(days=i)).day)} of %B %Y"
            )
            for i in range(1, 14)
        ]
    )

    now = dt.datetime.now(ZoneInfo(conv.variant.timezone))
    if is_restaurant_ooh(conv, now):
        conv.write_metric("OOH", write_once=True)

    if conv.state.include_experiences:
        try:
            get_active_experiences(conv)
        except Exception as e:
            plog.exception("Error getting OT experiences", exc=e)
            if conv.env == "live":
                return try_transfer_call(
                    conv,
                    "api_get_active_experiences_error",
                    "Something went wrong. Let me put you thorugh someone who can help.",
                    "FORCE_STANDARD_HANDOFF",
                )
            else:
                conv.state.include_experiences = False
    if not conv.state.include_experiences:
        conv.state.formatted_experiences = ""


@plog.tmp_bind(api_integration="opentable")
def get_active_experiences(conv: Conversation):
    api = get_restaurant_api(conv)
    # Mock API doesn't support experiences — short-circuit
    if hasattr(api, "check_availability"):
        conv.state.active_experiences = {}
        conv.state.formatted_experiences = ""
        return

    endpoint = f"booking/experiences/{conv.variant.rid}"
    res = api(conv, method="GET", endpoint=endpoint, data={}, params={})
    res.raise_for_status()
    response = res.json()
    plog.info("Get active experiences response", response=response)
    # no active experiences -> returns empty object, otherwise it has "data"
    conv.state.active_experiences = {}
    if response:
        for experience in response["data"]:
            conv.state.active_experiences[experience["experience_id"]] = experience
            conv.state.active_experiences[experience["experience_id"]]["formatted"] = (
                format_experience(experience)
            )
    conv.state.formatted_experiences = "\n\n".join(
        [experience["formatted"] for experience in conv.state.active_experiences.values()]
    )


def format_experience(experience: dict):
    text = ""
    name = experience["name"]
    text += f"*Name*: {name}"
    experience_id = experience["experience_id"]
    bookable = experience["bookable"]
    if bookable:
        text += f"\n*Experience id*: {experience_id}"
    else:
        text += "\n*Experience id*: None - this offer doesn't need a specific booking. It should be booked as a standard booking instead of specifying experience id."
    description = experience["description"]
    text += f"\n*Description*: {description}"

    if "price_info" in experience:
        text += "\n*Prices:*\n"
        price_info = experience["price_info"]
        text += format_prices(price_info)
    plog.info("formatted experience", text=text)
    # TODO: Gratuity info formatting (if needed)
    return text


def format_prices(price_info):
    text = ""
    price_type = price_info["price_type"].lower().replace("_", " ")
    pre_payment_required = price_info["prepayment_required"]
    if pre_payment_required:
        text += "All options require pre-payment via a link received after booking.\n"
    else:
        text += "All options are payable at the restaurant and don't require a pre-payment after booking.\n"
    currency_code = price_info["currency_code"]
    multiplier = price_info["multiplier"]
    prices = []
    for price in price_info["prices"]:
        currency_names = {
            "USD": "dollars",
            "CAD": "dollars",
            "AUD": "dollars",
            "GBP": "pounds",
        }
        all_inclusive = price.get("price_all_inclusive", False)
        amount = price["min_unit_amount"] / multiplier
        # Check if the amount is a whole number
        if amount.is_integer():
            amount_str = f"{int(amount)}"
        else:
            decimals = int(math.log10(multiplier))
            amount_str = f"{amount:.{decimals}f}"
        friendly_currency = currency_names.get(currency_code, currency_code)
        formatted_price = f"{amount_str} {friendly_currency} {price_type}"
        if all_inclusive:
            formatted_price += " all inclusive"
        if title := price.get("price_title"):
            formatted_price = f"*{title}*: {formatted_price}"
        # make into a list
        formatted_price = f"- {formatted_price}"
        prices.append(formatted_price)
    text += "\n".join(prices)
    return text
