"""
Calendar MCP — Tools for reading Google Calendar events.

Requires OAuth setup:
1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create OAuth 2.0 Desktop credentials
4. Download credentials.json to config/google_credentials.json

On first use, a browser window opens for authorization.
The token is saved to config/google_token.json for future use.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Paths for Google OAuth files
CREDENTIALS_PATH = Path("config/google_credentials.json")
TOKEN_PATH = Path("config/google_token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _get_calendar_service():
    """
    Build and return an authenticated Google Calendar service.

    On first run, opens a browser for OAuth consent.
    Subsequent runs use the saved token.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        return None, "Google API libraries not installed. Run: uv add google-api-python-client google-auth-oauthlib"

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not CREDENTIALS_PATH.exists():
                return None, (
                    f"Google credentials not found at {CREDENTIALS_PATH.resolve()}. "
                    "Download from Google Cloud Console > APIs > Credentials > OAuth 2.0 Client IDs"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service, None


def get_upcoming_events(max_results: int = 10, days_ahead: int = 7) -> list[dict[str, Any]]:
    """
    Get upcoming calendar events.

    Args:
        max_results: Maximum events to return.
        days_ahead: How many days ahead to look.

    Returns:
        List of event dicts with summary, start, end, location, description.
    """
    service, error = _get_calendar_service()
    if error:
        return [{"error": error}]

    now = datetime.now(timezone.utc)
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for event in result.get("items", []):
            events.append({
                "summary": event.get("summary", "(No title)"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "location": event.get("location", ""),
                "description": event.get("description", "")[:200],
                "link": event.get("htmlLink", ""),
                "status": event.get("status", ""),
            })
        return events

    except Exception as e:
        return [{"error": f"Failed to fetch events: {e}"}]


def get_todays_schedule() -> list[dict[str, Any]]:
    """Get all events for today."""
    return get_upcoming_events(max_results=20, days_ahead=1)


def search_events(query: str, days_back: int = 30, max_results: int = 20) -> list[dict[str, Any]]:
    """
    Search calendar events by keyword.

    Args:
        query: Search term.
        days_back: How many days back to search.
        max_results: Maximum results.

    Returns:
        List of matching events.
    """
    service, error = _get_calendar_service()
    if error:
        return [{"error": error}]

    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat() + "Z"
    time_max = (now + timedelta(days=7)).isoformat() + "Z"

    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
            q=query,
        ).execute()

        events = []
        for event in result.get("items", []):
            events.append({
                "summary": event.get("summary", "(No title)"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "location": event.get("location", ""),
                "description": event.get("description", "")[:200],
            })
        return events

    except Exception as e:
        return [{"error": f"Search failed: {e}"}]


def list_calendars() -> list[dict[str, Any]]:
    """List all available calendars."""
    service, error = _get_calendar_service()
    if error:
        return [{"error": error}]

    try:
        result = service.calendarList().list().execute()
        calendars = []
        for cal in result.get("items", []):
            calendars.append({
                "id": cal["id"],
                "summary": cal.get("summary", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
            })
        return calendars
    except Exception as e:
        return [{"error": f"Failed to list calendars: {e}"}]
