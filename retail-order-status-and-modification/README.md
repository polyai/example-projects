# Retail Order Status & Modification Template

A retail customer service agent that verifies callers, looks up orders, provides shipping updates, and handles order modifications, cancellations, and returns. Runs out of the box against mock APIs with test data.

## What it does

- **IDNV** — Verify customer by phone number or order number + name
- **Order lookup** — Find orders by phone or order number
- **WISMO** — "Where is my order?" with shipping status and tracking
- **Cancel/modify** — Cancel or modify pending orders
- **Returns** — Guide customers through return process
- **Handoff** — Transfer to live agent when out of scope
- **SMS** — Send tracking links and return labels via text
- **FAQ** — Answers ~30 common questions (return policy, shipping costs, refunds, etc.)

## Quick start

This project is pulled directly from Agent Studio, so you'd need access to its source account to run it as-is. Instead, load it into your own project — no special permissions needed:

```bash
poly template load --region us-1   # interactive picker — search for "retail" or "order"
poly chat
```

### Test data (happy path)

Say: _"I want to track my order"_

When asked for verification:
- **Phone:** 555-000-1234
- **Name:** John Smith

The mock will show:
- **ORD-001:** Running Shoes + Sport Socks — Shipped, delivery in 3 days
- **ORD-002:** Backpack — Processing

### Second test customer

- **Phone:** 555-000-5678, **Name:** Jane Doe
- **ORD-003:** Sneakers — Delivered

## Project structure

```
├── agent_settings/          # Personality, role, rules
├── config/
│   ├── sms_templates.yaml   # SMS message templates
│   └── variant_attributes.yaml  # Store config (name, URLs, policies)
├── flows/
│   ├── initial_ani_lookup/  # Caller phone identification
│   ├── oms_idnv/            # Order management ID verification
│   ├── oms_wismo/           # Where Is My Order tracking
│   ├── order_management_flow_v2/  # Order cancel/modify
│   └── sms_flow/            # SMS delivery
├── functions/
│   ├── mock_api.py          # In-memory mock (OMS, shipping, ticketing)
│   ├── oms_connector.py     # Real OMS handler
│   ├── narvar_client.py     # Real shipping/tracking handler
│   └── ...                  # Flow-specific functions
├── topics/                  # 30 FAQ topics
└── tests/                   # Structured conversation tests
```

## Customisation guide

### 5-minute setup
1. `ad chat` — WISMO happy path works against mock
2. Edit `voice/configuration.yaml` to change the greeting

### 30-minute setup
1. Edit topics in `topics/` to match your store's policies
2. Update `config/variant_attributes.yaml` with real store details
3. Update `config/sms_templates.yaml` with your URLs

### Production setup (real OMS)
1. Set `use_real_api` flag in real-time config
2. Configure OMS/Narvar/Zendesk API credentials in Agent Studio secrets
3. Update API client files with your endpoint patterns

## ADK primitives demonstrated

- IDNV with ANI lookup and order number verification
- API-style function calls (OMS, shipping, ticketing)
- Handoff to human agents
- Deterministic routing in Python (not in prompts)
- Multi-turn state management
- SMS integration
- Topic-based FAQ with RAG
