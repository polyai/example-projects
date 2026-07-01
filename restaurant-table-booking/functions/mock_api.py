"""In-memory mock of the OpenTable API for demo / testing without a live backend."""

import uuid
from datetime import datetime, timedelta

import plog
from _gen import *  # <AUTO GENERATED>


class MockOpenTableApi:
    """Deterministic in-memory restaurant API that mirrors the real OpenTable
    endpoints used by this agent.  Mutations (lock, finalize, cancel, modify)
    update shared class-level state so changes persist across calls within a
    single conversation."""

    # ── Class-level seed data (shared across instances) ────────────────────

    _last_conv_id: str | None = None
    _slots: dict[str, list[str]] = {}
    _bookings: dict[str, dict] = {}
    _guests: dict[str, dict] = {}
    _pending_locks: dict[str, dict] = {}

    def __init__(self, conv=None):
        self.conv = conv
        # Re-seed when a new conversation starts so state doesn't leak
        # across calls via warm Lambda containers.
        conv_id = getattr(conv, "id", None)
        if conv_id != MockOpenTableApi._last_conv_id:
            self._seed()
            MockOpenTableApi._last_conv_id = conv_id

    # ── Seed helpers ──────────────────────────────────────────────────────

    @classmethod
    def _seed(cls):
        now = datetime.now()
        tomorrow = (now + timedelta(days=1)).date()
        day_after = (now + timedelta(days=2)).date()
        three_days = (now + timedelta(days=3)).date()

        def _dt(date, hour, minute=0):
            return datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))

        cls._slots = {
            tomorrow.isoformat(): [
                _dt(tomorrow, 12, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(tomorrow, 13, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(tomorrow, 18, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(tomorrow, 19, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(tomorrow, 20, 0).strftime("%Y-%m-%dT%H:%M"),
            ],
            day_after.isoformat(): [
                _dt(day_after, 12, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(day_after, 13, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(day_after, 18, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(day_after, 19, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(day_after, 20, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(day_after, 20, 30).strftime("%Y-%m-%dT%H:%M"),
            ],
            three_days.isoformat(): [
                _dt(three_days, 12, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(three_days, 18, 0).strftime("%Y-%m-%dT%H:%M"),
                _dt(three_days, 19, 0).strftime("%Y-%m-%dT%H:%M"),
            ],
        }

        # Pre-seeded bookings
        booking_1_id = "mock-booking-001"
        booking_1_dt = _dt(tomorrow, 19, 0).strftime("%Y-%m-%dT%H:%M")
        cls._bookings[booking_1_id] = {
            "reservation_id": booking_1_id,
            "first_name": "John",
            "last_name": "Smith",
            "party_size": 4,
            "date_time": booking_1_dt,
            "phone": {"number": "5550001234", "country_code": 1},
            "special_request": "",
        }

        booking_2_id = "mock-booking-002"
        booking_2_dt = _dt(day_after, 20, 0).strftime("%Y-%m-%dT%H:%M")
        cls._bookings[booking_2_id] = {
            "reservation_id": booking_2_id,
            "first_name": "Jane",
            "last_name": "Doe",
            "party_size": 2,
            "date_time": booking_2_dt,
            "phone": {"number": "5550005678", "country_code": 1},
            "special_request": "",
        }

        cls._guests = {
            "5550001234": {
                "firstName": "John",
                "lastName": "Smith",
                "phone": "5550001234",
            },
            "5550005678": {
                "firstName": "Jane",
                "lastName": "Doe",
                "phone": "5550005678",
            },
        }

    # ── Public API (mirrors OpenTableApiWrapper) ──────────────────────────

    def check_availability(
        self,
        party_size,
        date_time,
        forward_minutes=120,
        backward_minutes=0,
        include_experiences=False,
    ):
        """Return a response dict matching the shape of the real availability
        endpoint.  Filters pre-seeded slots by the requested time window."""
        try:
            requested_dt = datetime.strptime(date_time, "%Y-%m-%dT%H:%M")
        except ValueError:
            return _error_response(400, "InvalidDateTime")

        date_key = requested_dt.date().isoformat()
        all_slots = self._slots.get(date_key, [])

        window_start = requested_dt - timedelta(minutes=backward_minutes)
        window_end = requested_dt + timedelta(minutes=forward_minutes)

        matched = []
        for slot_str in all_slots:
            slot_dt = datetime.strptime(slot_str, "%Y-%m-%dT%H:%M")
            if window_start <= slot_dt <= window_end:
                matched.append(slot_str)

        times_available = []
        for t in matched:
            times_available.append(
                {
                    "time": t,
                    "availability_types": [
                        {
                            "type": "Standard",
                            "diningArea": [{"table_type": ["default"]}],
                            "cancellationPolicy": {"type": "None"},
                        }
                    ],
                }
            )

        plog.info(
            "MockOpenTableApi.check_availability",
            party_size=party_size,
            date_time=date_time,
            matched=len(matched),
        )

        return _ok_response(
            {
                "times": matched,
                "times_available": times_available,
            }
        )

    def lock_booking(
        self,
        party_size,
        date_time,
        table_type="default",
        experience_id=None,
    ):
        """Create a temporary lock and return a reservation token."""
        token = f"mock-token-{uuid.uuid4().hex[:8]}"
        self._pending_locks[token] = {
            "party_size": int(party_size),
            "date_time": date_time,
            "table_type": table_type,
            "experience_id": experience_id,
        }

        plog.info(
            "MockOpenTableApi.lock_booking",
            token=token,
            party_size=party_size,
            date_time=date_time,
        )

        return _ok_response({"reservation_token": token})

    def finalize_booking(
        self,
        first_name,
        last_name,
        phone_number,
        country_code,
        reservation_token,
        special_request="",
        table_type="default",
        experience=None,
    ):
        """Finalize a locked booking.  Retrieves party_size from the pending lock."""
        lock = self._pending_locks.pop(reservation_token, None)
        party_size = lock["party_size"] if lock else 1
        date_time = lock["date_time"] if lock else datetime.now().strftime("%Y-%m-%dT%H:%M")

        booking_id = f"mock-booking-{uuid.uuid4().hex[:8]}"
        booking = {
            "reservation_id": booking_id,
            "first_name": first_name,
            "last_name": last_name,
            "party_size": party_size,
            "date_time": date_time,
            "phone": {
                "number": str(phone_number),
                "country_code": int(country_code),
            },
            "special_request": special_request or "",
        }
        self._bookings[booking_id] = booking

        # Ensure the guest is in our database
        phone_key = str(phone_number).removeprefix("0")
        if phone_key not in self._guests:
            self._guests[phone_key] = {
                "firstName": first_name,
                "lastName": last_name,
                "phone": phone_key,
            }

        plog.info("MockOpenTableApi.finalize_booking", booking_id=booking_id)

        return _ok_response(booking)

    def cancel_booking(self, booking_id):
        """Remove a booking from the in-memory store."""
        if booking_id not in self._bookings:
            return _error_response(400, "InvalidRidOrReservationId")

        del self._bookings[booking_id]
        plog.info("MockOpenTableApi.cancel_booking", booking_id=booking_id)
        return _ok_response({})

    def modify_booking(
        self,
        booking_id,
        party_size=None,
        date_time=None,
        special_request=None,
    ):
        """Modify fields on an existing booking."""
        if booking_id not in self._bookings:
            return _error_response(400, "InvalidRidOrReservationId")

        booking = self._bookings[booking_id]
        if party_size is not None:
            booking["party_size"] = int(party_size)
        if date_time is not None:
            booking["date_time"] = date_time
        if special_request is not None:
            booking["special_request"] = special_request

        plog.info("MockOpenTableApi.modify_booking", booking_id=booking_id)
        return _ok_response(booking)

    def guest_search(self, phone_number):
        """Look up a guest by phone number."""
        phone_key = str(phone_number).removeprefix("0")
        guest = self._guests.get(phone_key)

        plog.info(
            "MockOpenTableApi.guest_search",
            phone=phone_number,
            found=guest is not None,
        )

        if guest:
            return {
                "count": 1,
                "candidates": [guest],
                "primaryGuest": guest,
            }
        return {"count": 0, "candidates": [], "primaryGuest": None}

    def get_bookings(self, phone_number, country_code="1"):
        """Return all bookings for a given phone number."""
        phone_key = str(phone_number).removeprefix("0")
        cc = int(country_code)
        results = [
            b
            for b in self._bookings.values()
            if b["phone"]["number"] == phone_key and b["phone"]["country_code"] == cc
        ]

        plog.info(
            "MockOpenTableApi.get_bookings",
            phone=phone_number,
            count=len(results),
        )

        return _ok_response({"reservations": results})


# ── Response helpers ──────────────────────────────────────────────────────


class _MockResponse:
    """Minimal shim that satisfies ``res.ok``, ``res.status_code``, ``res.json()``,
    and ``res.text`` — the four attributes the calling code checks."""

    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.ok = 200 <= status_code < 300
        self.text = str(body)

    def json(self):
        return self._body


def _ok_response(body):
    return _MockResponse(200, body)


def _error_response(status_code, code):
    return _MockResponse(status_code, {"errors": [{"code": code}]})


@func_description("[UTIL] Mock OpenTable API for demo mode. Do not call directly.")
def mock_api(conv: Conversation):
    pass
