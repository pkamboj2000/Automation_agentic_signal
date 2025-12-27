"""
Demo script showing the re-engagement agent workflow.
Run with: python examples/demo.py
"""

import json
from datetime import datetime

from sago import (
    Signal,
    SignalType,
    SignalSource,
    Company,
    Interaction,
    UserProfile,
    ReengagementAgent,
)


# =============================================================================
# Sample Data
# =============================================================================

USER = UserProfile(
    id="user_001",
    name="Alex Chen",
    email="alex@sagovc.com",
    fund_name="Sago Ventures",
    fund_focus=["B2B SaaS", "Fintech", "Infrastructure"],
    thesis_keywords=["usage growth", "product-led", "efficient acquisition", "compliance automation"],
    communication_tone="concise, direct, founder-friendly",
    availability_slots=["Tuesday 10am-1pm PT", "Thursday 8am-12pm PT"],
)

COMPANY = Company(
    id="company_001",
    name="Northwind AI",
    domain="northwind.ai",
    sector="AI/ML",
    stage="Seed",
)

PAST_INTERACTION = Interaction(
    id="interaction_001",
    user_id="user_001",
    company_id="company_001",
    interaction_type="first_meeting",
    occurred_at=datetime(2025, 9, 10, 10, 0, 0),
    summary="Initial meeting with Northwind AI founding team.",
    notes="Team is strong (ex-Google, ex-Stripe). Product is pre-PMF, focused on compliance automation using LLMs. Too early for current fund stage requirements. Agreed to reconnect when they secure first enterprise pilot.",
    outcome="pass_for_now",
    follow_up_trigger="enterprise pilot secured",
    topics_discussed=["compliance automation", "LLM hallucination handling", "GTM timing"],
)

SIGNALS = [
    Signal(
        id="signal_001",
        company_id="company_001",
        signal_type=SignalType.TRACTION,
        source=SignalSource.LINKEDIN,
        title="Fortune 100 design partner announced",
        description="CEO posted about securing their first enterprise pilot with a major financial services company.",
        evidence="LinkedIn post dated 2025-12-01: 'Thrilled to announce our design partnership with [Fortune 100 bank]. Compliance automation at scale.'",
        confidence=0.88,
        detected_at=datetime(2025, 12, 1, 14, 0, 0),
    ),
    Signal(
        id="signal_002",
        company_id="company_001",
        signal_type=SignalType.NEED,
        source=SignalSource.SLACK,
        title="SOC2 readiness help requested",
        description="Founder asked for SOC2 templates in portfolio Slack channel.",
        evidence="Slack message in #founders: 'Does anyone have a good SOC2 readiness checklist? Enterprise buyer asking about our security posture.'",
        confidence=0.75,
        detected_at=datetime(2025, 12, 18, 9, 30, 0),
    ),
    Signal(
        id="signal_003",
        company_id="company_001",
        signal_type=SignalType.HIRING,
        source=SignalSource.COMPANY_SITE,
        title="First sales leadership hire",
        description="Company posted Head of Sales role indicating GTM ramp.",
        evidence="Careers page job posting for 'Head of Sales - Enterprise' with focus on financial services.",
        confidence=0.68,
        detected_at=datetime(2025, 12, 15, 0, 0, 0),
    ),
]


# =============================================================================
# Main Demo
# =============================================================================

def main():
    print("=" * 60)
    print("SAGO RE-ENGAGEMENT AGENT DEMO")
    print("=" * 60)
    print()

    print("1. INPUTS")
    print("-" * 40)
    print(f"User: {USER.name} ({USER.fund_name})")
    print(f"Company: {COMPANY.name} ({COMPANY.sector}, {COMPANY.stage})")
    print(f"Past outcome: {PAST_INTERACTION.outcome}")
    print(f"Follow-up trigger: \"{PAST_INTERACTION.follow_up_trigger}\"")
    print(f"Signals detected: {len(SIGNALS)}")
    print()

    print("2. SIGNAL ANALYSIS")
    print("-" * 40)
    for s in SIGNALS:
        print(f"  [{s.signal_type.value.upper()}] {s.title}")
        print(f"     Confidence: {s.confidence:.0%} | Source: {s.source.value}")
    print()

    print("3. EVALUATION")
    print("-" * 40)

    agent = ReengagementAgent(confidence_threshold=0.6, cooldown_days=14)
    plan = agent.evaluate(USER, COMPANY, SIGNALS, PAST_INTERACTION)

    if plan:
        print(f"Should re-engage: True")
        print(f"Reason: {plan.reasoning}")
        print()

        print("4. PLANNED ACTIONS")
        print("-" * 40)
        for i, action in enumerate(plan.actions, 1):
            approval = "(needs approval)" if action.requires_approval else "(auto)"
            print(f"  {i}. {action.description} {approval}")
        print()

        print("5. GENERATED OUTREACH")
        print("-" * 40)
        print(plan.outreach_message)
        print()

        print("=" * 60)
        print("JSON OUTPUT:")
        print(json.dumps(agent.to_dict(plan), indent=2))
    else:
        print("Should re-engage: False")

    print("=" * 60)
    print("END OF DEMO")
    print("=" * 60)


if __name__ == "__main__":
    main()
