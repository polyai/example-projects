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

## Prerequisites

Install the ADK, which provides the `poly` CLI:

```bash
pip install polyai-adk
```

Then sign in to your own Agent Studio account — `poly start` for self-serve, or `poly login --region <your-region>` for an enterprise workspace. You don't need access to the account these folders were pulled from; `poly template load` (below) copies a template into a project you already own.

## Quick start

These folders are pulled directly from Agent Studio, so cloning this repo alone won't let you run them — you'd need access to the source account. Instead, load a template into your own project:

```bash
poly init                              # or `poly start`, if you don't have a project yet
poly template load                     # interactive picker — search by name, e.g. "healthcare"
poly chat
```

`poly template load` copies the template's resources into your current project without needing any permissions on the original. Run `poly push` afterwards if you want to save it to your own Agent Studio project.

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
