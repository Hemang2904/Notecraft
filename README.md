# NPL Note Tracker — Notecraft Capital

A Streamlit-based follow-up and status tracking system for Non-Performing Loan
notes. Upload weekly Outlook email exports and the system will parse, diff,
and update your tracker automatically.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Supported email formats

| Format | Source | Notes |
|--------|--------|-------|
| `.docx` | Outlook → Save As → Word | Best for bulk email threads |
| `.eml` | Drag emails from Outlook to a folder | Standard email format |
| `.msg` | Outlook native format | Requires `extract-msg` |
| `.txt` | Copy-paste or export | Plain text fallback |

## How to export emails from Outlook

### Option A: Save as .docx (recommended for bulk threads)
1. Open the email thread in Outlook
2. **File → Save As → Word Document (.docx)**
3. Name the file with the state code: e.g. `095-108177_FL_1-20_Feb_2026_Mails.docx`
4. The filename must contain `FL`, `OR`, or `TX`/`Texas` so the system can
   match it to the correct note

### Option B: Drag as .msg
1. Select emails in Outlook
2. Drag them into a folder on your desktop
3. They save as `.msg` files automatically

### Option C: Save as .eml
1. In Outlook: **File → Save As → Outlook Message Format - Unicode (.msg)**
   or use **File → Save As → Text Only (.txt)**
2. For `.eml`: some Outlook versions support this directly; otherwise use
   Thunderbird or another client

## Weekly workflow

1. Export this week's email threads from Outlook (one file per note/state)
2. Open the app → click **📤 Weekly email upload** in the sidebar
3. Drop all files into the uploader
4. (Optional) Paste your Anthropic API key for AI-powered parsing
5. Click **🚀 Process emails**
6. Review the **🔔 Notifications** panel for what changed
7. Update statuses and check off completed tasks

## AI parsing vs. fallback

- **With API key**: Claude Sonnet reads the emails, finds new events not
  already in the timeline, suggests status changes, generates follow-up
  tasks, and creates notifications. Deduplicates automatically.
- **Without API key**: Files are logged as uploads in the timeline. You can
  still manually update statuses and tasks.

## File naming convention

The system auto-detects which note a file belongs to based on keywords in the
filename:

| Keyword in filename | Matched note |
|---------------------|-------------|
| `FL` or `Florida` | FL-095108177 (Florida — Property Maintenance) |
| `OR` or `Orlando` | OR-431445777 (Orlando — Insurance FPI) |
| `TX` or `Texas` | TX-511048346 (Texas — Foreclosure / Title) |

## Data storage

All data is stored locally in the `data/` directory:
- `notes.json` — note data, timelines, tasks, contacts
- `notifications.json` — notification queue
- `meta.json` — upload history and metadata

To reset to seed data, delete the `data/` folder and restart.

## Project structure

```
npl_tracker/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── data/               # Auto-created on first run
    ├── notes.json
    ├── notifications.json
    └── meta.json
```
