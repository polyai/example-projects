# CLAUDE.md — Financial Services Bill Pay Template

## Overview

Template for a bill pay / payment collection voice agent. Runs against a mock billing API by default.

## Key files

| What | Where |
|------|-------|
| Mock billing API | `functions/mock_api.py` |
| Call init | `functions/start_function.py` |
| Rules | `agent_settings/rules.txt` |
| Voice greeting | `voice/configuration.yaml` |

## Mock data

- **John Smith** — Account: 1234567890, DOB: 1985-03-15, Balance: $150.00
- **Jane Doe** — Account: 0987654321, DOB: 1990-07-22, Balance: $275.50

## Flows

1. `greet_user` — Initial greeting and routing
2. `payments_general` — Balance lookup and payment routing
3. `make_payment` — Card collection and payment processing
4. `sms_flow` — Confirmation SMS
5. `csat` — Post-call satisfaction
6. `reset_failure_counter` — Error recovery
