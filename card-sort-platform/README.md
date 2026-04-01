# Admin Card Sort Platform

A local Flask app for running open card sort studies with real participants.
Results are stored in SQLite and exportable as JSON and CSV.

---

## Setup (one time)

```bash
# 1. Install Python 3.9+ if you haven't already
# 2. Install Flask
pip install flask

# 3. Run the app
python app.py
```

The app will print:
```
🗂️  Card Sort Platform running at http://localhost:5050
📊  Researcher dashboard: http://localhost:5050/dashboard
```

---

## How to run a study

### Step 1 — Open the dashboard
Go to **http://localhost:5050/dashboard**

### Step 2 — Create a session link for each participant
Click **"+ New session link"** — a unique URL is generated.
Copy it and send it to your participant (Slack, email, calendar invite, etc.).

### Step 3 — Participant takes the sort
The participant opens their unique link, enters their name (optional), and sorts all 20 cards into groups they create themselves. Results save automatically when they submit.

### Step 4 — View results live
The dashboard auto-refreshes every 12 seconds. Switch between:
- **Sessions** — individual sorts with expandable group view
- **Card Matrix** — heatmap of card placement across all participants
- **Category Usage** — how often each group was used

### Step 5 — Export
Click **⬇ CSV** or **⬇ JSON** from the dashboard header to download all completed results.
Individual session JSON files are also saved automatically to `data/sessions/`.

---

## File structure

```
card-sort-platform/
├── app.py              ← Flask app (routes, API)
├── db.py               ← SQLite setup and helpers
├── requirements.txt    ← Python dependencies
├── README.md           ← This file
├── data/               ← Auto-created on first run
│   ├── card_sort.db    ← SQLite database
│   └── sessions/       ← Per-session JSON exports
├── static/
│   └── style.css       ← Shared styles
└── templates/
    ├── base.html       ← Base layout
    ├── home.html       ← Landing page
    ├── sort.html       ← Card sort interface
    ├── done.html       ← Completion page
    ├── dashboard.html  ← Researcher dashboard
    └── error.html      ← Error page
```

---

## Customising the card list

Edit the `CARDS` list at the top of `app.py`. Each card needs an `id` and a `label`.
The study is configured as an **open card sort** — participants create all groups themselves.

---

## Environment variables

| Variable     | Default                    | Purpose                          |
|---|---|---|
| `SECRET_KEY` | `uxr-card-sort-dev-key`    | Flask session secret (change in production) |
| `PORT`       | `5050`                     | Port to run on                   |

```bash
# Example: run on port 8080
PORT=8080 python app.py
```

---

## Sharing with remote participants

By default the app runs on `localhost` — only accessible from your machine.

**For remote/unmoderated sessions:** deploy to a free host like [Railway](https://railway.app) or [Render](https://render.com) in under 5 minutes. No code changes needed.

---

*Admin IA — UXR Card Sort Platform, Phase 01*
