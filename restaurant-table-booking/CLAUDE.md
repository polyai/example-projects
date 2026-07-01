# CLAUDE.md — Restaurant Table Booking Template

## Overview

Template project for a single-site restaurant reservation voice agent. Runs against a mock reservation API by default — no credentials needed.

## Key files

| What | Where |
|------|-------|
| Mock API (availability, bookings) | `functions/mock_api.py` |
| Real OpenTable handler | `functions/opentable_api.py` |
| Call init (hours, dates, features) | `functions/start_function.py` |
| Routing rules | `agent_settings/rules.txt` |
| Site config (hours, address) | `config/variant_attributes.yaml` |
| Voice greeting | `voice/configuration.yaml` |

## Mock API test data

- **Restaurant:** Poly Bistro (MOCK-RID-001), max party 8
- **Availability:** Tomorrow + 2 more days, lunch and dinner slots
- **Booking 1:** John Smith, party 4, tomorrow 7pm (phone: 5550001234)
- **Booking 2:** Jane Doe, party 2, day after tomorrow 8pm (phone: 5550005678)

## Flows

1. `make_booking` — Collect date/time/party size/name/phone, check availability, confirm
2. `confirm_cancel_modify_booking` — Look up existing booking, cancel or modify
3. `booking_disambiguation_flow` — When caller has multiple bookings
4. `sms_flow` — Send confirmation SMS
5. `csat` — Post-call satisfaction survey

## Common tasks

```bash
ad chat              # Test locally
pytest tests/        # Run tests
ad validate          # Validate structure
```

## Customisation

- **Restaurant name/hours/address**: Edit `config/variant_attributes.yaml`
- **Greeting**: Edit `voice/configuration.yaml`
- **Menu/FAQ content**: Edit YAML files in `topics/`
- **Switching to real OpenTable**: Set `use_real_api` flag; configure API credentials
