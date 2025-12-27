"""
Sago Re-Engagement Agent

A system for automated investor re-engagement based on company signals.
"""

from sago.models import (
    Signal,
    SignalType,
    SignalSource,
    Company,
    Interaction,
    UserProfile,
    PlannedAction,
    ActionType,
    ChannelType,
    ReengagementPlan,
)
from sago.agent import (
    ReengagementAgent,
    SignalFilter,
    Policy,
    ActionPlanner,
    OutreachGenerator,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "Signal",
    "SignalType",
    "SignalSource",
    "Company",
    "Interaction",
    "UserProfile",
    "PlannedAction",
    "ActionType",
    "ChannelType",
    "ReengagementPlan",
    # Agent
    "ReengagementAgent",
    "SignalFilter",
    "Policy",
    "ActionPlanner",
    "OutreachGenerator",
]
