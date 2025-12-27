# Sago Re-Engagement Agent

Production-grade agent for automated investor re-engagement. When an investor passes on a startup but wants to stay in touch, this system monitors Gmail and Slack for meaningful signals (traction, hiring, funding, needs) and generates personalized outreach when the right moment arrives.

## Status
✅ Ready for production deployment

## Design Principles

This project demonstrates the three Sago design principles:

1. **Seamless Integration**: The agent lives inside Gmail and Slack. No new UI to learn. It reads from your inbox and channels, creates drafts or DMs in-place, and logs to your existing CRM.

2. **Hyper-Personalization**: Every outreach references your thesis keywords, prior meeting notes, agreed follow-up triggers, and availability. The agent knows what you talked about and why you passed.

3. **True Agency**: Beyond surfacing data, the agent takes action: drafts emails, attaches resources (SOC2 templates), offers intros, and schedules reminders. Human-in-the-loop approval by default.

## Project Structure

```
sago/
  __init__.py          # Package exports
  models.py            # Domain models (Signal, Company, User, etc.)
  agent.py             # Core logic (policy, actions, outreach)
  integrations.py      # Gmail, Slack, LLM connectors
examples/
  demo.py              # Standalone demo
tests/
  test_agent.py        # Unit tests
docs/
  architecture.md      # System design (export to PDF)
  sample_inputs_outputs.md
```

## Quick Start

### Option 1: Run the demo (no dependencies)

```bash
python examples/demo.py
```

This runs the full workflow with mock data and prints the evaluation, planned actions, and generated outreach.

### Option 2: Run with Docker (full stack)

```bash
cp .env.example .env
# Edit .env with your API keys

docker-compose up -d
docker-compose logs -f demo
```

This spins up PostgreSQL with pgvector, Redis, and the Celery worker.

## How It Works

### 1. Ingestion
Gmail and Slack connectors fetch new messages on a schedule (hourly) or via webhooks. Raw events are normalized and queued.

### 2. Signal Detection
An LLM classifier (GPT-4 or Claude) analyzes each event and extracts structured signals:
- **Traction**: customer wins, revenue, usage
- **Hiring**: key roles, team growth
- **Funding**: rounds, runway updates
- **Need**: asks for help, templates, intros
- **Risk**: churn, layoffs, pivots

Each signal gets a confidence score (0-1) and is stored with its embedding for semantic search.

### 3. Policy Evaluation
For each company, the agent checks:
- Are there actionable signals above the confidence threshold (default 0.6)?
- Do the signals match the agreed follow-up trigger from the last meeting?
- Has enough time passed since the last outreach (cooldown period)?

### 4. Outreach Generation
If re-engagement is warranted, the agent:
- Retrieves prior interaction notes and user profile
- Generates a personalized message grounded in thesis, signals, and availability
- Plans secondary actions (share resources, offer intros, log to CRM)

### 5. Execution
Actions are queued for approval or auto-executed based on user settings. Drafts appear in Gmail; DMs go to Slack. Everything is logged.

## Configuration

Key settings in `.env`:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | For signal detection and outreach generation |
| `SLACK_BOT_TOKEN` | Slack bot for reading messages and sending DMs |
| `GOOGLE_CLIENT_ID` | OAuth for Gmail access |
| `SIGNAL_CONFIDENCE_THRESHOLD` | Minimum confidence to act (default 0.6) |
| `AUTO_SEND_ENABLED` | If true, send without approval (default false) |
| `REENGAGEMENT_COOLDOWN_DAYS` | Days between outreach to same company |

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Deliverables

- [README.md](README.md) (this file)
- [Architecture](docs/architecture.md) (1-2 pages, export to PDF)
- [Sample Inputs/Outputs](docs/sample_inputs_outputs.md)
