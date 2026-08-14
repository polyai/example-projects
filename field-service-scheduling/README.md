# Field Service Scheduling Template

A caller schedules, reschedules, or cancels a technician visit. Handles ANI lookup, identity verification, emergencies, and out-of-hours routing. Runs against a mock dispatch API.

## What it does

- **ANI lookup** — Identify caller from inbound phone number
- **Verify user** — Confirm identity if ANI miss (name + address)
- **Schedule appointment** — Pick service type, date, time window
- **Confirm appointment** — Fetch and recite upcoming appointment
- **Reschedule appointment** — Find appointment, pick new slot
- **Cancel appointment** — Confirm and cancel
- **SMS** — Send appointment confirmation
- **CSAT** — Post-call satisfaction

## Quick start

This project is pulled directly from Agent Studio, so you'd need access to its source account to run it as-is. Instead, load it into your own project — no special permissions needed:

```bash
poly template load --region us-1   # interactive picker — search for "field service"
poly chat
```

### Test data

- **Phone:** 555-000-1234 → John Smith, 123 Main St (ANI match)
- **Phone:** 555-000-5678 → Jane Doe, 456 Oak Ave (ANI match)
- Upcoming appointment: John Smith, tomorrow 9am-12pm (General Service)

## ADK primitives demonstrated

- ANI-based auth and fallback verification
- Lifecycle functions (start_function, end_function)
- Time-of-day routing (OOH/emergency)
- Address entity handling
- Multi-flow navigation with state handoffs
- SMS integration
- Post-call CSAT
