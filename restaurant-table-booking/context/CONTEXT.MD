# Restaurant template

The phone host for one restaurant site. Books, checks, changes and cancels tables, answers questions, texts links (menu, takeout, private dining, group form) and puts callers through to the team.

- **Shape (flat):** one flow per task, one advanced step each. `check_booking`, `change_booking` and `cancel_reservation` start with an entry function step that checks ID&V and picks the booking. Rules live in tool code (`functions/bookings.py`, `functions/hours.py`, `functions/idnv.py`); flow tools import only from `functions/`.
- **Booking:** day and time, party size, availability, name, number, one note question, readback, "Shall I go ahead and book that?". A free time is said plainly with no alternatives. A taken time returns every free time in the API's window (OpenTable: about three hours either side); the model offers two at most. A full day returns the nearest day each side; the next free table only when asked.
- **ID&V (lax):** only to find an existing booking: caller ID match, or the number the booking is under plus the name. The number is never read back. No caller ID (Studio chat, an email address) is never a fixture caller.
- **Consent:** writes return the readback; an acknowledgement to its question is a yes; an "okay" to information writes nothing; a same-turn yes writes nothing and speaks the readback again. Done lines are spoken from code.
- **Facts:** variant attributes (`site_name`, `address`, `address_info`, `phone_number`, `opening_hours`, `timezone`, `*_info`). Blank hours are never spoken or treated as closed.
- **Switches:** real-time config `settings`: `max_party_size` (8), `cancel_booking_flow_enabled` (true), `transfer_out_of_hours` (true), `csat_enabled` (false), `use_mock_api` (true).
- **Data:** `functions/api_client.py`, mocked outside live. Fixtures: John Smith 201-555-0123 (4 people tomorrow 7pm), Jane Doe 212-555-0178 (2 people, day after tomorrow 8pm), Maria Garcia 312-555-0144 (two bookings), Alex Turner 201-555-0177 (none upcoming), 201-555-0199 (no guest). Friday and Saturday evenings are busy.
