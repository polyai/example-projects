# CLAUDE.md — Healthcare Appointment Scheduling Template

## Overview

This is a template project for a healthcare appointment scheduling voice agent. It runs against a mock EHR API by default — no credentials needed.

## Key files

| What | Where |
|------|-------|
| Mock API (test patients, slots) | `functions/mock_api.py` |
| Real EHR handler (production) | `functions/api_handler.py` |
| Call init (timezone, OOH) | `functions/start_function.py` |
| Routing rules | `agent_settings/rules.txt` |
| Handoff targets | `config/handoffs.yaml` |
| Voice greeting | `voice/configuration.yaml` |

## Mock API test data

Two test patients are available in `functions/mock_api.py`:

- **Jane Smith** — Phone: 5550001234, DOB: 1985-03-15, ID: MOCK-P001
- **John Doe** — Phone: 5550005678, DOB: 1990-07-22, ID: MOCK-P002

Available booking slots: Aug 20 (9am, 11am, 2pm) and Aug 21 (10am, 3pm).

## Flows

Five flows, matching the brief:
1. `idnv` — Verify patient identity (phone + DOB + name)
2. `booking_flow` — Collect appointment type, find slot, confirm
3. `cancel_flow` — Find appointment, confirm cancellation
4. `reschedule_flow` — Find appointment, pick new slot, confirm
5. `sms_flow` — Send confirmation SMS

## Common tasks

```bash
# Test locally
ad chat

# Run tests
pytest tests/

# Validate project structure
ad validate

# Format code
ad format
```

## Customisation

- **Timezone/hours**: Edit `CLINIC_TIMEZONE`, `OPENING_TIME`, `CLOSING_TIME` in `functions/time_utils.py` and `functions/start_function.py`
- **Handoffs**: Edit `config/handoffs.yaml` (8 generic targets) and `functions/handoff.py` (reason mapping)
- **Topics**: Edit YAML files in `topics/` — 25 generic healthcare FAQ topics
- **Switching to real EHR**: Set `use_real_api` flag in real-time config; update `api_handler.py` with your credentials secret name
