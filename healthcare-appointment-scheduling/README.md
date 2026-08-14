# Healthcare Appointment Scheduling Template

A verified-identity voice agent that handles appointment booking, cancellation, and rescheduling for a healthcare clinic. Runs out of the box against a mock EHR API with test patients.

## What it does

- **ID&V** — Verifies patients by phone number + date of birth + name
- **Book** — Collects appointment type, finds available slots, confirms booking
- **Cancel** — Looks up upcoming appointments, confirms cancellation
- **Reschedule** — Finds existing appointment, picks a new slot, confirms
- **SMS** — Sends booking confirmation via text
- **FAQ** — Answers ~25 common clinic questions (hours, insurance, policies, etc.)

## Quick start

This project is pulled directly from Agent Studio, so you'd need access to its source account to run it as-is. Instead, load it into your own project — no special permissions needed:

```bash
poly template load --region us-1   # interactive picker — search for "healthcare" or "clinic"
poly chat

# Or with metadata to see function calls and state
poly chat --metadata
```

### Test patient (happy path)

Say: _"I'd like to book an appointment"_

When asked for verification:
- **Phone:** 555-000-1234
- **DOB:** March 15, 1985
- **Name:** Jane Smith

The mock will offer slots on August 20 and 21.

## Project structure

```
├── agent_settings/          # Personality, role, rules, experimental config
│   ├── experimental_config.json
│   ├── personality.yaml
│   ├── role.yaml
│   └── rules.txt
├── config/
│   ├── entities.yaml        # phone_number, date_of_birth, full_name
│   ├── handoffs.yaml        # 8 generic handoff targets
│   └── sms_templates.yaml
├── flows/
│   ├── idnv/                # Identity verification
│   ├── booking_flow/        # Appointment booking
│   ├── cancel_flow/         # Appointment cancellation
│   ├── reschedule_flow/     # Appointment rescheduling
│   └── sms_flow/            # SMS confirmation
├── functions/
│   ├── mock_api.py          # In-memory mock EHR (runs by default)
│   ├── api_handler.py       # Real EHR handler (for production use)
│   ├── start_function.py    # Call initialization
│   ├── end_function.py      # Post-call metrics
│   └── ...                  # Flow-specific functions
├── topics/                  # 25 FAQ topics (hours, insurance, policies, etc.)
├── voice/                   # Voice config, keyphrase boosting, pronunciations
└── tests/                   # Structured conversation tests
```

## Customisation guide

### 5-minute setup (mock API)
1. `ad chat` — verify the happy path works
2. Edit `voice/configuration.yaml` to change the greeting
3. Edit `agent_settings/rules.txt` to adjust routing logic

### 30-minute setup (your clinic)
1. Edit topics in `topics/` to match your clinic's policies
2. Update `config/handoffs.yaml` with real phone numbers
3. Update `config/sms_templates.yaml` with your clinic details
4. Edit `functions/time_utils.py` to set your timezone and hours

### Production setup (real EHR)
1. Create API credentials in Agent Studio secrets
2. Set the `use_real_api` flag in real-time config
3. Update `functions/api_handler.py` with your EHR's endpoint patterns
4. Replace `functions/nextgen_*_models.py` with your EHR's data models

## ADK primitives demonstrated

- ID&V with state counters and retry logic
- Lifecycle functions (`start_function`, `end_function`)
- Multi-flow navigation with state handoffs
- Entity extraction (phone, date, name)
- Topic-based FAQ with RAG
- SMS integration
- Out-of-hours routing
- Handoff to live agents
- Metrics and observability
