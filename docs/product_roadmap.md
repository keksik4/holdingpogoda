# Product Roadmap

## Before A Polished Frontend

The next technical phase should strengthen the backend before design polish:

- Add automated smoke tests for all endpoints.
- Add database migrations instead of relying on automatic table creation.
- Add scheduled weather refresh and daily forecast jobs.
- Add clearer import replacement options for real company data.
- Add richer historical weather backfill.
- Add archived forecast alignment for decision-time model training.
- Add school holiday and local event calendars.
- Add model experiment tracking.

## Polished Frontend Phase

Build a role-based product UI:

- management dashboard
- operations planner
- marketing opportunity view
- data import/admin view
- provider health screen
- forecast scenario explorer

## AI Narrative Phase

Add an LLM layer only after deterministic outputs are stable. The LLM should summarize forecasts, explain risks, draft manager briefings, and generate marketing copy variants from validated backend data.

## Integration Phase

Connect real systems:

- ticketing and POS
- campaign and ad platforms
- staffing and shift planning
- parking and queue systems
- CRM/newsletter tools
- finance and revenue reporting

## Production Phase

- PostgreSQL
- authentication and roles
- deployment
- backups
- monitoring
- alerts
- audit logs
- secure configuration management

## Business Outcome

The mature product should move the company from reactive planning to a repeatable operating rhythm: forecast, explain, recommend, execute, measure, and improve.
