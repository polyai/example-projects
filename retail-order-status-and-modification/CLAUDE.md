# CLAUDE.md — Retail Order Status & Modification Template

## Overview

Template project for a retail customer service voice agent handling order tracking, cancellations, returns, and FAQs. Runs against mock APIs by default.

## Key files

| What | Where |
|------|-------|
| Mock APIs (orders, shipping, ticketing) | `functions/mock_api.py` |
| Real OMS handler | `functions/oms_connector.py` |
| Real shipping/tracking | `functions/narvar_client.py` |
| Real ticketing | `functions/zendesk_client.py` |
| Call init | `functions/start_function.py` |
| Routing rules | `agent_settings/rules.txt` |
| Store config | `config/variant_attributes.yaml` |

## Mock API test data

Two test customers:

- **John Smith** — Phone: 5550001234, Email: john@example.com
  - ORD-001: Running Shoes + Sport Socks (Shipped, delivery in 3 days)
  - ORD-002: Backpack (Processing)
- **Jane Doe** — Phone: 5550005678, Email: jane@example.com
  - ORD-003: Sneakers (Delivered)

## Flows

1. `initial_ani_lookup` — Identify caller from inbound number
2. `oms_idnv` — Verify identity via order number or phone + name
3. `oms_wismo` — "Where is my order" — shipping status + tracking
4. `order_management_flow_v2` — Cancel or modify orders
5. `sms_flow` — Send tracking links via SMS

## Common tasks

```bash
ad chat              # Test locally
pytest tests/        # Run tests
ad validate          # Validate structure
```

## Customisation

- **Store name/policies**: Edit `config/variant_attributes.yaml`
- **Topics**: Edit YAML files in `topics/` — 30 retail FAQ topics
- **Switching to real APIs**: Set `use_real_api` flag; configure OMS/Narvar/Zendesk credentials
