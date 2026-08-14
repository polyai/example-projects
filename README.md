# PolyAI ADK Example Projects

Working example voice agent projects for the [PolyAI Agent Development Kit (ADK)](https://pypi.org/project/polyai-adk/). Each folder is a complete Agent Studio project you can pull, run, and edit locally with the `poly` CLI — no live account needed, since every template runs against a mock backend API by default.

## Templates

| Template | What it does |
|---|---|
| [`field-service-scheduling`](field-service-scheduling) | Schedules, reschedules, and cancels technician visits. ANI lookup, identity verification, emergency and out-of-hours routing. |
| [`financial-services-bill-pay-and-collection`](financial-services-bill-pay-and-collection) | Verifies a caller, reads out a balance, takes a payment, and offers payment plans or escalation. |
| [`healthcare-appointment-scheduling`](healthcare-appointment-scheduling) | Books, cancels, and reschedules clinic appointments for a verified patient. |
| [`restaurant-table-booking`](restaurant-table-booking) | Takes, confirms, modifies, and cancels restaurant table reservations. |
| [`retail-order-status-and-modification`](retail-order-status-and-modification) | Verifies a customer, looks up orders, gives shipping updates, and handles cancellations/modifications. |

Each folder has its own README with the flows it demonstrates and test data to try.

## Prerequisites

Install the ADK, which provides the `poly` CLI:

```bash
pip install polyai-adk
```

Then authenticate against the region these projects live in (`us-1`):

```bash
poly login --region us-1
```

## Quick start

```bash
cd <template-folder>
poly chat
```

`poly chat` starts an interactive session with the agent, running against the mock API bundled in `functions/`. Each template's README lists test data (phone numbers, names, etc.) to try the happy path.

## Project structure

Every template folder contains:

```
├── project.yaml        # Agent Studio project_id, account_id, region
├── agent_settings/      # Personality, role, rules
├── config/              # Entities, handoffs, SMS templates
├── flows/               # Conversational flows
├── functions/           # Python logic, incl. the mock API
├── topics/              # FAQ topics
├── voice/               # Voice config, pronunciations
└── tests/               # Automated conversation tests
```

`project.yaml` is what makes a folder a distinct Agent Studio project — it's how [`poly pull`](https://polyai.github.io/adk/reference/cli/#poly-pull) knows what to sync.

## Keeping templates in sync

[`.github/workflows/adk-pull.yml`](.github/workflows/adk-pull.yml) runs daily and on demand: it finds every folder with a `project.yaml`, runs `poly pull --force --format` in each against Agent Studio, and commits any changes straight to `main`. Trigger it manually from the **Actions** tab if you need an out-of-band sync.
