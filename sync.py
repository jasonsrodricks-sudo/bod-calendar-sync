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
        p_items.append("  {id:'p" + str(i+1) + "',text:'" + title + "'}")
    pl_priorities = 'var PL_PRIORITIES=[\n' + ',\n'.join(p_items) + '\n];'

    # Build agenda — timed events first, then all-day at the bottom
    a_items = []
    for i, e in enumerate(timed_events):
        title = e.get('summary', '').replace("'", "\\'")
        time_str = format_time(e.get('start', {}).get('dateTime', ''))
        a_items.append("  {id:'a" + str(i+1) + "', time:'" + time_str + "', text:'" + title + "', sub:''}")

    offset = len(timed_events)
    for i, e in enumerate(allday_events):
        title = e.get('summary', '').replace("'", "\\'")
        a_items.append("  {id:'a" + str(offset+i+1) + "', time:'all day', text:'" + title + "', sub:''}")

    pl_agenda = 'var PL_AGENDA=[\n' + ',\n'.join(a_items) + '\n];'

    start_p = html.find('var PL_PRIORITIES=[')
    end_p = html.find('];', start_p) + 2
    html = html[:start_p] + pl_priorities + html[end_p:]

    start_a = html.find('var PL_AGENDA=[')
    end_a = html.find('];', start_a) + 2
    html = html[:start_a] + pl_agenda + html[end_a:]

    return html

def deploy_to_netlify(html_content):
    encoded = html_content.encode('utf-8')
    sha1 = hashlib.sha1(encoded).hexdigest()
    headers = {
        'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    url = f'https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys'
    manifest = requests.post(url, headers=headers, json={
        'files': {'/index.html': sha1}
    })
    manifest_data = manifest.json()
    print(f'Manifest status: {manifest.status_code}')
    deploy_id = manifest_data.get('id')
    required = manifest_data.get('required', [])
    if required:
        upload_url = f'https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html'
        upload_headers = {
            'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}',
            'Content-Type': 'text/html; charset=UTF-8'
        }
        upload = requests.put(upload_url, headers=upload_headers, data=encoded)
        print(f'Upload status: {upload.status_code}')
    print(f'Deploy ID: {deploy_id}')

if __name__ == '__main__':
    service = get_calendar_service()
    events = get_todays_events(service)
    print(f'Found {len(events)} events today')
    html = build_dashboard(events)
    deploy_to_netlify(html)
    print('Done!')
