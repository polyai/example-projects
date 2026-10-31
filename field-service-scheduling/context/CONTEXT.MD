# Field Service template

Books, checks, moves and cancels technician visits, answers service FAQs, and texts portal links.

- **Shape (flat):** one flow per task, each with one advanced step and a short numbered prompt. Task flows (`schedule_appointment`, `confirm_appointment`, `reschedule_appointment`, `cancel_appointment`) start with an entry function step that checks ID&V and picks the visit. Rules live in tool code (`functions/visits.py`, `functions/idnv.py`); tools say what to read back and what to ask next, and end with a CALL STATE block.
- **ID&V (lax):** caller ID match, or the phone number on the account plus the account holder's name (`flows/verify_caller`). Retry limits and the transfer on failure are in `functions/idnv.py`; each miss names the attempt and tells the agent to call `verify_caller` again. A read-back number counts only with `phone_confirmed='true'` (a clear yes or the same number again, not an "okay"; the second unconfirmed readback transfers; any other reply goes to `verify_caller` with `phone_confirmed='false'` so it is counted, never re-asked by the agent); a name mismatch says the phone number is kept and asks only for the name. No caller ID (Studio chat or a simulation without `caller_number`) is never the fixture account.
- **RSN-1:** tools have at most six parameters (booking is `update_visit_request` for what and where plus `find_visit_time` for when); writes need a clear yes to the yes-or-no question the tool's readback asks (it names the action; the readback is only the visit or number and its window, 25 words or fewer in all; "okay" isn't a yes), and a yes in the same turn as the question returns `NOT DONE YET` (`visits.same_turn_as_question`, history length as a marker only); after an ID&V readback the agent waits for the answer; no keypad entry (`dtmf_config` is Raven 3.5 only).
- **Company facts:** variant attributes on the one default variant: `site_name`, the location four (`address`, `address_info`, `phone_number`, `opening_hours`), `timezone`, and the `_info` facts (services, area, pricing, emergency, payment, guarantee, plans, windows, visit prep, cancellation policy, licensing) plus `customer_portal_url`. Topics, rules and SMS read them; hours and timezone are read in code (`functions/utils.py`) from `conv.variant`, never real-time config. Blank or unreadable `opening_hours` counts as open, and the agent says it doesn't have the exact hours to hand; keep the attribute blank rather than filling a default. Switches (`hours_sensitive`, `force_ooh_enabled`, `cancel_appointment_flow_enabled`, `use_mock_api`) stay in real-time config `settings`.
- **Data:** `functions/api_client.py`. Mocked on branch, draft and sandbox; mocked on pre-release and live until `settings.use_mock_api` is false. Mock bookings live in `conv.state`, so test calls never share data.
- **Fixtures:** John Smith 201-555-0123 (General Service visit tomorrow 9am-12pm), Jane Doe 212-555-0178 (no visits), 201-555-0199 (no account).

## Test scenarios

```json
{
  "scenarios": [
    {
      "id": "schedule-appointment",
      "title": "Schedule a new service appointment",
      "prompt": "I need to schedule a service visit.",
      "attributes": {
        "variant": "Poly_Services",
        "service_types": [
          "General Service",
          "Deep Clean",
          "Emergency Repair",
          "Maintenance Check"
        ],
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With caller ID 2015550123 the caller ID matches John Smith and no questions are asked; from any other number the agent asks for the phone number on the account and the account holder's name (see ani-miss-verify). The agent takes the problem (General Service, leak under the kitchen sink), where it is (kitchen, so indoors) and when suits, in any order, offers one arrival window with a full readback (for example tomorrow 1pm-4pm) and books it on a yes"
    },
    {
      "id": "confirm-upcoming-appointment",
      "title": "Confirm an upcoming appointment",
      "prompt": "I'm calling to confirm my appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With ANI matched to John Smith (caller ID 2015550123), agent identifies John Smith at 123 Main St, finds appointment MOCK-APT-001 (tomorrow 9am-12pm), and confirms the details"
    },
    {
      "id": "reschedule-appointment",
      "title": "Reschedule an existing appointment",
      "prompt": "I need to reschedule my appointment to a different day.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With ANI matched to John Smith, agent finds the appointment (tomorrow 9am-12pm), offers available windows, and confirms the reschedule"
    },
    {
      "id": "cancel-appointment",
      "title": "Cancel an existing appointment",
      "prompt": "I need to cancel my service appointment.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "With caller ID matched to John Smith, the agent reads back visit MOCK-APT-001 (tomorrow 9am-12pm) and asks whether to cancel it; only on a clear yes does it cancel with cancel_visit (an \"okay\" or anything unclear is asked again). Setting settings.cancel_appointment_flow_enabled to false in real-time config sends cancellations to a colleague instead"
    },
    {
      "id": "ani-miss-verify",
      "title": "ANI miss - verify user by phone and ZIP",
      "prompt": "I'd like to schedule a visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2125550178",
        "Name": "Jane Doe"
      },
      "goal": "Caller ID does not match (a call from any number other than 2015550123). The agent enters verify_caller, collects phone 2125550178 and the name Jane Doe, verifies, and goes straight back to scheduling without asking for anything the caller already said"
    },
    {
      "id": "faq-services",
      "title": "FAQ - what services are offered",
      "prompt": "What services do you offer?",
      "attributes": {
        "variant": "Poly_Services",
        "service_types": [
          "General Service",
          "Deep Clean",
          "Emergency Repair",
          "Maintenance Check"
        ],
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent lists available service types: General Service, Deep Clean, Emergency Repair, Maintenance Check"
    },
    {
      "id": "faq-need-to-be-home",
      "title": "FAQ - do I need to be home",
      "prompt": "Do I need to be home?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent explains outdoor work doesn't require presence, indoor work needs someone to let the technician in"
    },
    {
      "id": "verify-unknown-number-readback",
      "title": "Unknown number read back, then corrected",
      "prompt": "I'd like to schedule a visit.",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "First number given": "2015550199",
        "Correct phone": "2125550178",
        "Name": "Jane Doe"
      },
      "goal": "Caller gives 2015550199, which has no account. The agent reads it back as \"two zero one, five five five, zero one nine nine\" and asks if that's right. Caller corrects it to 2125550178; the agent asks for the name, verifies Jane Doe and continues to scheduling"
    },
    {
      "id": "phone-number-pause-partial",
      "title": "Pause and partial phone number",
      "prompt": "Can I schedule a new service appointment?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {
        "Phone": "2015550123",
        "Name": "John Smith"
      },
      "goal": "From a number that is not on the account, the caller says \"Yes, the phone number is\" and pauses, then gives only \"two zero one\", then \"two zero one five five five zero one to three\". The agent says \"Go ahead\" or asks for the full ten-digit number, treats \"to\" as two, finds the account on 2015550123, asks for the name and continues to scheduling. It never transfers because of trouble collecting the number unless the code's limit (three unusable numbers) is reached"
    },
    {
      "id": "speak-to-someone",
      "title": "Ask for a person",
      "prompt": "Can I talk to someone?",
      "attributes": {
        "variant": "Poly_Services",
        "site_name": "Poly Services"
      },
      "context": {},
      "goal": "Agent first offers to help itself. When the caller declines, it says \"Sure, I'll put you through to a colleague. One moment please.\" and the call ends (mock handoff in sandbox and draft)"
    }
  ]
}
```
