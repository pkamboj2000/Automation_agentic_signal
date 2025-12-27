"""
Unit tests for the Sago Re-Engagement Agent.
"""

import pytest
from datetime import datetime, timedelta

from sago.models import Signal, SignalType, SignalSource, Interaction, UserProfile, Company
from sago.agent import SignalFilter, Policy, ActionPlanner, ReengagementAgent


class TestSignalFilter:
    def test_filter_actionable_keeps_high_confidence(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.TRACTION,
                source=SignalSource.GMAIL,
                title="Test",
                description="Desc",
                evidence="Evidence",
                confidence=0.8,
            ),
            Signal(
                company_id="c1",
                signal_type=SignalType.HIRING,
                source=SignalSource.SLACK,
                title="Hiring",
                description="Desc",
                evidence="Evidence",
                confidence=0.4,
            ),
        ]

        f = SignalFilter()
        result = f.filter_actionable(signals, threshold=0.6)

        assert len(result) == 1
        assert result[0].signal_type == SignalType.TRACTION

    def test_filter_excludes_risk_signals(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.RISK,
                source=SignalSource.NEWS,
                title="Risk",
                description="Desc",
                evidence="Evidence",
                confidence=0.9,
            ),
        ]

        f = SignalFilter()
        result = f.filter_actionable(signals)

        assert len(result) == 0

    def test_prioritize_orders_by_type_and_confidence(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.HIRING,
                source=SignalSource.COMPANY_SITE,
                title="Hiring",
                description="Desc",
                evidence="Evidence",
                confidence=0.9,
            ),
            Signal(
                company_id="c1",
                signal_type=SignalType.TRACTION,
                source=SignalSource.LINKEDIN,
                title="Traction",
                description="Desc",
                evidence="Evidence",
                confidence=0.8,
            ),
        ]

        f = SignalFilter()
        result = f.prioritize(signals)

        # Traction has higher type priority even with lower confidence
        assert result[0].signal_type == SignalType.TRACTION


class TestPolicy:
    def test_should_reengage_with_actionable_signals(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.TRACTION,
                source=SignalSource.GMAIL,
                title="Pilot secured",
                description="Fortune 100",
                evidence="Email",
                confidence=0.85,
            ),
        ]

        policy = Policy()
        should, reason = policy.should_reengage(signals, None)

        assert should is True
        assert "actionable" in reason.lower()

    def test_should_not_reengage_below_threshold(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.TRACTION,
                source=SignalSource.GMAIL,
                title="Minor update",
                description="Small news",
                evidence="Email",
                confidence=0.3,
            ),
        ]

        policy = Policy(confidence_threshold=0.6)
        should, reason = policy.should_reengage(signals, None)

        assert should is False

    def test_respects_cooldown_period(self):
        signals = [
            Signal(
                company_id="c1",
                signal_type=SignalType.TRACTION,
                source=SignalSource.GMAIL,
                title="Big news",
                description="Major",
                evidence="Email",
                confidence=0.9,
            ),
        ]

        recent_interaction = Interaction(
            user_id="u1",
            company_id="c1",
            interaction_type="email",
            occurred_at=datetime.utcnow() - timedelta(days=5),
            summary="Last outreach",
        )

        policy = Policy(cooldown_days=14)
        should, reason = policy.should_reengage(signals, recent_interaction)

        assert should is False
        assert "cooldown" in reason.lower()


class TestReengagementAgent:
    def test_evaluate_returns_plan_when_warranted(self):
        user = UserProfile(
            name="Alex Chen",
            email="alex@vc.com",
            thesis_keywords=["product-led", "compliance"],
            availability_slots=["Tuesday 10am"],
        )

        company = Company(name="Northwind AI", sector="AI")

        signals = [
            Signal(
                company_id=company.id,
                signal_type=SignalType.TRACTION,
                source=SignalSource.LINKEDIN,
                title="Fortune 100 pilot",
                description="Secured enterprise pilot",
                evidence="LinkedIn post",
                confidence=0.88,
            ),
        ]

        agent = ReengagementAgent()
        plan = agent.evaluate(user, company, signals, None)

        assert plan is not None
        assert len(plan.actions) > 0
        assert "Northwind" in plan.outreach_message

    def test_evaluate_returns_none_when_not_warranted(self):
        user = UserProfile(name="Alex", email="alex@vc.com")
        company = Company(name="TestCo")
        signals = []

        agent = ReengagementAgent()
        plan = agent.evaluate(user, company, signals, None)

        assert plan is None
