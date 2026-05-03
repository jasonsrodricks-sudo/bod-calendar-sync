import os
import json
import requests
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
TOKEN_JSON = os.environ.get('TOKEN_JSON')
NETLIFY_SITE_ID = os.environ.get('NETLIFY_SITE_ID')
NETLIFY_AUTH_TOKEN = os.environ.get('NETLIFY_AUTH_TOKEN')

DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']

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
    if not dt_str:
        return 'All day'
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        hour = dt.hour % 12 or 12
        minute = dt.strftime('%M')
        ampm = 'AM' if dt.hour < 12 else 'PM'
        return f'{hour}:{minute} {ampm}'
    except:
        return dt_str

def build_html(events):
    now = datetime.now()
    day_name = DAYS[now.weekday() + 1 if now.weekday() < 6 else 0]
    # Python weekday: 0=Mon, fix for JS style
    import calendar
    day_name = DAYS[now.toordinal() % 7]
    month_name = MONTHS[now.month - 1]
    date_str = f'{day_name} {month_name} {now.day}'

    priorities = [e for e in events if 'top priority' in e.get('summary','').lower()]
    reminders = [e for e in events if not e.get('start',{}).get('dateTime') and 'top priority' not in e.get('summary','').lower()]
    agenda = [e for e in events if e.get('start',{}).get('dateTime')]

    # Fill priorities to minimum 3
    if len(priorities) < 3:
        timed = [e for e in agenda if e not in priorities]
        while len(priorities) < 3 and timed:
            priorities.append(timed.pop(0))

    p_items = ''
    for i, e in enumerate(priorities[:5]):
        title = e.get('summary','').replace(' — top priority','').replace(' top priority','')
        p_items += f'<div class="item" onclick="toggle(this)"><div class="check"></div><div class="inum">0{i+1}</div><div style="flex:1"><div class="itext">{title}</div></div></div>'

    r_items = ''
    for e in reminders:
        title = e.get('summary','')
        r_items += f'<div class="rem-item" onclick="toggleRem(this)"><div class="rem-check"></div><span class="rem-text">{title}</span></div>'

    a_items = ''
    for e in agenda:
        title = e.get('summary','')
        time_str = format_time(e.get('start',{}).get('dateTime',''))
        sub = e.get('description','')
        sub_html = f'<div class="isub">{sub}</div>' if sub else ''
        a_items += f'<div class="item" onclick="toggle(this)"><div class="check"></div><span class="atime">{time_str}</span><div style="flex:1"><div class="itext">{title}</div>{sub_html}</div></div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard — {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=Playfair+Display:ital,wght@0,700;1,400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
:root{{--black:#0a0a0a;--cream:#f2ede4;--gold:#c9a84c;--navy:#1a2744;--navy75:rgba(26,39,68,0.75);--muted:#7a7060;--green:#0f6e56;}}
body{{background:var(--cream);color:var(--black);font-family:'DM Mono',monospace;min-height:100vh;}}
.topbar{{background:var(--black);padding:22px 28px 18px;position:relative;overflow:hidden;}}
.topbar::before{{content:'';position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 38px,rgba(255,255,255,0.03) 38px,rgba(255,255,255,0.03) 39px);}}
.eyebrow{{font-size:9px;letter-spacing:0.3em;text-transform:uppercase;color:var(--gold);position:relative;margin-bottom:6px;}}
.heading{{font-family:'Bebas Neue',sans-serif;font-size:48px;letter-spacing:0.06em;color:var(--cream);position:relative;line-height:1;}}
.heading span{{color:var(--gold);}}
.tagline{{font-family:'Playfair Display',serif;font-style:italic;font-size:14px;color:rgba(242,237,228,0.45);margin-top:8px;position:relative;}}
.goldbar{{background:var(--gold);padding:9px 28px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}}
.goldbar span{{font-size:9px;letter-spacing:0.25em;text-transform:uppercase;color:var(--black);font-weight:500;}}
.dot{{width:3px;height:3px;border-radius:50%;background:var(--black);opacity:0.4;}}
.main{{padding:24px 28px 0;max-width:1200px;margin:0 auto;}}
.prog-row{{display:flex;align-items:center;gap:14px;margin-bottom:20px;}}
.prog-label{{font-size:9px;letter-spacing:0.25em;text-transform:uppercase;color:var(--muted);}}
.prog-track{{flex:1;height:3px;background:rgba(0,0,0,0.1);border-radius:2px;}}
.prog-fill{{height:3px;background:var(--gold);border-radius:2px;transition:width 0.4s ease;}}
.prog-pct{{font-size:13px;font-weight:500;color:var(--gold);min-width:36px;text-align:right;}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:2px;margin-bottom:2px;}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr;}}}}
.card{{background:#fff;border:1px solid rgba(0,0,0,0.08);padding:20px 22px 16px;position:relative;overflow:hidden;}}
.card::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:var(--gold);transform:scaleX(0);transform-origin:left;transition:transform 0.3s ease;}}
.card:hover::after{{transform:scaleX(1);}}
.badge{{display:inline-block;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--cream);background:var(--navy);padding:3px 9px;border-radius:2px;margin-bottom:10px;}}
.card-title{{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:0.04em;color:var(--black);line-height:1;margin-bottom:12px;}}
.item{{display:flex;align-items:flex-start;gap:10px;padding:9px 0;border-bottom:1px solid rgba(0,0,0,0.06);cursor:pointer;user-select:none;}}
.item:last-child{{border-bottom:none;}}
.item.done .itext{{text-decoration:line-through;color:#b0a896;}}
.check{{width:18px;height:18px;border-radius:50%;border:1.5px solid rgba(0,0,0,0.2);flex-shrink:0;margin-top:2px;display:flex;align-items:center;justify-content:center;transition:all 0.2s;}}
.item.done .check{{background:var(--green);border-color:var(--green);}}
.item.done .check::after{{content:'';display:block;width:4px;height:8px;border:2px solid #fff;border-top:none;border-left:none;transform:rotate(45deg) translate(-1px,-1px);}}
.inum{{font-family:'Bebas Neue',sans-serif;font-size:26px;color:rgba(0,0,0,0.07);line-height:1;min-width:22px;}}
.itext{{font-size:12px;color:var(--black);line-height:1.5;flex:1;}}
.isub{{font-size:10px;color:var(--muted);margin-top:2px;}}
.atime{{font-size:9px;letter-spacing:0.1em;color:var(--gold);min-width:82px;padding-top:2px;flex-shrink:0;font-weight:500;}}
.rem-label{{font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--gold);padding:12px 0 6px;border-top:1px solid rgba(0,0,0,0.06);margin-top:4px;}}
.rem-item{{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(0,0,0,0.04);cursor:pointer;user-select:none;}}
.rem-item:last-child{{border-bottom:none;}}
.rem-item.done .rem-text{{text-decoration:line-through;color:#b0a896;}}
.rem-check{{width:14px;height:14px;border-radius:3px;border:1.5px solid rgba(0,0,0,0.15);flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:all 0.2s;}}
.rem-item.done .rem-check{{background:var(--green);border-color:var(--green);}}
.rem-item.done .rem-check::after{{content:'';display:block;width:3px;height:6px;border:1.5px solid #fff;border-top:none;border-left:none;transform:rotate(45deg) translate(-1px,-1px);}}
.rem-text{{font-size:11px;color:var(--muted);}}
.reset-btn{{display:inline-block;margin-top:14px;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--muted);border:1px solid rgba(0,0,0,0.12);padding:6px 14px;cursor:pointer;background:transparent;transition:all 0.2s;}}
.health-card{{background:var(--navy75);border:1px solid rgba(26,39,68,0.4);padding:20px 22px 16px;position:relative;overflow:hidden;margin-top:2px;}}
.health-badge{{display:inline-block;font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:var(--black);background:var(--gold);padding:3px 9px;border-radius:2px;margin-bottom:10px;}}
.health-title{{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:0.04em;color:var(--cream);line-height:1;margin-bottom:12px;}}
.health-table{{width:100%;border-collapse:collapse;margin-top:4px;}}
.health-table th{{font-size:9px;letter-spacing:0.15em;text-transform:uppercase;color:rgba(242,237,228,0.5);font-weight:400;padding:4px 6px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.1);}}
.health-table th.left{{text-align:left;}}
.health-table td{{padding:6px;border-bottom:1px solid rgba(255,255,255,0.06);vertical-align:middle;}}
.health-table tr:last-child td{{border-bottom:none;}}
.ex-name{{font-size:11px;color:var(--cream);white-space:nowrap;}}
.ex-target{{font-size:9px;color:rgba(242,237,228,0.45);}}
.set-box{{width:22px;height:22px;border-radius:3px;border:1.5px solid rgba(255,255,255,0.2);cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all 0.2s;margin:0 auto;user-select:none;font-size:10px;color:transparent;}}
.set-box.on{{background:var(--gold);border-color:var(--gold);color:var(--black);}}
.ex-total{{font-size:11px;font-weight:500;color:var(--gold);text-align:right;}}
.health-footer{{display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.08);}}
.health-total-label{{font-size:9px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(242,237,228,0.45);}}
.health-grand-total{{font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--gold);letter-spacing:0.05em;}}
</style>
</head>
<body>
<div class="topbar">
  <div class="eyebrow">Bored of Directors · Daily Punchlist</div>
  <div class="heading">{DAYS[now.toordinal() % 7]} <span>{MONTHS[now.month-1]} {now.day}</span></div>
  <div class="tagline">Connection is the only currency</div>
</div>
<div class="goldbar">
  <span id="prog-label">0 done</span>
  <div class="dot"></div>
  <span>Beverly, MA</span>
  <div class="dot"></div>
  <span>Today</span>
</div>
<div class="main">
  <div class="prog-row">
    <span class="prog-label">Day Progress</span>
    <div class="prog-track"><div class="prog-fill" id="pfill" style="width:0%"></div></div>
    <span class="prog-pct" id="ppct">0%</span>
  </div>
  <div class="grid">
    <div class="card">
      <span class="badge">Must Do</span>
      <div class="card-title">Top Priorities</div>
      {p_items}
      <div class="rem-label">Reminders</div>
      {r_items}
    </div>
    <div class="card">
      <span class="badge">Schedule</span>
      <div class="card-title">Full Agenda</div>
      {a_items}
      <button class="reset-btn" onclick="resetAll()">↺ Reset Day</button>
    </div>
  </div>
  <div class="health-card">
    <span class="health-badge">Health Zone</span>
    <div class="health-title">Daily Movement</div>
    <table class="health-table">
      <thead><tr><th class="left">Exercise</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>Total</th></tr></thead>
      <tbody id="hbody"></tbody>
    </table>
    <div class="health-footer">
      <span class="health-total-label">Day Total</span>
      <span class="health-grand-total" id="hgrand">0</span>
    </div>
  </div>
</div>
<script>
var TOTAL = document.querySelectorAll('.item, .rem-item').length;
function updateProgress(){{
  var done = document.querySelectorAll('.item.done, .rem-item.done').length;
  var pct = TOTAL ? Math.round(done/TOTAL*100) : 0;
  document.getElementById('pfill').style.width = pct + '%';
  document.getElementById('ppct').textContent = pct + '%';
  document.getElementById('prog-label').textContent = done + ' of ' + TOTAL + ' done';
}}
function toggle(el){{ el.classList.toggle('done'); updateProgress(); }}
function toggleRem(el){{ el.classList.toggle('done'); updateProgress(); }}
function resetAll(){{
  document.querySelectorAll('.item.done, .rem-item.done').forEach(function(el){{ el.classList.remove('done'); }});
  document.querySelectorAll('.set-box.on').forEach(function(b){{ b.classList.remove('on'); b.textContent=''; }});
  updateProgress(); buildHealth();
}}
var HZ=[
  {{name:'Meditate',target:'20 min',val:20}},
  {{name:'Push ups',target:'33 reps',val:33}},
  {{name:'Squats',target:'33 reps',val:33}},
  {{name:'Leg lifts',target:'33 reps',val:33}},
  {{name:'Sit ups',target:'33 reps',val:33}},
  {{name:'Pull ups',target:'5 reps',val:5}},
  {{name:'Cardio',target:'100 cal',val:100}},
];
var hzState = HZ.map(function(){{ return [false,false,false,false,false,false]; }});
function buildHealth(){{
  var tbody = document.getElementById('hbody');
  tbody.innerHTML = '';
  var grand = 0;
  HZ.forEach(function(ex, ei){{
    var tr = document.createElement('tr');
    var rowTotal = hzState[ei].filter(Boolean).length * ex.val;
    grand += rowTotal;
    var td0 = document.createElement('td');
    td0.innerHTML = '<div class="ex-name">'+ex.name+'</div><div class="ex-target">'+ex.target+'/set</div>';
    tr.appendChild(td0);
    for(var si=0;si<6;si++){{
      var td = document.createElement('td');
      var box = document.createElement('div');
      box.className = 'set-box' + (hzState[ei][si] ? ' on' : '');
      box.textContent = hzState[ei][si] ? '✓' : '';
      (function(eix,six){{ box.onclick = function(){{ hzState[eix][six]=!hzState[eix][six]; buildHealth(); }}; }})(ei,si);
      td.appendChild(box); tr.appendChild(td);
    }}
    var tdT = document.createElement('td');
    tdT.className = 'ex-total';
    tdT.textContent = rowTotal || '';
    tr.appendChild(tdT);
    tbody.appendChild(tr);
  }});
  document.getElementById('hgrand').textContent = grand || '0';
}}
buildHealth();
updateProgress();
</script>
</body>
</html>'''

def deploy_to_netlify(html_content):
    url = f'https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys'
    import base64, zipfile, io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('index.html', html_content.encode('utf-8'))
    zip_buffer.seek(0)
    headers = {
        'Authorization': f'Bearer {NETLIFY_AUTH_TOKEN}',
        'Content-Type': 'application/zip'
    }
    response = requests.post(url, headers=headers, data=zip_buffer.getvalue())
    print(f'Netlify deploy status: {response.status_code}')
    print(response.text[:500])
