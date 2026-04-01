# CLAUDE.md — Admin Card Sort Platform

> Claude Code reads this file automatically at session start.
> It covers architecture, design system, data model, and open tasks.

---

## Project Overview

A **local Flask + SQLite card sorting platform** for UX research.
Built for Dualboot Partners / Lexipol to run an **open card sort** with
admin users of the Lexipol Solar design system.

- Researcher creates unique session links → shares with participants
- Each participant drags 20 task cards into self-created groups (open sort)
- All results persist in SQLite + per-session JSON files
- Researcher dashboard shows live stats, card matrix heatmap, category usage bars
- Export to CSV or JSON for analysis

**Run locally:**
```bash
pip install flask
python app.py
# → http://localhost:5050
# → http://localhost:5050/dashboard
```

---

## File Map

```
card-sort-platform/
├── app.py                  # Flask routes + business logic
├── db.py                   # SQLite schema + helpers (get_db, init_db, close_db)
├── requirements.txt        # Flask>=3.0.0
├── CLAUDE.md               # ← you are here
├── static/
│   └── style.css           # Solar/Lexipol design tokens (global shared styles)
├── templates/
│   ├── base.html           # Base layout: Google Fonts (Sora, Roboto, Geist) + CSS
│   ├── home.html           # Landing page
│   ├── sort.html           # Participant card sort interface (drag-and-drop)
│   ├── dashboard.html      # Researcher dashboard (stats, matrix, categories)
│   ├── done.html           # Post-submission thank-you page
│   └── error.html          # 404 / error page
└── data/
    ├── card_sort.db        # SQLite database (auto-created on first run)
    └── sessions/           # Per-session JSON snapshots (auto-created)
```

---

## Design System — Solar for Lexipol

All UI must use these tokens. **Never introduce new colors or fonts.**

### Colors
| Token | Hex | Use |
|---|---|---|
| Primary | `#014AA8` | Buttons, links, active states, progress bar |
| Primary Dark | `#002B69` | Overlay backgrounds, hover states |
| Navy | `#000F2F` | Page headings, dark text |
| Secondary | `#6792CB` | Card IDs, secondary highlights |
| Bright Blue | `#026BEC` | Accent links |
| Accent Amber | `#FFB81C` | "New" badge background (light variant `#FFF3CC`) |
| Text | `#191919` | Body text |
| Muted | `#717377` | Secondary labels, meta text |
| Light | `#B4B6BA` | Placeholder text, empty states |
| Neutral | `#DDDDDF` | Borders, dividers |
| Background | `#F5F5F5` | Page backgrounds, tray backgrounds |
| White | `#ffffff` | Card surfaces |
| Red | `#D50032` | Delete actions, error states |
| Green | `#84C341` | Success, completed badges |

### Typography
| Role | Font | Weight |
|---|---|---|
| Headings, buttons, tabs, labels | **Sora** | 600 / 700 / 800 |
| Body text, descriptions, card content | **Roboto** | 400 / 500 |
| Monospace labels (tokens, IDs, code) | **Geist** | 600 / 700 |

Fonts are loaded via Google Fonts in `base.html`.
CSS variables are defined in `:root` in `static/style.css`.

---

## Database Schema

### `sessions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto-increment |
| token | TEXT UNIQUE | 8-char UUID prefix, used in participant URL |
| participant_name | TEXT | filled on sort start |
| role | TEXT | optional (not collected in current UI) |
| status | TEXT | `pending` / `in_progress` / `completed` |
| card_order | TEXT | JSON array of card IDs (shuffled once, persisted) |
| started_at | TEXT | ISO datetime |
| completed_at | TEXT | ISO datetime |
| created_at | TEXT | ISO datetime (default: now) |
| duration_seconds | INTEGER | filled on submit |

### `assignments`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| session_id | INTEGER FK | → sessions.id |
| card_id | TEXT | e.g. `P1`, `T3`, `W2` |
| card_label | TEXT | full label text |
| category | TEXT | group name participant chose |
| confidence | INTEGER | not currently collected in UI (nullable) |
| time_seconds | INTEGER | not currently collected in UI (nullable) |
| emotional_signal | TEXT | not currently collected in UI (default: neutral) |

### `categories`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| session_id | INTEGER FK | → sessions.id |
| name | TEXT | group name as typed by participant |
| is_user_created | INTEGER | 1 = participant created |
| card_count | INTEGER | how many cards in this group |

---

## Card Inventory (20 cards)

| ID | Label |
|---|---|
| P1 | Update policy or procedure manual content |
| P2 | Assign policy-related trainings to users |
| P3 | Review regulatory policy updates |
| P4 | Review policy acknowledgement records |
| P5 | Review accreditation requirements |
| T1 | Assign trainings to users |
| T2 | Create learning plans |
| T3 | Review training phase progress |
| T4 | View certification expiration records |
| T5 | Audit training reports |
| W1 | Manage peer support and help line contacts |
| W2 | Create health and well-being resources |
| W3 | Send notifications to users about resources |
| W4 | Review engagement analytics for wellness programs |
| W5 | Create wellness and development events |
| PR1 | Configure data collection forms |
| PR2 | Configure monitoring rules |
| PR3 | View and export analytics |
| PR4 | Configure form review workflows |
| PR5 | Review flagged records |

Card IDs encode their origin domain (P=Policy, T=Training, W=Wellness, PR=Performance Reporting)
but **participants never see these IDs** — only the label text.

---

## Key Architecture Decisions

1. **Open sort only** — `categories = []` at start; participants create all groups from scratch.
   There are NO predefined categories passed to any template.

2. **No participant download** — results are saved server-side automatically.
   The `/done` page explicitly tells participants they can close the window.

3. **Unique session tokens** — 8-char UUID prefix per session. One participant per link.
   A completed session redirects to `/done` with an "already submitted" message.

4. **Dual persistence** — SQLite (primary) + per-session JSON snapshot in `data/sessions/`
   (backup + easier analysis pipeline integration).

5. **Live polling** — dashboard polls `/api/stats` and `/api/analysis` every 12 seconds.

6. **Agreement matrix** — `_agreement_matrix()` in app.py calculates per-card distribution
   across all completed sessions. Used for the heatmap in the dashboard.

---

## API Reference

| Method | Route | Description |
|---|---|---|
| GET | `/` | Home / landing page |
| GET | `/sort/<token>` | Participant sort interface |
| POST | `/api/session/start` | Set name, mark session in_progress |
| POST | `/api/session/submit` | Store assignments + categories, mark completed |
| GET | `/done` | Thank-you page |
| GET | `/dashboard` | Researcher dashboard |
| POST | `/dashboard/create-session` | Create new session token, return URL |
| POST | `/dashboard/delete-session/<sid>` | Delete session + all data |
| GET | `/api/stats` | Live session counts + list |
| GET | `/api/analysis` | Agreement matrix + category usage |
| GET | `/api/export/json` | Download all completed sessions as JSON |
| GET | `/api/export/csv` | Download all assignments as CSV |

---

## Known Gaps / Open Tasks

These are areas ready for further development:

### High priority
- [ ] **Researcher auth** — `/dashboard` is currently unprotected. Add a simple password
  or token-based gate (env var `DASHBOARD_PASSWORD`).
- [ ] **Role field UI** — the DB has a `role` column but the sort intro doesn't collect it.
  Add a dropdown (e.g. "Sergeant / Lieutenant / Captain / Admin") before the name field.
- [ ] **Debrief questions** — after submit, show 2–3 open-text questions
  (e.g. "What was your logic for naming your groups?"). Store in a new `debrief_responses` table.

### Medium priority
- [ ] **Session detail groups** — the dashboard session detail panel calls `renderDetailHTML()`
  but never fetches the actual group data. Add a `/api/session/<sid>/groups` endpoint and
  populate the grid when the row is expanded.
- [ ] **Co-occurrence matrix** — build a secondary analysis view showing which cards
  were most often grouped together (beyond per-card agreement).
- [ ] **Print / PDF export** — add a print stylesheet so the researcher can print the heatmap.

### Low priority / nice-to-have
- [ ] **Mobile responsiveness** — the sort interface is desktop-only (drag-and-drop).
  Consider a tap-to-assign fallback for tablet.
- [ ] **Session notes** — let the researcher add a text note per session
  (e.g. "participant was distracted", "moderator had to explain twice").
- [ ] **Participant timer warning** — show a gentle nudge if the timer exceeds 20 minutes.

---

## UXR Context

This platform supports a **moderated open card sort** for:
- **Client:** Lexipol (Solar design system team)
- **Study goal:** Understand how admin users naturally group their daily tasks
  to inform the information architecture of the admin panel.
- **Participants:** ~8–12 law enforcement agency admins
- **Analysis output:** Agreement matrix → category dendogram → IA recommendations
- **Companion files** (in `UXR_Admin_Testing_System/`):
  - `01_System_Rules.md` — session lifecycle + file map
  - `02_Tester_Agent.md` — moderator AI prompt + probe bank
  - `03_Admin_Agent.md` — data + insights admin modes
  - `04_Test_Script.md` — full moderator script
  - `05_Response_Schema.json` — JSON schema (draft-07) for session validation
  - `06_Analysis_Prompt.md` — 7-step analysis pipeline
