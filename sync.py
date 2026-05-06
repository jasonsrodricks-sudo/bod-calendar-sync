import os
import json
import hashlib
import requests
import base64
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_JSON = os.environ.get('TOKEN_JSON')
NETLIFY_SITE_ID = os.environ.get('NETLIFY_SITE_ID')
NETLIFY_AUTH_TOKEN = os.environ.get('NETLIFY_AUTH_TOKEN')
GITHUB_TOKEN = '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'
GITHUB_REPO = 'jasonsrodricks-sudo/bod-calendar-sync'
GITHUB_FILE = 'index.html'

PRIORITY_TRIGGERS = ['meet', 'drop', 'call', 'session', 'coaching', 'pick up',
                     'deliver', 'ship', 'pay', 'appointment', 'top priority',
                     'gym', 'physical therapy', 'pt ']
EXCLUDE_PREFIXES = ['bod —', 'bod-', 'bod build', 'bod fix']

def get_calendar_service():
    creds = Credentials.from_authorized_user_info(json.loads(TOKEN_JSON), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def get_events_for_day(service, date_str):
    start = date_str + 'T00:00:00-04:00'
    end = date_str + 'T23:59:59-04:00'
    events = service.events().list(
        calendarId='primary', timeMin=start, timeMax=end,
        singleEvents=True, orderBy='startTime',
        timeZone='America/New_York'
    ).execute()
    return events.get('items', [])

def get_next_5_days(service, today_str):
    week = []
    base = datetime.strptime(today_str, '%Y-%m-%d')
    for i in range(1, 6):
        d = base + timedelta(days=i)
        ds = d.strftime('%Y-%m-%d')
        try:
            result = service.events().list(
                calendarId='primary',
                timeMin=ds + 'T00:00:00-04:00',
                timeMax=ds + 'T23:59:59-04:00',
                singleEvents=True, orderBy='startTime',
                timeZone='America/New_York'
            ).execute()
            events = result.get('items', [])
            timed = [e for e in events if e.get('start', {}).get('dateTime')
                     and not any(e.get('summary','').lower().startswith(p) for p in EXCLUDE_PREFIXES)]
            week.append({'day': d.strftime('%a'), 'month': d.strftime('%b'),
                         'day_num': d.strftime('%-d'), 'events': timed[:3]})
        except:
            week.append({'day': d.strftime('%a'), 'month': d.strftime('%b'),
                         'day_num': d.strftime('%-d'), 'events': []})
    return week

def get_yesterdays_unchecked(service, today_str):
    base = datetime.strptime(today_str, '%Y-%m-%d')
    yesterday_str = (base - timedelta(days=1)).strftime('%Y-%m-%d')
    events = get_events_for_day(service, yesterday_str)
    unchecked = [e for e in events if e.get('start', {}).get('date')
                 and not e.get('start', {}).get('dateTime')
                 and not any(e.get('summary','').lower().startswith(p) for p in EXCLUDE_PREFIXES)]
    print(f'Carrying over {len(unchecked)} unchecked items')
    return unchecked

def is_priority(event):
    title = event.get('summary', '').lower()
    if any(title.startswith(p) for p in EXCLUDE_PREFIXES):
        return False
    return any(t in title for t in PRIORITY_TRIGGERS)

def is_excluded(event):
    return any(event.get('summary', '').lower().startswith(p) for p in EXCLUDE_PREFIXES)

def format_time(dt_str):
    try:
        dt = datetime.strptime(dt_str[:19], '%Y-%m-%dT%H:%M:%S')
        hour = dt.hour % 12 or 12
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f'{hour}:{dt.strftime("%M")} {ampm}'
    except Exception as e:
        print(f'Time parse error: {e}')
        return dt_str

def build_dashboard(events, carryover=[], week_ahead=[]):
    # Read template from GitHub
    headers = {'Authorization': f'token {GITHUB_TOKEN}', 'Accept': 'application/vnd.github.v3+json'}
    res = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/contents/dashboard_template.html', headers=headers)
    file_data = res.json()
    html = base64.b64decode(file_data['content']).decode('utf-8')

    timed = [e for e in events if e.get('start', {}).get('dateTime') and not is_excluded(e)]
    allday = [e for e in events if e.get('start', {}).get('date')
              and not e.get('start', {}).get('dateTime') and not is_excluded(e)]

    priorities = [e for e in timed if is_priority(e)]
    non_priority = [e for e in timed if not is_priority(e)]
    while len(priorities) < 3 and non_priority:
        priorities.append(non_priority.pop(0))
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

    week_items = []
    for day in week_ahead:
        titles = [e.get('summary','').replace("'","\\'") for e in day['events']]
        events_str = ','.join(["'" + t + "'" for t in titles])
        week_items.append("  {label:'" + day['day'] + ' ' + day['month'] + ' ' + day['day_num'] + "',events:[" + events_str + "]}")
    week_js = 'var WEEK_AHEAD=[\n' + ',\n'.join(week_items) + '\n];'

    start_p = html.find('var PL_PRIORITIES=[')
    end_p = html.find('];', start_p) + 2
    html = html[:start_p] + pl_priorities + html[end_p:]

    start_a = html.find('var PL_AGENDA=[')
    end_a = html.find('];', start_a) + 2
    html = html[:start_a] + pl_agenda + html[end_a:]

    start_w = html.find('var WEEK_AHEAD=[')
    if start_w >= 0:
        end_w = html.find('];', start_w) + 2
        html = html[:start_w] + week_js + html[end_w:]
    else:
        html = html.replace('var PL_PRIORITIES=[', week_js + '\nvar PL_PRIORITIES=[')

    return html

def push_to_github(html_content):
    """Push updated HTML as index.html to GitHub — Netlify auto-deploys and serves functions"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    # Get current SHA of index.html
    res = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}', headers=headers)
    sha = None
    if res.status_code == 200:
        sha = res.json().get('sha')

    content_b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    payload = {
        'message': f'Daily dashboard update {datetime.now().strftime("%Y-%m-%d")}',
        'content': content_b64,
    }
    if sha:
        payload['sha'] = sha

    result = requests.put(
        f'https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}',
        headers=headers,
        json=payload
    )
    print(f'GitHub push: {result.status_code}')
    if result.status_code in [200, 201]:
        print('Pushed to GitHub — Netlify will auto-deploy with functions')
    else:
        print(f'GitHub error: {result.text}')
        # Fallback to direct Netlify deploy
        deploy_to_netlify_direct(html_content)

def deploy_to_netlify_direct(html_content):
    """Fallback direct Netlify deploy"""
    encoded = html_content.encode('utf-8')
    sha1 = hashlib.sha1(encoded).hexdigest()
    headers = {'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}', 'Content-Type': 'application/json'}
    url = f'https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys'
    manifest = requests.post(url, headers=headers, json={'files': {'/index.html': sha1}})
    manifest_data = manifest.json()
    deploy_id = manifest_data.get('id')
    if manifest_data.get('required'):
        requests.put(
            f'https://api.netlify.com/api/v1/deploys/{deploy_id}/files/index.html',
            headers={'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}', 'Content-Type': 'text/html; charset=UTF-8'},
            data=encoded)
    print(f'Fallback Netlify deploy: {deploy_id}')

if __name__ == '__main__':
    service = get_calendar_service()
    eastern_now = datetime.now(timezone.utc) + timedelta(hours=-4)
    today_str = eastern_now.strftime('%Y-%m-%d')
    print(f'Today (Eastern): {today_str}')
    events = get_events_for_day(service, today_str)
    print(f'Found {len(events)} events today')
    carryover = get_yesterdays_unchecked(service, today_str)
    week_ahead = get_next_5_days(service, today_str)
    html = build_dashboard(events, carryover, week_ahead)
    push_to_github(html)
    print('Done!')
