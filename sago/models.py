"""
Domain models for the Sago Re-Engagement Agent.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import uuid


class SignalType(str, Enum):
    TRACTION = "traction"
    HIRING = "hiring"
    FUNDING = "funding"
    PARTNERSHIP = "partnership"
    PRODUCT_LAUNCH = "product_launch"
    NEED = "need"
    RISK = "risk"
    EXECUTIVE_CHANGE = "executive_change"


class SignalSource(str, Enum):
    GMAIL = "gmail"
    SLACK = "slack"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    NEWS = "news"
    CRUNCHBASE = "crunchbase"
    COMPANY_SITE = "company_site"
    MANUAL = "manual"


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    SEND_SLACK_DM = "send_slack_dm"
    CREATE_DRAFT = "create_draft"
    SCHEDULE_REMINDER = "schedule_reminder"
    LOG_TO_CRM = "log_to_crm"
    SHARE_RESOURCE = "share_resource"
    REQUEST_INTRO = "request_intro"
    FLAG_FOR_REVIEW = "flag_for_review"


class ChannelType(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


@dataclass
class Company:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: Optional[str] = None
    sector: Optional[str] = None
    stage: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Signal:
    company_id: str
    signal_type: SignalType
    source: SignalSource
    title: str
    description: str
    evidence: str
    confidence: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_url: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None

    def is_actionable(self, threshold: float = 0.6) -> bool:
        return self.confidence >= threshold and self.signal_type != SignalType.RISK


@dataclass
class Interaction:
    user_id: str
    company_id: str
    interaction_type: str
    occurred_at: datetime
    summary: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_trigger: Optional[str] = None
    topics_discussed: List[str] = field(default_factory=list)


@dataclass
class UserProfile:
    name: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fund_name: Optional[str] = None
    fund_focus: List[str] = field(default_factory=list)
    thesis_keywords: List[str] = field(default_factory=list)
    communication_tone: str = "professional"
    availability_slots: List[str] = field(default_factory=list)
    preferred_channels: List[ChannelType] = field(default_factory=list)


@dataclass
class PlannedAction:
    action_type: ActionType
    company_id: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_ids: List[str] = field(default_factory=list)
    channel: Optional[ChannelType] = None
    content: Optional[str] = None
    requires_approval: bool = True
    executed: bool = False


@dataclass
class ReengagementPlan:
    user_id: str
    company_id: str
    signals: List[Signal]
    actions: List[PlannedAction]
    outreach_message: str
    reasoning: str
    confidence: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved: bool = False
    executed: bool = False
