import os
import json
import hashlib
import requests
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_JSON = os.environ.get('TOKEN_JSON')
NETLIFY_SITE_ID = os.environ.get('NETLIFY_SITE_ID')
NETLIFY_AUTH_TOKEN = os.environ.get('NETLIFY_AUTH_TOKEN')

def get_calendar_service():
    creds = Credentials.from_authorized_user_info(json.loads(TOKEN_JSON), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def get_todays_events(service):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    events = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events.get('items', [])

def format_time(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        hour = dt.hour % 12 or 12
        minute = dt.strftime('%M')
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f'{hour}:{minute} {ampm}'
    except:
        return dt_str

def build_dashboard(events):
    with open('dashboard_template.html', 'r') as f:
        html = f.read()

    # Split timed vs all-day events
    timed_events = [e for e in events if e.get('start', {}).get('dateTime')]
    allday_events = [e for e in events if e.get('start', {}).get('date') and not e.get('start', {}).get('dateTime')]

    # Build priorities — flagged first, then fill from timed
    priorities = [e for e in timed_events if 'top priority' in e.get('summary', '').lower()]
    timed_copy = [e for e in timed_events if e not in priorities]
    while len(priorities) < 3 and timed_copy:
        priorities.append(timed_copy.pop(0))
    priorities = priorities[:5]

    p_items = []
    for i, e in enumerate(priorities):
        title = e.get('summary', '').replace("'", "\\'")
        title = title.replace(' — top priority', '').replace(' top priority', '').replace('top priority — ', '').replace('top priority', '').strip()
        p_items.append(f"  {{id:'p{i+1}',text:'{title}'}}")
    pl_priorities = 'var PL_PRIORITIES=[\n' + ',\n'.join(p_items) + '\n];'

    # Build agenda — timed events first, then all-day at the bottom
    a_items = []
    for i, e in enumerate(timed_events):
        title = e.get('summary', '').replace("'", "\\'")
        time_str = format_time(e.get('start', {}).get('dateTime', ''))
        a_items.append(f"  {{id:'
