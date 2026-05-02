import os
import json
import requests
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
NETLIFY_HOOK = os.environ.get('NETLIFY_HOOK')
TOKEN_JSON = os.environ.get('TOKEN_JSON')

def get_calendar_service():
    creds = Credentials.from_authorized_user_info(json.loads(TOKEN_JSON), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def get_todays_events(service):
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end = now.replace(hour=23, minute=59, second=59).isoformat()
    events = service.events().list(
        calendarId='primary',
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events.get('items', [])

def trigger_netlify():
    if NETLIFY_HOOK:
        requests.post(NETLIFY_HOOK)
        print('Netlify deploy triggered')

if __name__ == '__main__':
    service = get_calendar_service()
    events = get_todays_events(service)
    print(f'Found {len(events)} events today')
    trigger_netlify()
