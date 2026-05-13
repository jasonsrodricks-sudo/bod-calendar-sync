# BOD Dashboard — Cheat Sheet
*Snapshot: May 12, 2026 — Things that work and how to fix them when they don't.*

---

## What's Working Right Now ✅

- **Calendar sync** — Pulls from Google Calendar every morning at 5 AM Eastern
- **Top Priorities** — Auto-populated from timed calendar events (trigger words: gym, meet, call, drop, pick up, etc.)
- **Full Agenda** — All timed events for the day, in order
- **Week Ahead** — Next 5 days of events
- **Cross-device checklist sync** — Supabase stores checkbox state, proxy reads/writes it
- **Weather** — Live from OpenWeather API (Beverly, MA)
- **BOD Navy Cards** — 12 ventures, clickable detail views
- **Construction Black Cards** — Active jobs with punch lists, invoice notes, contacts

---

## The Full Stack

| Layer | Service | Purpose |
|-------|---------|---------|
| Frontend | Netlify (bored-of-directors.netlify.app) | Serves the dashboard |
| Repo | GitHub (jasonsrodricks-sudo/bod-calendar-sync) | Source of truth for all code |
| Cron | Render (bod-calendar-sync) | Runs sync.py at 5 AM Eastern (9 AM UTC) |
| Proxy | Render (bod-proxy) | Reads/writes checklist state |
| Database | Supabase (bored-of-directors) | Stores daily_checklist state |
| Calendar | Google Calendar API | Pulls today's events |
| Weather | OpenWeather API | Current conditions + forecast |

---

## How the Daily Sync Works

1. Render cron job fires at 5 AM Eastern
2. `sync.py` pulls today's events from Google Calendar
3. Splits events into priorities (timed + trigger words) and agenda (all timed)
4. Reads `dashboard_template.html` from GitHub
5. Injects `PL_PRIORITIES` and `PL_AGENDA` arrays with today's data
6. Pushes updated `index.html` to GitHub
7. Netlify auto-deploys from GitHub push (auto-publishing must be UNLOCKED)

---

## Critical Rules — Never Break These

### dashboard_template.html
- `PL_PRIORITIES` and `PL_AGENDA` must be **empty arrays** — no hardcoded data
- Must look exactly like this:
```javascript
var PL_PRIORITIES=[
];
var PL_AGENDA=[
];
```
- If these get stale data baked in, sync.py injection breaks

### Netlify
- **Auto publishing must be UNLOCKED** — if locked, deploys succeed but nothing goes live
- Check: app.netlify.com → bored-of-directors → Deploys → look for "Auto Publishing Locked" warning
- Fix: click "Unlock to start auto publishing"

### Supabase daily_checklist table
- Columns: `date`, `item_id`, `checked`, `state`
- `item_id` and `checked` must have **NOT NULL dropped** — otherwise inserts silently fail
- `anon` role must have INSERT, SELECT, UPDATE grants
- Fix if broken:
```sql
ALTER TABLE public.daily_checklist ALTER COLUMN item_id DROP NOT NULL;
ALTER TABLE public.daily_checklist ALTER COLUMN checked DROP NOT NULL;
grant insert on public.daily_checklist to anon;
grant select on public.daily_checklist to anon;
grant update on public.daily_checklist to anon;
```

---

## Manual Trigger (Force Fresh Dashboard)

Go to: **dashboard.render.com → bod-calendar-sync → Trigger Run**

This forces an immediate sync + deploy outside the 5 AM schedule.

---

## Debugging Order (follow this exactly)

1. **Check Supabase first** — `select * from daily_checklist;` in SQL editor
2. **Check Render logs** — bod-calendar-sync → Logs (look for errors)
3. **Check Netlify** — is auto publishing locked? Is the latest deploy live?
4. **Check GitHub** — does `index.html` have today's data in `PL_PRIORITIES`?
5. **Check proxy** — bod-proxy → Logs (are POSTs returning 200?)
6. **Check browser** — hard refresh (Cmd+Shift+R) before assuming it's broken

---

## Common Breaks & Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Full Agenda empty | dashboard_template.html has stale data | Clear PL_PRIORITIES and PL_AGENDA to empty arrays in GitHub |
| Full Agenda empty | Netlify auto publishing locked | Unlock in Netlify → Deploys |
| Checkboxes not syncing cross-device | Supabase NOT NULL constraints | Run the ALTER TABLE fix above |
| Checkboxes not syncing cross-device | Render proxy spun down (cold start) | Wait 30s and reload — proxy wakes up |
| Dashboard shows raw code on mobile | Content-type issue | Now fixed — GitHub → Netlify deploys with correct type |
| Cron job failing | Python indentation error in sync.py | Check sync.py in GitHub for indentation |
| No events in priorities | All events are all-day in Google Calendar | Make sure recurring blocks have actual times set |

---

## Keys Location
All sensitive keys are in Jay's Notes app.

- **GITHUB BOD TOKEN** — needed to push code changes
- **NETLIFY AUTH TOKEN** — Netlify API (still in sync.py env vars)
- **NETLIFY SITE ID** — 2e055607-0959-4169-8252-a940f2716e90
- **SUPABASE URL** — https://vtmzpjkjabuuyhsahhol.supabase.co
- **SUPABASE PUBLISHABLE KEY** — in Jay's notes
- **GOOGLE CLIENT SECRET** — in Jay's notes
- **GOOGLE REFRESH TOKEN** — in Jay's notes
- **OPENWEATHER API KEY** — in Jay's notes

---

## Still On The To-Do List

- Health Zone → wire to Supabase (currently localStorage only)
- Mobile layout — responsive CSS improvements
- Construction cards — Invoiced button + payment reminder
- Speaking + sober coaching one-pager (Kara homework)
- northofbostonstudios.com build-out

---

## Golden Rule
**When something breaks, check Supabase first. Then Netlify. Then GitHub. Then the browser. In that order. Every time.**
