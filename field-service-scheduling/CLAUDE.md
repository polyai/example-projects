# CLAUDE.md — Field Service Scheduling Template

## Overview

Template for a field service / home services scheduling voice agent. Runs against a mock dispatch API by default.

## Key files

| What | Where |
|------|-------|
| Mock dispatch API | `functions/mock_api.py` |
| Slot matching logic | `functions/utils.py` (get_potential_slot) |
| Call init | `functions/start_function.py` |
| Rules | `agent_settings/rules.txt` |

## Mock data

- **John Smith** — Phone: 5550001234, Address: 123 Main St, upcoming appointment tomorrow 9am-12pm
- **Jane Doe** — Phone: 5550005678, Address: 456 Oak Ave, no upcoming appointments

## Flows

1. `initial_ani_lookup` — Identify caller from phone number
2. `verify_user` — Fallback identity verification
3. `schedule_appointment` — Pick service/date/time, confirm
4. `confirm_appointment` — Read back upcoming appointment
5. `reschedule_appointment` — Change existing appointment
6. `cancel_appointment` — Cancel existing appointment
7. `sms_flow` — Confirmation SMS
8. `end_of_call_questions` — CSAT survey
