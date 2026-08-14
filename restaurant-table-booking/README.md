# Restaurant Table Booking Template

A single-site restaurant agent that takes, confirms, modifies, and cancels table reservations and answers FAQs. Runs out of the box against a mock reservation API with test data.

## What it does

- **Make booking** — Collect date, time, party size, name, phone; check availability; confirm
- **Modify booking** — Look up by phone, change date/time/party size
- **Cancel booking** — Look up by phone, confirm cancellation
- **Booking disambiguation** — When a caller has multiple upcoming bookings
- **SMS** — Send booking confirmation link
- **CSAT** — Post-call satisfaction (optional)
- **FAQ** — Answers ~25 common questions (hours, menu, parking, allergies, etc.)

## Quick start

This project is pulled directly from Agent Studio, so you'd need access to its source account to run it as-is. Instead, load it into your own project — no special permissions needed:

```bash
poly template load --region us-1   # interactive picker — search for "restaurant"
poly chat
```

### Test data (happy path)

Say: _"I'd like to make a reservation for 4 people tomorrow at 7pm"_

The mock returns availability slots for the next 3 days. When asked for your name, use **John Smith** with phone **555-000-1234**.

### Existing bookings (cancel/modify)

- **John Smith** — party of 4, tomorrow at 7pm (phone: 555-000-1234)
- **Jane Doe** — party of 2, day after tomorrow at 8pm (phone: 555-000-5678)

## Project structure

```
├── agent_settings/          # Personality, role, rules, experimental config
├── config/
│   ├── sms_templates.yaml   # SMS message templates
│   └── variant_attributes.yaml  # Single-site config (name, hours, address)
├── flows/
│   ├── make_booking/        # New reservation flow
│   ├── confirm_cancel_modify_booking/  # Manage existing bookings
│   ├── booking_disambiguation_flow/    # Multiple bookings disambiguation
│   ├── sms_flow/            # SMS confirmation
│   └── csat/                # Post-call satisfaction
├── functions/
│   ├── mock_api.py          # In-memory mock reservation system (runs by default)
│   ├── opentable_api.py     # Real OpenTable handler (for production)
│   └── ...                  # Flow-specific functions
├── topics/                  # 25 FAQ topics
├── voice/                   # Voice config, keyphrases
└── tests/                   # Structured conversation tests
```

## Customisation guide

### 5-minute setup
1. `ad chat` — booking happy path works against mock
2. Edit `voice/configuration.yaml` to change the greeting
3. Edit topic YAMLs to match your venue

### 30-minute setup
1. Edit `config/variant_attributes.yaml` with your restaurant's real hours, address, phone
2. Update `config/sms_templates.yaml` with your URLs
3. Customise ~5 topic YAMLs (menu, hours, parking, etc.)

### Production setup (real reservation system)
1. Set `use_real_api` flag in real-time config
2. Configure OpenTable API credentials in Agent Studio secrets
3. Update `functions/opentable_api.py` with your restaurant ID

## ADK primitives demonstrated

- Flows + steps with low-code configuration
- Entity extraction (date, time, party size, name, phone)
- Multi-turn state management
- SMS integration
- Post-call CSAT
- Topic-based FAQ with RAG
- Conditional booking disambiguation
- Background restaurant ambiance track
