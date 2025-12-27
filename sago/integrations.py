"""
External integrations: Gmail, Slack, LLM, and database connectors.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
import asyncio
import json

from sago.models import Signal, SignalType, SignalSource


# =============================================================================
# Base Connector Interface
# =============================================================================

class BaseConnector(ABC):
    """Abstract base class for all external service connectors."""

    source: SignalSource

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def fetch_messages(self, since: Optional[datetime] = None) -> List[Dict]:
        pass

    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> Dict:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass


# =============================================================================
# Gmail Connector
# =============================================================================

class GmailConnector(BaseConnector):
    """Gmail API connector for reading emails and sending drafts."""

    source = SignalSource.GMAIL

    def __init__(self, credentials):
        self.credentials = credentials
        self.service = None
        self._user_email = None

    async def connect(self) -> None:
        """Build Gmail API service."""
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        if self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())

        self.service = build("gmail", "v1", credentials=self.credentials)
        profile = self.service.users().getProfile(userId="me").execute()
        self._user_email = profile.get("emailAddress")

    async def disconnect(self) -> None:
        self.service = None

    async def health_check(self) -> bool:
        if not self.service:
            return False
        try:
            self.service.users().getProfile(userId="me").execute()
            return True
        except Exception:
            return False

    async def fetch_messages(self, since: Optional[datetime] = None) -> List[Dict]:
        """Fetch recent emails."""
        if not self.service:
            raise RuntimeError("Not connected")

        query = "is:inbox"
        if since:
            query += f" after:{int(since.timestamp())}"

        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=50
        ).execute()

        messages = []
        for msg_meta in results.get("messages", []):
            msg = self.service.users().messages().get(
                userId="me", id=msg_meta["id"], format="metadata"
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            messages.append({
                "id": msg["id"],
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
            })

        return messages

    async def send_message(self, recipient: str, content: str) -> Dict:
        """Create a draft email."""
        import base64
        from email.mime.text import MIMEText

        if not self.service:
            raise RuntimeError("Not connected")

        message = MIMEText(content)
        message["to"] = recipient
        message["from"] = self._user_email
        message["subject"] = "Following up"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = self.service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

        return {"type": "draft", "id": draft["id"]}


# =============================================================================
# Slack Connector
# =============================================================================

class SlackConnector(BaseConnector):
    """Slack API connector for reading messages and sending DMs."""

    source = SignalSource.SLACK

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.client = None
        self._bot_user_id = None

    async def connect(self) -> None:
        from slack_sdk import WebClient

        self.client = WebClient(token=self.bot_token)
        auth = self.client.auth_test()
        self._bot_user_id = auth["user_id"]

    async def disconnect(self) -> None:
        self.client = None

    async def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.auth_test()
            return True
        except Exception:
            return False

    async def fetch_messages(self, since: Optional[datetime] = None) -> List[Dict]:
        """Fetch messages from channels."""
        if not self.client:
            raise RuntimeError("Not connected")

        oldest = str(since.timestamp()) if since else "0"
        channels = self.client.conversations_list(types="public_channel", limit=50)

        messages = []
        for channel in channels.get("channels", []):
            if not channel.get("is_member"):
                continue
            history = self.client.conversations_history(
                channel=channel["id"], oldest=oldest, limit=20
            )
            for msg in history.get("messages", []):
                if not msg.get("subtype"):
                    messages.append({
                        "channel": channel["name"],
                        "user": msg.get("user"),
                        "text": msg.get("text", ""),
                        "ts": msg["ts"],
                    })

        return messages

    async def send_message(self, recipient: str, content: str) -> Dict:
        """Send a DM."""
        if not self.client:
            raise RuntimeError("Not connected")

        if recipient.startswith("U"):
            dm = self.client.conversations_open(users=[recipient])
            channel_id = dm["channel"]["id"]
        else:
            channel_id = recipient

        response = self.client.chat_postMessage(channel=channel_id, text=content)
        return {"channel": channel_id, "ts": response["ts"]}


# =============================================================================
# LLM Client for Signal Detection
# =============================================================================

class LLMClient:
    """Wrapper for OpenAI/Anthropic API calls."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key
        self.model = model

    async def detect_signals(self, text: str, company: str) -> List[Signal]:
        """Use LLM to extract signals from text."""
        import openai

        client = openai.AsyncOpenAI(api_key=self.api_key)

        system = """Extract business signals from text. Return JSON list with:
- signal_type: traction, hiring, funding, need, risk, product_launch
- title: brief headline
- description: 1-2 sentences
- evidence: quote from text
- confidence: 0.0 to 1.0

Return [] if no signals found."""

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Company: {company}\n\nText:\n{text}"},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        content = self._extract_json_from_response(content)
        return self._parse_signals_from_json(content, company)

    async def generate_outreach(
        self,
        company: str,
        signals: List[Signal],
        notes: str,
        thesis: List[str],
        availability: List[str],
    ) -> str:
        """Generate personalized outreach using LLM."""
        import openai

        client = openai.AsyncOpenAI(api_key=self.api_key)

        prompt = self._build_outreach_prompt(company, signals, notes, thesis, availability)

        response = await client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()
    
    @staticmethod
    def _extract_json_from_response(content: str) -> str:
        """Extract JSON from LLM response."""
        if "```json" in content:
            return content.split("```json")[1].split("```")[0]
        elif "```" in content:
            return content.split("```")[1].split("```")[0]
        return content
    
    @staticmethod
    def _parse_signals_from_json(content: str, company: str) -> List[Signal]:
        """Parse signals from JSON string."""
        try:
            data = json.loads(content.strip())
            return [
                Signal(
                    company_id="",
                    signal_type=SignalType(s["signal_type"]),
                    source=SignalSource.MANUAL,
                    title=s["title"],
                    description=s["description"],
                    evidence=s["evidence"],
                    confidence=float(s["confidence"]),
                )
                for s in data
            ]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []
    
    @staticmethod
    def _build_outreach_prompt(
        company: str,
        signals: List[Signal],
        notes: str,
        thesis: List[str],
        availability: List[str],
    ) -> str:
        """Build the outreach generation prompt."""
        signals_text = "\n".join([f"- {s.title}: {s.description}" for s in signals])
        thesis_text = ", ".join(thesis) if thesis else "our focus"
        avail_text = ", ".join(availability) if availability else "this week"

        return f"""Write a re-engagement email to {company}.

Previous notes: {notes}

New signals:
{signals_text}

Investor thesis: {thesis_text}
Availability: {avail_text}

Write concisely (under 150 words), reference past conversation, highlight new signals, offer help."""
