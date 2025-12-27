# System Architecture

## Overview

The Sago Re-Engagement Agent monitors investor communication channels (Gmail, Slack) for signals that indicate a previously-passed startup is ready for re-engagement. When the right signals appear, it generates personalized outreach and executes follow-up actions.

## Design Goals

1. **Seamless Integration**: No new apps. The agent reads from Gmail/Slack and writes back to the same channels.
2. **Hyper-Personalization**: Every decision uses user thesis, prior interaction notes, and communication preferences.
3. **True Agency**: Beyond alerts, the system drafts emails, shares resources, and logs to CRM.

## High-Level Architecture

```
+------------------+     +------------------+
|   Gmail API      |     |   Slack API      |
|   (Push/Poll)    |     |   (Events API)   |
+--------+---------+     +--------+---------+
         |                        |
         v                        v
+-------------------------------------------+
|           INGESTION LAYER                 |
|  - Normalize events                       |
|  - Deduplicate by content hash            |
|  - Extract company via NER / domain match |
+-------------------------------------------+
                   |
                   v
+-------------------------------------------+
|           SIGNAL DETECTOR                 |
|  - LLM classification (GPT-4 / Claude)    |
|  - Output: signal type + confidence       |
|  - Persist to Postgres + embed to pgvector|
+-------------------------------------------+
                   |
                   v
+-------------------------------------------+
|           POLICY ENGINE                   |
|  - Check confidence threshold             |
|  - Match against follow-up trigger        |
|  - Enforce cooldown period                |
+-------------------------------------------+
                   |
                   v
+-------------------------------------------+
|           ORCHESTRATOR                    |
|  - Retrieve user profile + last notes     |
|  - Prioritize signals                     |
|  - Generate outreach via LLM              |
|  - Plan actions (email, DM, CRM, intros)  |
+-------------------------------------------+
                   |
                   v
+-------------------------------------------+
|           EXECUTORS                       |
|  - Gmail: create draft or send            |
|  - Slack: DM or thread reply              |
|  - CRM: log via webhook                   |
|  - Human approval queue (optional)        |
+-------------------------------------------+
```

## Component Details

### Connectors (`sago/connectors/`)
Abstract `BaseConnector` defines the interface. Implementations for Gmail and Slack handle:
- OAuth token management and refresh
- Fetching messages since a timestamp
- Sending messages or creating drafts
- Health checks and reconnection

### Models (`sago/models.py`)
Pydantic models for domain objects:
- `Signal`: typed (traction, hiring, need, risk), scored (0-1), embedded
- `Interaction`: past meeting with notes, outcome, follow-up trigger
- `UserProfile`: thesis, tone, availability, preferred channels
- `PlannedAction`: what to do, approval status, execution result

### Database (`sago/database.py`)
SQLAlchemy ORM with:
- PostgreSQL for structured data
- pgvector extension for semantic search on embeddings
- Indexes for fast lookups by company, user, and recency

### LLM Layer (`sago/llm.py`)
- Signal detection: extract structured signals from raw text
- Outreach generation: personalized message grounded in context
- Embedding: for semantic search and similarity matching
- Retry logic and token counting

### Agent (`sago/agent.py`)
Core orchestration:
- `ReengagementPolicy`: decision rules (threshold, cooldown, trigger match)
- `ReengagementOrchestrator`: coordinates evaluation and execution
- `SignalRepository` / `InteractionRepository`: data access

### Pipeline (`sago/pipeline.py`)
- `EventProcessor`: dedupe, extract company, call LLM, persist signals
- `IngestionPipeline`: fetch from all connectors, process in batch

### Tasks (`sago/tasks.py`)
Celery tasks for async processing:
- `ingest_all_sources`: hourly batch fetch
- `evaluate_all_companies`: daily re-engagement sweep
- `process_single_event`: real-time webhook handler
- `execute_approved_plan`: post-approval execution

## Data Flow Example

1. **Gmail receives an email** from a founder with subject "Update: closed Fortune 100 pilot".
2. **Webhook triggers** `process_single_event` task.
3. **Event processor** normalizes content, matches sender domain to company "Northwind AI".
4. **Signal detector** calls GPT-4, extracts `{type: traction, confidence: 0.88, title: "Fortune 100 pilot secured"}`.
5. **Policy engine** checks: confidence > 0.6 (yes), matches follow-up trigger "enterprise pilot" (yes), cooldown passed (yes).
6. **Orchestrator** retrieves user profile and last interaction notes.
7. **LLM generates outreach**: references prior meeting, highlights signal, offers help.
8. **Planner** queues actions: draft email, attach SOC2 template, log to CRM.
9. **Executor** creates Gmail draft (pending approval) and logs to CRM (auto).
10. **User approves** in Gmail, email is sent.

## Key Design Decisions

### Why Gmail + Slack first?
These are where investors already live. No new app to install. The agent becomes a layer on top of existing workflow.

### Why LLM for signal detection?
Rule-based systems miss nuance. LLMs can understand context ("we just signed our first enterprise pilot" means traction) and assign calibrated confidence.

### Why human-in-the-loop by default?
Trust is earned. Initially, all outreach requires approval. Per-company or per-user auto-send can be enabled once accuracy is proven.

### Why pgvector?
Semantic search lets the agent find relevant past interactions even when exact keywords do not match. "We closed a Fortune 100" should match "enterprise pilot landed".

### Why Celery?
Async processing handles webhook spikes, retries failures, and decouples ingestion from evaluation. Beat scheduler runs periodic sweeps.

## Extensibility

- **Additional connectors**: Twitter, LinkedIn, news feeds, Crunchbase
- **Calendar integration**: pull real availability from Google Calendar
- **CRM sync**: bidirectional sync with Affinity, Attio, or HubSpot
- **Multi-user**: workspace-level settings with per-user overrides

## Infrastructure

- **PostgreSQL + pgvector**: structured data and embeddings
- **Redis**: Celery broker and result backend
- **Docker Compose**: local development stack
- **Environment variables**: secrets and tunable parameters
