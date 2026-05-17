"""
Calendar MCP Server — Read Google Calendar events.

Requires one-time OAuth setup. See connectors/calendar_mcp/tools.py for details.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.calendar_mcp.tools import (
    get_upcoming_events, get_todays_schedule, search_events, list_calendars,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("calendar-mcp")


@mcp.tool()
def upcoming_events(days_ahead: int = 7, max_results: int = 10) -> str:
    """
    Get upcoming Google Calendar events.

    Args:
        days_ahead: How many days to look ahead (default 7).
        max_results: Maximum events to return (default 10).

    Returns:
        JSON list of upcoming events with times, locations, descriptions.
    """
    events = get_upcoming_events(max_results, days_ahead)
    return json.dumps({"count": len(events), "events": events}, indent=2, default=str)


@mcp.tool()
def todays_schedule() -> str:
    """
    Get today's calendar schedule.

    Returns all events scheduled for today.
    """
    events = get_todays_schedule()
    return json.dumps({"date": "today", "count": len(events), "events": events}, indent=2, default=str)


@mcp.tool()
def search_calendar(query: str, days_back: int = 30) -> str:
    """
    Search calendar events by keyword.

    Searches event titles and descriptions within the given time range.

    Args:
        query: Search term (e.g., "meeting", "dentist", "sprint review").
        days_back: How many days back to search (default 30).

    Returns:
        JSON list of matching events.
    """
    events = search_events(query, days_back)
    return json.dumps({"query": query, "count": len(events), "events": events}, indent=2, default=str)


@mcp.tool()
def my_calendars() -> str:
    """
    List all Google Calendar calendars accessible to you.

    Returns calendar names, IDs, and access roles.
    """
    calendars = list_calendars()
    return json.dumps({"count": len(calendars), "calendars": calendars}, indent=2, default=str)


def main():
    logger.info("Starting calendar-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
