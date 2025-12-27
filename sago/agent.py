"""
Core agent logic: signal filtering, policy decisions, action planning, outreach generation.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import asdict
from functools import lru_cache

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
        now = datetime.utcnow()
        return sorted(
            signals,
            key=lambda s: self._score_signal(s, now),
            reverse=True
        )
    
    @staticmethod
    def _score_signal(signal: Signal, now: datetime) -> float:
        """Calculate priority score for a signal."""
        type_weight = SignalFilter.TYPE_PRIORITY.get(signal.signal_type, 0.5)
        days_old = (now - signal.detected_at).days
        recency = max(0, 1 - days_old / 30)
        return signal.confidence * type_weight * 0.7 + recency * 0.3


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
        trigger_words = set(trigger.lower().split())
        signal_text = " ".join(
            [f"{s.title} {s.description}".lower() for s in signals]
        )
        matched = sum(1 for w in trigger_words if w in signal_text)
        min_required = max(1, len(trigger_words) // 2)
        return matched >= min_required


class ActionPlanner:
    """Plans concrete actions based on signals."""

    def plan(self, signals: List[Signal], company_id: str) -> List[PlannedAction]:
        """Generate action plan from signals."""
        actions = []
        signal_ids = [s.id for s in signals]
        signal_by_type = self._group_signals_by_type(signals)

        # Primary: outreach email
        actions.append(
            PlannedAction(
                action_type=ActionType.SEND_EMAIL,
                company_id=company_id,
                description="Draft personalized re-engagement email",
                signal_ids=signal_ids,
                requires_approval=True,
            )
        )

        # Secondary actions based on signal type
        for signal_type, type_signals in signal_by_type.items():
            action = self._create_action_for_type(signal_type, company_id, type_signals)
            if action:
                actions.append(action)

        # Always log to CRM
        actions.append(
            PlannedAction(
                action_type=ActionType.LOG_TO_CRM,
                company_id=company_id,
                description="Record signals and outreach in CRM",
                signal_ids=signal_ids,
                requires_approval=False,
            )
        )

        return actions
    
    @staticmethod
    def _group_signals_by_type(signals: List[Signal]) -> Dict[SignalType, List[Signal]]:
        """Group signals by type."""
        grouped: Dict[SignalType, List[Signal]] = {}
        for signal in signals:
            if signal.signal_type not in grouped:
                grouped[signal.signal_type] = []
            grouped[signal.signal_type].append(signal)
        return grouped
    
    @staticmethod
    def _create_action_for_type(signal_type: SignalType, company_id: str, signals: List[Signal]) -> Optional[PlannedAction]:
        """Create an action based on signal type."""
        signal_ids = [s.id for s in signals]
        titles = ", ".join(s.title for s in signals[:2])
        
        if signal_type == SignalType.NEED:
            return PlannedAction(
                action_type=ActionType.SHARE_RESOURCE,
                company_id=company_id,
                description=f"Share resource (triggered by: {titles})",
                signal_ids=signal_ids,
                requires_approval=False,
            )
        elif signal_type == SignalType.HIRING:
            return PlannedAction(
                action_type=ActionType.REQUEST_INTRO,
                company_id=company_id,
                description=f"Offer candidate intros (triggered by: {titles})",
                signal_ids=signal_ids,
                requires_approval=True,
            )
        elif signal_type == SignalType.RISK:
            return PlannedAction(
                action_type=ActionType.FLAG_FOR_REVIEW,
                company_id=company_id,
                description=f"Flag for review (triggered by: {titles})",
                signal_ids=signal_ids,
                requires_approval=False,
            )
        return None


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
        signals_text = self._format_signals(signals)
        thesis = self._format_thesis(user)
        availability = self._format_availability(user)

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
    
    @staticmethod
    def _format_signals(signals: List[Signal]) -> str:
        """Format signals into readable list."""
        return "\n".join(f"  - {s.title}" for s in signals[:3])
    
    @staticmethod
    def _format_thesis(user: UserProfile) -> str:
        """Format investor thesis keywords."""
        return ", ".join(user.thesis_keywords[:3]) if user.thesis_keywords else "our focus areas"
    
    @staticmethod
    def _format_availability(user: UserProfile) -> str:
        """Format availability slots."""
        return " or ".join(user.availability_slots[:2]) if user.availability_slots else "this week"


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
