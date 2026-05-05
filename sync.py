import os
import json
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_JSON = os.environ.get('TOKEN_JSON')
NETLIFY_SITE_ID = os.environ.get('NETLIFY_SITE_ID')
NETLIFY_AUTH_TOKEN = os.environ.get('NETLIFY_AUTH_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://vtmzpjkjabuuyhsahhol.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_publishable_-fuWvPzb3IMMsxt7Bq9iXg_yX1BJH3Z')

PRIORITY_TRIGGERS = ['meet', 'drop', 'call', 'session', 'coaching', 'pick up',
                     'deliver', 'ship', 'pay', 'appointment', 'top priority']

def get_calendar_service():
    creds = Credentials.from_authorized_user_info(json.loads(TOKEN_JSON), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def get_events_for_day(service, date):
    start = date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end = date.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    events = service.events().list(
        calendarId='primary', timeMin=start, timeMax=end,
        singleEvents=True, orderBy='startTime',
        timeZone='America/New_York'
    ).execute()
    return events.get('items', [])

def get_yesterdays_unchecked(service):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    events = get_events_for_day(service, yesterday)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    checked_ids = set()
    if SUPABASE_KEY:
        try:
            res = requests.get(
                f'{SUPABASE_URL}/rest/v1/daily_checklist?date=eq.{yesterday_str}&checked=eq.true&select=item_id',
                headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
            )
            rows = res.json()
            if isinstance(rows, list):
                checked_ids = {r['item_id'] for r in rows}
        except Exception as e:
            print(f'Supabase error: {e}')
    unchecked = []
    for i, e in enumerate(events):
        is_allday = e.get('start', {}).get('date') and not e.get('start', {}).get('dateTime')
        if is_allday and f'a{i+1}' not in checked_ids:
            unchecked.append(e)
    print(f'Carrying over {len(unchecked)} unchecked items')
    return unchecked

def is_priority(event):
    title = event.get('summary', '').lower()
    return any(t in title for t in PRIORITY_TRIGGERS)

def format_time(dt_str):
    """Parse time from calendar — already in Eastern time since we requested timeZone=America/New_York"""
    try:
        # dt_str comes back like 2026-05-05T09:30:00-04:00
        dt = datetime.fromisoformat(dt_str)
        hour = dt.hour % 12 or 12
        minute = dt.strftime('%M')
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f'{hour}:{minute} {ampm}'
    except:
        return dt_str

def build_dashboard(events, carryover=[]):
    with open('dashboard_template.html', 'r') as f:
        html = f.read()

    timed = [e for e in events if e.get('start', {}).get('dateTime')]
    allday = [e for e in events if e.get('start', {}).get('date') and not e.get('start', {}).get('dateTime')]

    # Priorities — trigger words first, then fill
    priorities = [e for e in timed if is_priority(e)]
    non_priority_timed = [e for e in timed if not is_priority(e)]
    while len(priorities) < 3 and non_priority_timed:
        priorities.append(non_priority_timed.pop(0))
    priorities = priorities[:5]
    priority_titles = {e.get('summary', '').lower() for e in priorities}

    p_items = []
    for i, e in enumerate(priorities):
        title = e.get('summary', '').replace("'", "\\'")
        for phrase in ['top priority', '— top priority', 'top priority —']:
            title = title.replace(phrase, '').strip()
        time_str = format_time(e.get('start', {}).get('dateTime', '')) if e.get('start', {}).get('dateTime') else ''
        p_items.append("  {id:'p" + str(i+1) + "',text:'" + title + "',time:'" + time_str + "'}")
    pl_priorities = 'var PL_PRIORITIES=[\n' + ',\n'.join(p_items) + '\n];'

    # Agenda — timed only, not in priorities
    a_items = []
    idx = 1
    for e in timed:
        if e.get('summary', '').lower() not in priority_titles:
            title = e.get('summary', '').replace("'", "\\'")
            time_str = format_time(e.get('start', {}).get('dateTime', ''))
            a_items.append("  {id:'a" + str(idx) + "', time:'" + time_str + "', text:'" + title + "', sub:''}")
            idx += 1

    for e in allday:
        title = e.get('summary', '').replace("'", "\\'")
        a_items.append("  {id:'a" + str(idx) + "', time:'all day', text:'" + title + "', sub:''}")
        idx += 1

    for e in carryover:
        title = e.get('summary', '').replace("'", "\\'")
        a_items.append("  {id:'a" + str(idx) + "', time:'carry over', text:'" + title + "', sub:'from yesterday'}")
        idx += 1

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
    headers = {'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}', 'Content-Type': 'application/json'}
    url = f'https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys'
    manifest = requests.post(url, headers=headers, json={'files': {'/index.html': sha1}})
    manifest_data = manifest.json()
    print(f'Manifest: {manifest.status_code}')
    deploy_id = manifest_data.get('id')
    if manifest_data.get('required'):
        up = requests.put(
            f'https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html',
            headers={'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}', 'Content-Type': 'text/html; charset=UTF-8'},
            data=encoded)
        print(f'Upload: {up.status_code}')
    print(f'Deploy ID: {deploy_id}')

if __name__ == '__main__':
    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    events = get_events_for_day(service, now)
    print(f'Found {len(events)} events today')
    carryover = get_yesterdays_unchecked(service)
    html = build_dashboard(events, carryover)
    deploy_to_netlify(html)
    print('Done!')
