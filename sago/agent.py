"""
Core agent logic: signal filtering, policy decisions, action planning, outreach generation.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import asdict

from sago.models import (
    Signal,
    SignalType,
    Interaction,
    UserProfile,
    Company,
    PlannedAction,
    ActionType,
    ReengagementPlan,
)


class SignalFilter:
    """Filters and prioritizes signals based on confidence and type."""

    TYPE_PRIORITY = {
        SignalType.TRACTION: 1.0,
        SignalType.FUNDING: 0.9,
        SignalType.NEED: 0.85,
        SignalType.PRODUCT_LAUNCH: 0.8,
        SignalType.PARTNERSHIP: 0.75,
        SignalType.HIRING: 0.7,
        SignalType.EXECUTIVE_CHANGE: 0.6,
        SignalType.RISK: 0.3,
    }

    def filter_actionable(
        self, signals: List[Signal], threshold: float = 0.6
    ) -> List[Signal]:
        """Keep only signals above confidence threshold, excluding risk signals."""
        return [s for s in signals if s.is_actionable(threshold)]

    def prioritize(self, signals: List[Signal]) -> List[Signal]:
        """Rank signals by type priority and confidence."""

        def score(s: Signal) -> float:
            type_weight = self.TYPE_PRIORITY.get(s.signal_type, 0.5)
            days_old = (datetime.utcnow() - s.detected_at).days
            recency = max(0, 1 - days_old / 30)
            return s.confidence * type_weight * 0.7 + recency * 0.3

        return sorted(signals, key=score, reverse=True)


class Policy:
    """Decision engine for when to re-engage."""

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        cooldown_days: int = 14,
    ):
        self.confidence_threshold = confidence_threshold
        self.cooldown_days = cooldown_days
        self.filter = SignalFilter()

    def should_reengage(
        self,
        signals: List[Signal],
        last_interaction: Optional[Interaction],
    ) -> Tuple[bool, str]:
        """Decide whether re-engagement is warranted."""

        # Check for actionable signals
        actionable = self.filter.filter_actionable(signals, self.confidence_threshold)
        if not actionable:
            return False, "No signals above confidence threshold"

        # Check cooldown
        if last_interaction:
            days_since = (datetime.utcnow() - last_interaction.occurred_at).days
            if days_since < self.cooldown_days:
                return False, f"Within {self.cooldown_days}-day cooldown period"

        # Check trigger match
        if last_interaction and last_interaction.follow_up_trigger:
            if not self._matches_trigger(actionable, last_interaction.follow_up_trigger):
                return False, "Signals do not match agreed follow-up trigger"

        return True, f"Found {len(actionable)} actionable signals"

    def _matches_trigger(self, signals: List[Signal], trigger: str) -> bool:
        """Check if any signal matches the follow-up trigger."""
        trigger_words = trigger.lower().split()
        signal_text = " ".join(
            [f"{s.title} {s.description}".lower() for s in signals]
        )
        matched = sum(1 for w in trigger_words if w in signal_text)
        return matched >= len(trigger_words) // 2


class ActionPlanner:
    """Plans concrete actions based on signals."""

    def plan(self, signals: List[Signal], company_id: str) -> List[PlannedAction]:
        """Generate action plan from signals."""
        actions = []

        # Primary: outreach email
        actions.append(
            PlannedAction(
                action_type=ActionType.SEND_EMAIL,
                company_id=company_id,
                description="Draft personalized re-engagement email",
                signal_ids=[s.id for s in signals],
                requires_approval=True,
            )
        )

        # Secondary actions based on signal type
        for signal in signals:
            if signal.signal_type == SignalType.NEED:
                actions.append(
                    PlannedAction(
                        action_type=ActionType.SHARE_RESOURCE,
                        company_id=company_id,
                        description=f"Share resource (triggered by: {signal.title})",
                        signal_ids=[signal.id],
                        requires_approval=False,
                    )
                )
            elif signal.signal_type == SignalType.HIRING:
                actions.append(
                    PlannedAction(
                        action_type=ActionType.REQUEST_INTRO,
                        company_id=company_id,
                        description=f"Offer candidate intros (triggered by: {signal.title})",
                        signal_ids=[signal.id],
                        requires_approval=True,
                    )
                )
            elif signal.signal_type == SignalType.RISK:
                actions.append(
                    PlannedAction(
                        action_type=ActionType.FLAG_FOR_REVIEW,
                        company_id=company_id,
                        description=f"Flag for review (triggered by: {signal.title})",
                        signal_ids=[signal.id],
                        requires_approval=False,
                    )
                )

        # Always log to CRM
        actions.append(
            PlannedAction(
                action_type=ActionType.LOG_TO_CRM,
                company_id=company_id,
                description="Record signals and outreach in CRM",
                signal_ids=[s.id for s in signals],
                requires_approval=False,
            )
        )

        return actions


class OutreachGenerator:
    """Generates personalized outreach messages."""

    def generate(
        self,
        company: Company,
        signals: List[Signal],
        user: UserProfile,
        last_interaction: Optional[Interaction],
    ) -> str:
        """Generate personalized re-engagement message."""

        # Build signal summary
        signal_lines = [f"  - {s.title}" for s in signals[:3]]
        signals_text = "\n".join(signal_lines)

        # Extract context
        thesis = ", ".join(user.thesis_keywords[:3])
        availability = " or ".join(user.availability_slots[:2]) if user.availability_slots else "this week"

        # Reference past interaction
        past_context = ""
        if last_interaction and last_interaction.notes:
            past_context = last_interaction.notes.split(".")[0]

        message = f"""Hi {company.name} team,

Hope you are well. We chatted previously and I mentioned I would love to reconnect once you hit some key milestones. Looks like things are moving.

I noticed a few updates:
{signals_text}

This caught my attention since it aligns with what we look for around {thesis}. Congratulations on the progress.

If it would be helpful, happy to share resources or connect you with folks from our portfolio who have navigated similar stages.

I have time {availability} if you want to catch up. Let me know what works.

Best,
{user.name}"""

        return message


class ReengagementAgent:
    """Main orchestrator that ties everything together."""

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        cooldown_days: int = 14,
    ):
        self.policy = Policy(confidence_threshold, cooldown_days)
        self.planner = ActionPlanner()
        self.generator = OutreachGenerator()
        self.filter = SignalFilter()

    def evaluate(
        self,
        user: UserProfile,
        company: Company,
        signals: List[Signal],
        last_interaction: Optional[Interaction],
    ) -> Optional[ReengagementPlan]:
        """Evaluate whether to re-engage and build a plan if warranted."""

        # Check policy
        should_engage, reason = self.policy.should_reengage(signals, last_interaction)

        if not should_engage:
            return None

        # Filter and prioritize signals
        actionable = self.filter.filter_actionable(
            signals, self.policy.confidence_threshold
        )
        prioritized = self.filter.prioritize(actionable)

        # Generate outreach
        outreach = self.generator.generate(
            company, prioritized, user, last_interaction
        )

        # Plan actions
        actions = self.planner.plan(prioritized, company.id)

        # Attach outreach to primary action
        for action in actions:
            if action.action_type == ActionType.SEND_EMAIL:
                action.content = outreach

        # Build plan
        plan = ReengagementPlan(
            user_id=user.id,
            company_id=company.id,
            signals=prioritized,
            actions=actions,
            outreach_message=outreach,
            reasoning=reason,
            confidence=max(s.confidence for s in prioritized),
        )

        return plan

    def to_dict(self, plan: ReengagementPlan) -> Dict[str, Any]:
        """Convert plan to dictionary for JSON output."""
        return {
            "company_id": plan.company_id,
            "should_reengage": True,
            "reason": plan.reasoning,
            "confidence": plan.confidence,
            "signals_used": [
                {
                    "type": s.signal_type.value,
                    "title": s.title,
                    "confidence": s.confidence,
                    "source": s.source.value,
                }
                for s in plan.signals
            ],
            "actions": [
                {
                    "type": a.action_type.value,
                    "description": a.description,
                    "requires_approval": a.requires_approval,
                }
                for a in plan.actions
            ],
            "outreach_message": plan.outreach_message,
        }
