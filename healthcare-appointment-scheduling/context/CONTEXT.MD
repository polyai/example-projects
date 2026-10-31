# Healthcare template

Books, checks, moves and cancels clinic appointments, answers clinic FAQs, and texts the clinic address.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. Task flows (`book_appointment`, `confirm_appointment`, `reschedule_appointment`, `cancel_appointment`) start with an entry function step that checks ID&V and picks the appointment. Rules live in tool code (`functions/appointments.py`, `functions/idnv.py`); tools say what to read back and what to ask next, and end with a CALL STATE block. A retry return names the attempt ("attempt 1 of 2") and says to call the same tool again; writes ask one short yes-or-no question naming the action and the item (no separate readback, 25 words or fewer) and need a clear yes to it in the caller's latest reply; a yes in the same turn as the question (history length unchanged, a marker only) writes nothing. No keypad (`dtmf_config` is ignored on Dialog-RSN-1 voice). `rules.txt` stays under 1k tokens and holds the pass-every-parameter rule.
- **ID&V (strict):** phone number on the record + date of birth + member ID (`flows/verify_caller`). Never reveal whether a record exists or which detail failed. Retry limits and the transfer on failure are in `functions/idnv.py` (shared; don't edit here).
- **Company copy:** one default variant; every clinic fact is a variant attribute (`site_name`, the four location attributes, `timezone`, contacts, `providers`, and `_info` policy text), wired into topics, rules, SMS and code. `opening_hours` + `timezone` drive out-of-hours and the slots offered; when `opening_hours` is blank those rules use a weekday 8am-5pm default that is never spoken (the agent says it doesn't have the exact hours to hand). See README. Out of hours `handoff` refuses transfers in code (closed line instead) except emergencies, `CLINICAL_SUPPORT` and tool-made transfers (`transfers_when_closed`).
- **Data:** `functions/api_client.py`. Mocked on branch, draft and sandbox; mocked on pre-release and live until `settings.use_mock_api` is false. Mock bookings live in `conv.state`.
- **Switches (real-time config):** `settings.cancel_appointment_flow_enabled` (default true; false transfers cancellations), `settings.use_mock_api`.
- **Fixtures:** Jane Smith 201-555-0123, DOB 1985-03-15, member ID HC48213 (one follow-up); John Doe 212-555-0178, DOB 1990-07-22, HC77306 (two appointments); 201-555-0199 (no record).

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "book-appointment",
      "title": "Book an appointment",
      "prompt": "I'd like to schedule an appointment.",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213"
      },
      "goal": "The agent asks for the phone number, date of birth and member ID one at a time (or takes them all at once), verifies Jane Smith and, in the same reply, asks what kind of appointment she needs. Given 'a new health issue' it offers one slot (the earliest, e.g. tomorrow at 9am with Dr. Smith) and books it on a yes."
    },
    {
      "id": "cancel-appointment",
      "title": "Cancel - patient with two appointments",
      "prompt": "I need to cancel an appointment.",
      "context": {
        "Phone": "2125550178",
        "DOB": "July 22, 1990",
        "Member ID": "HC77306"
      },
      "goal": "After verification the agent lists John Doe's follow-up and sick visit, asks which one, reads the chosen one back with its type, date, time and provider, and cancels it on a yes without asking for a reason."
    },
    {
      "id": "reschedule-appointment",
      "title": "Reschedule an appointment",
      "prompt": "Can I move my appointment to a different day?",
      "context": {
        "Phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213"
      },
      "goal": "After verification the agent mentions Jane's follow-up (date, time, Dr. Smith), asks when would suit instead, offers one new slot and moves it on a yes."
    },
    {
      "id": "wrong-dob",
      "title": "Wrong date of birth twice",
      "prompt": "I need to reschedule my appointment.",
      "context": {
        "Phone": "2015550123",
        "DOB given": "January 1, 1990",
        "Member ID": "HC48213"
      },
      "goal": "The agent says the details don't match without saying which, asks for them again (one at a time, starting with the date of birth), then transfers to the scheduling team. No appointment, provider or name is mentioned."
    },
    {
      "id": "unknown-number",
      "title": "No patient record",
      "prompt": "I'd like to book an appointment.",
      "context": {
        "Phone": "2015550199"
      },
      "goal": "The agent collects all three details, reads the number back, and never says no record exists. A confirmed number counts as a failed check; a caller with no other number is transferred."
    },
    {
      "id": "faq-hours",
      "title": "FAQ - clinic hours",
      "prompt": "What are your hours?",
      "context": {},
      "goal": "Agent gives the opening hours from the opening_hours attribute (Monday to Friday, 8am to 5pm; closed weekends) without asking for verification."
    },
    {
      "id": "faq-insurance",
      "title": "FAQ - accepted insurance",
      "prompt": "Do you accept Blue Cross?",
      "context": {},
      "goal": "Agent answers the insurance question from the knowledge base, no IDNV needed."
    },
    {
      "id": "phone-readback-correction",
      "title": "Correct the phone number at readback",
      "prompt": "I'd like to schedule an appointment.",
      "context": {
        "First number given": "2015550128",
        "Correct phone": "2015550123",
        "DOB": "March 15, 1985",
        "Member ID": "HC48213"
      },
      "goal": "Caller gives 2015550128 with the right DOB and member ID. The agent reads the number back digit by digit using \"zero\", without saying whether a record exists. The caller says the last digit is three; the agent verifies with the corrected number without asking for the DOB or member ID again."
    },
    {
      "id": "speak-to-doctor",
      "title": "Ask to speak to a doctor",
      "prompt": "I need to speak with my doctor.",
      "context": {},
      "goal": "Agent does not start booking or IDNV and does not ask for phone, DOB, or name. Monday to Friday, 8am to 5pm New York time, it says it is transferring the caller and the call ends (mock handoff in sandbox and draft). Out of hours it says the clinic is closed and gives the opening hours without offering a transfer."
    }
  ]
}
```
