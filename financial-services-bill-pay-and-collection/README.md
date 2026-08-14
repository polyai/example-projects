# Financial Services — Bill Pay & Payment Collection Template

A verified-identity agent for bill pay: verify caller, read out balance, take a payment, offer payment plans, and escalate failed payments. Runs out of the box against a mock billing API.

## What it does

- **IDNV** — Verify caller by account number + DOB or phone
- **Balance lookup** — Fetch and recite current balance
- **Make payment** — Collect amount, card details (PCI-safe), confirm
- **Payment plan** — Offer split or future-dated payments
- **Handoff** — Failed payment or hardship → live agent
- **SMS** — Send receipt/confirmation link
- **CSAT** — Post-call satisfaction
- **FAQ** — ~50 topics (payment methods, late fees, autopay, billing, disputes, etc.)

## Quick start

This project is pulled directly from Agent Studio, so you'd need access to its source account to run it as-is. Instead, load it into your own project — no special permissions needed:

```bash
poly template load --region us-1   # interactive picker — search for "banking" or "bill pay"
poly chat
```

### Test data

- **Account:** 1234567890, **DOB:** 1985-03-15, **Name:** John Smith
  - Balance: $150.00, one pending payment of $50
- **Account:** 0987654321, **DOB:** 1990-07-22, **Name:** Jane Doe
  - Balance: $275.50, no pending payments

## ADK primitives demonstrated

- IDNV with account number verification
- PII handling (`is_pii: true` for card details, DTMF collection)
- Payment confirmation patterns
- Error recovery and handoff fallbacks
- Multi-flow navigation with state handoffs
- SMS integration
