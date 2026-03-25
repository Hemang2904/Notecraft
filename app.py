"""
NPL Note Tracker — Streamlit App
================================
Notecraft Capital follow-up and status tracking system.
Upload weekly Outlook email exports (.docx / .msg / .txt / .eml),
parse them with Claude AI, and track follow-ups per note.
"""

import streamlit as st
import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NPL Note Tracker — Notecraft Capital",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
NOTES_FILE = DATA_DIR / "notes.json"
NOTIFS_FILE = DATA_DIR / "notifications.json"
META_FILE = DATA_DIR / "meta.json"

STATUS_CONFIG = {
    "action_needed": {"label": "🔴 Action needed", "color": "#E24B4A", "bg": "#FCEBEB"},
    "awaiting_response": {"label": "🟡 Awaiting response", "color": "#BA7517", "bg": "#FAEEDA"},
    "in_progress": {"label": "🔵 In progress", "color": "#378ADD", "bg": "#E6F1FB"},
    "completed": {"label": "🟢 Completed", "color": "#639922", "bg": "#EAF3DE"},
    "on_hold": {"label": "⚪ On hold", "color": "#888780", "bg": "#F1EFE8"},
}

PRIORITY_COLORS = {
    "high": "#E24B4A",
    "medium": "#BA7517",
    "low": "#888780",
}

TYPE_COLORS = {
    "update": "#378ADD",
    "decision": "#534AB7",
    "follow_up": "#BA7517",
    "milestone": "#639922",
    "issue": "#E24B4A",
    "acknowledgment": "#888780",
    "new_upload": "#0F6E56",
}

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
SEED_NOTES = [
    {
        "id": "FL-095108177",
        "state": "FL",
        "label": "Florida",
        "loanNumber": "5926000001",
        "noteId": "095-108177",
        "property": "3915 Barnegat Dr, Punta Gorda, FL 33950",
        "servicer": "LandHome Financial Services",
        "attorney": "Waldman Law",
        "propertyMgmt": "Cliff Pointe Inc / South Watuppa Asset Management",
        "status": "in_progress",
        "category": "Property Maintenance",
        "summary": (
            "Yard brush/tree cleanup required for HOA compliance. "
            "First bid $1,920 (Left Coast Pres), deemed too high. "
            "Contractor revised to $700. Waiting on 2nd bid. "
            "HOA treasurer John Giovanni flagged rodent concerns. "
            "Goal: minimal work — property may become REO (in foreclosure)."
        ),
        "contacts": [
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Russell Wilde", "role": "Senior Asset Manager (South Watuppa)", "email": "rwilde@reo-consult.com", "phone": "503-855-7252"},
            {"name": "Cliff Ponte", "role": "Default Consultant / Broker (KW)", "email": "cponte@kw.com", "phone": ""},
            {"name": "Nishit", "role": "Notecraft Team", "email": "nishit@notecraftcapital.com", "phone": ""},
            {"name": "Rushabh Sheth", "role": "Notecraft Team", "email": "rushabh@notecraftcapital.com", "phone": ""},
            {"name": "John Giovanni", "role": "HOA Treasurer", "email": "", "phone": ""},
        ],
        "timeline": [
            {"date": "2026-02-10", "action": "Abhi contacted Cliff Ponte about HOA overgrowth complaint. John Giovanni (HOA treasurer) flagged rodent concerns.", "from": "Abhi Sheth", "type": "issue"},
            {"date": "2026-02-10", "action": "Cliff introduced Russell Wilde as assigned asset manager. Requested local agent for bid on rush.", "from": "Cliff Ponte", "type": "update"},
            {"date": "2026-02-12", "action": "First bid received: Left Coast Pres at $1,920. Russell requested 2nd bid due to high amount.", "from": "Russell Wilde", "type": "milestone"},
            {"date": "2026-02-18", "action": "Abhi followed up on 2nd bid status. Emphasized minimal cleanup — property may become REO.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-02-18", "action": "Original contractor revised bid to $700. 2nd bid expected in 1-2 days.", "from": "Russell Wilde", "type": "update"},
            {"date": "2026-02-18", "action": "Abhi acknowledged revised quote. Agreed to wait for 2nd bid before deciding.", "from": "Abhi Sheth", "type": "decision"},
        ],
        "followUps": [
            {"task": "Receive 2nd contractor bid for yard cleanup", "dueDate": "2026-02-22", "priority": "high", "completed": False},
            {"task": "Compare both bids and approve one (target: under $700)", "dueDate": "2026-02-25", "priority": "high", "completed": False},
            {"task": "Consider bi-weekly maintenance schedule for HOA", "dueDate": "2026-03-01", "priority": "medium", "completed": False},
            {"task": "Confirm HOA compliance after cleanup", "dueDate": "2026-03-15", "priority": "medium", "completed": False},
        ],
    },
    {
        "id": "OR-431445777",
        "state": "OR",
        "label": "Orlando",
        "loanNumber": "5926000001, 5926000002, 5926000003",
        "noteId": "431-445777",
        "property": "Cross-loan (All 3 properties)",
        "servicer": "LandHome Financial Services",
        "attorney": "N/A",
        "propertyMgmt": "N/A",
        "status": "awaiting_response",
        "category": "Insurance (FPI)",
        "summary": (
            "Forced Place Insurance needed for all 3 newly boarded loans at LandHome. "
            "Constantine shared quotes. Awaiting: (1) ACH/wiring instructions, "
            "(2) confirmation coverage began at loan boarding. "
            "Loan 5926000002 transferred to ZBS. FL and TX loans in foreclosure with Waldman Law."
        ),
        "contacts": [
            {"name": "Constantine Pavlakis", "role": "LandHome Rep", "email": "Constantine.Pavlakis@LHFS.com", "phone": ""},
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Rachel Mott", "role": "Foreclosure Specialist (LandHome)", "email": "Rachel.Mott@LHFS.com", "phone": "+1 562-203-7949"},
            {"name": "Jeanne Drake", "role": "LandHome Insurance", "email": "Jeanne.Drake@LHFS.com", "phone": ""},
            {"name": "Crystin Sims", "role": "LandHome Insurance", "email": "Crystin.Sims@LHFS.com", "phone": ""},
            {"name": "Joe LaBruna", "role": "LandHome", "email": "Joe.LaBruna@lhfs.com", "phone": ""},
            {"name": "Gonzalo Bozo Valenzuela", "role": "Oak Harbor Capital", "email": "GValenzuela@oakharborcapital.com", "phone": ""},
            {"name": "Emma Brookman", "role": "Oak Harbor Capital", "email": "EBrookman@oakharborcapital.com", "phone": ""},
        ],
        "timeline": [
            {"date": "2026-01-30", "action": "Rachel Mott confirmed loan 5926000002 transfer to ZBS. FL and TX loans in foreclosure with Waldman Law / Cliff Pointe Inc.", "from": "Rachel Mott", "type": "update"},
            {"date": "2026-01-31", "action": "Constantine acknowledged Rachel's update.", "from": "Constantine Pavlakis", "type": "acknowledgment"},
            {"date": "2026-02-05", "action": "Abhi followed up requesting FPI status update.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-02-05", "action": "Constantine shared insurance quotes. Requested ACH/wiring instructions and coverage confirmation from Jeanne.", "from": "Constantine Pavlakis", "type": "update"},
        ],
        "followUps": [
            {"task": "Jeanne Drake to provide ACH/wiring instructions for FPI payment", "dueDate": "2026-02-12", "priority": "high", "completed": False},
            {"task": "Confirm FPI coverage retroactive to loan boarding date", "dueDate": "2026-02-12", "priority": "high", "completed": False},
            {"task": "Make FPI payment once instructions received", "dueDate": "2026-02-15", "priority": "high", "completed": False},
        ],
    },
    {
        "id": "TX-511048346",
        "state": "TX",
        "label": "Texas",
        "loanNumber": "5926000003",
        "noteId": "511-048346",
        "property": "3658 Racquet Club Dr, Grand Prairie, TX 75052",
        "servicer": "LandHome Financial Services",
        "attorney": "Waldman Law (Damian Waldman, Esq.)",
        "propertyMgmt": "Cliff Pointe Inc",
        "status": "action_needed",
        "category": "Foreclosure / Title",
        "summary": (
            "HECM NPL legal review. Indemnity letter from Old Republic received — "
            "insurance covers the lien, clearing foreclosure. Address in claim has "
            "transposed digits (Divinia Sabal error). Damian to request correction. "
            "Invoice for title claim requested under 'Notecraft Capital SOF I' for HUD reimbursement."
        ),
        "contacts": [
            {"name": "Damian Waldman", "role": "Attorney (Waldman Law)", "email": "damian@dwaldmanlaw.com", "phone": "(727) 538-4160"},
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Nishit", "role": "Notecraft Team", "email": "nishit@notecraftcapital.com", "phone": ""},
            {"name": "Rushabh Sheth", "role": "Notecraft Team", "email": "rushabh@notecraftcapital.com", "phone": ""},
            {"name": "Divinia Sabal", "role": "Claims Admin (Old Republic)", "email": "", "phone": ""},
        ],
        "timeline": [
            {"date": "2026-01-28", "action": "Damian asked about sending invoice for title claim for HUD reimbursement.", "from": "Damian Waldman", "type": "update"},
            {"date": "2026-01-28", "action": "Abhi confirmed — invoice under 'Notecraft Capital Special Opportunities Fund I', ref property + HECM loan 511-048346.", "from": "Abhi Sheth", "type": "decision"},
            {"date": "2026-01-31", "action": "Damian sent letter of indemnity from Old Republic. Insurance covers the lien — foreclosure can proceed.", "from": "Damian Waldman", "type": "milestone"},
            {"date": "2026-02-02", "action": "Abhi flagged incorrect address (digits transposed by Divinia Sabal). Requested corrected letter.", "from": "Abhi Sheth", "type": "issue"},
            {"date": "2026-02-03", "action": "Damian confirmed he will request corrected letter from Old Republic.", "from": "Damian Waldman", "type": "acknowledgment"},
        ],
        "followUps": [
            {"task": "Receive corrected indemnity letter with correct address", "dueDate": "2026-02-10", "priority": "high", "completed": False},
            {"task": "Receive invoice for title claim (SOF I) for HUD reimbursement", "dueDate": "2026-02-15", "priority": "medium", "completed": False},
            {"task": "Proceed with foreclosure once corrected letter confirmed", "dueDate": "2026-02-20", "priority": "high", "completed": False},
        ],
    },
]


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def load_notes():
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text())
    return SEED_NOTES


def save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


def load_notifications():
    if NOTIFS_FILE.exists():
        return json.loads(NOTIFS_FILE.read_text())
    return []


def save_notifications(notifs):
    NOTIFS_FILE.write_text(json.dumps(notifs, indent=2))


def load_meta():
    if META_FILE.exists():
        return json.loads(META_FILE.read_text())
    return {}


def save_meta(meta):
    META_FILE.write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------------------
# Email extraction helpers
# ---------------------------------------------------------------------------
def extract_text_from_docx(file_bytes, filename):
    """Extract text from a .docx file."""
    import docx
    import io

    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_eml(file_bytes, filename):
    """Extract text from a .eml file."""
    import email
    from email import policy

    msg = email.message_from_bytes(file_bytes, policy=policy.default)
    parts = []
    if msg["Subject"]:
        parts.append(f"Subject: {msg['Subject']}")
    if msg["From"]:
        parts.append(f"From: {msg['From']}")
    if msg["To"]:
        parts.append(f"To: {msg['To']}")
    if msg["Date"]:
        parts.append(f"Date: {msg['Date']}")
    parts.append("")
    body = msg.get_body(preferencelist=("plain", "html"))
    if body:
        content = body.get_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        parts.append(content)
    return "\n".join(parts)


def extract_text_from_msg(file_bytes, filename):
    """Extract text from Outlook .msg file using olefile."""
    try:
        import extract_msg

        import io
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            msg = extract_msg.Message(tmp_path)
            parts = []
            if msg.subject:
                parts.append(f"Subject: {msg.subject}")
            if msg.sender:
                parts.append(f"From: {msg.sender}")
            if msg.to:
                parts.append(f"To: {msg.to}")
            if msg.date:
                parts.append(f"Date: {msg.date}")
            parts.append("")
            if msg.body:
                parts.append(msg.body)
            msg.close()
            return "\n".join(parts)
        finally:
            os.unlink(tmp_path)
    except ImportError:
        return f"[Cannot parse .msg — install extract-msg: pip install extract-msg]\nFilename: {filename}"


def extract_text(file_bytes, filename):
    """Route file to the correct parser."""
    ext = Path(filename).suffix.lower()
    if ext == ".docx":
        return extract_text_from_docx(file_bytes, filename)
    elif ext == ".eml":
        return extract_text_from_eml(file_bytes, filename)
    elif ext == ".msg":
        return extract_text_from_msg(file_bytes, filename)
    elif ext in (".txt", ".text"):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        return file_bytes.decode("utf-8", errors="replace")


def detect_note_id(filename):
    """Match filename to a note based on state abbreviation."""
    name = filename.upper()
    if "FL" in name or "FLORIDA" in name:
        return "FL-095108177", "Florida"
    elif "OR" in name or "ORLANDO" in name:
        return "OR-431445777", "Orlando"
    elif "TX" in name or "TEXAS" in name:
        return "TX-511048346", "Texas"
    return None, None


# ---------------------------------------------------------------------------
# AI parsing via Anthropic API
# ---------------------------------------------------------------------------
def parse_with_claude(file_contents, existing_notes, api_key):
    """Send extracted emails to Claude for intelligent diff parsing."""
    import anthropic

    existing_summary = []
    for n in existing_notes:
        last_event = n["timeline"][-1] if n["timeline"] else {}
        existing_summary.append({
            "id": n["id"],
            "state": n["state"],
            "label": n["label"],
            "property": n["property"],
            "category": n["category"],
            "lastTimelineDate": last_event.get("date", "unknown"),
            "lastAction": last_event.get("action", "none"),
            "pendingTasks": [f["task"] for f in n["followUps"] if not f["completed"]],
        })

    files_text = "\n\n".join(
        f"--- FILE: {fc['name']} (matched to: {fc['note_label']}) ---\n{fc['content'][:8000]}"
        for fc in file_contents
    )

    prompt = f"""You are an email parser for an NPL (Non-Performing Loan) tracking system at Notecraft Capital.

EXISTING NOTES IN THE SYSTEM:
{json.dumps(existing_summary, indent=2)}

NEW EMAIL FILES UPLOADED:
{files_text}

Analyze these emails and return ONLY a JSON object (no markdown, no backticks, no preamble) with this exact structure:
{{
  "changes": [
    {{
      "noteId": "FL-095108177 or OR-431445777 or TX-511048346",
      "newEvents": [
        {{ "date": "YYYY-MM-DD", "action": "concise description", "from": "person name", "type": "update|decision|follow_up|milestone|issue|acknowledgment" }}
      ],
      "newFollowUps": [
        {{ "task": "description", "dueDate": "YYYY-MM-DD", "priority": "high|medium|low" }}
      ],
      "statusSuggestion": "in_progress|awaiting_response|action_needed|completed|on_hold or null",
      "summaryUpdate": "updated summary or null"
    }}
  ],
  "notifications": [
    {{ "message": "human-readable notification", "noteLabel": "Florida|Orlando|Texas", "noteStatus": "status_key", "severity": "high|medium|low", "date": "YYYY-MM-DD" }}
  ]
}}

RULES:
- Only include NEW events NOT already in the system (compare against lastTimelineDate/lastAction)
- Match files to notes: FL -> FL-095108177, OR -> OR-431445777, Texas/TX -> TX-511048346
- If no new information found, return empty changes array
- Generate notifications for: new decisions, issues, milestones, overdue items
- Be concise. Return ONLY the JSON object."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in message.content if hasattr(block, "text"))
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return json.loads(text.strip())


def fallback_parse(file_contents, existing_notes):
    """Simple fallback if AI parsing is unavailable."""
    today = datetime.now().strftime("%Y-%m-%d")
    changes = []
    notifications = []

    for fc in file_contents:
        note_id = fc.get("note_id")
        note_label = fc.get("note_label", "Unknown")
        if not note_id:
            continue
        note = next((n for n in existing_notes if n["id"] == note_id), None)
        if not note:
            continue

        changes.append({
            "noteId": note_id,
            "newEvents": [{
                "date": today,
                "action": f"Weekly email file uploaded: {fc['name']}",
                "from": "System",
                "type": "new_upload",
            }],
            "newFollowUps": [],
            "statusSuggestion": None,
            "summaryUpdate": None,
        })
        notifications.append({
            "message": f"New email file uploaded for {note_label}: {fc['name']}",
            "noteLabel": note_label,
            "noteStatus": note["status"],
            "severity": "low",
            "date": today,
        })

    return {"changes": changes, "notifications": notifications}


def apply_changes(notes, notifs, result):
    """Apply parsed changes to notes and notifications."""
    updated_notes = [n.copy() for n in notes]
    new_notifs = list(notifs)

    for change in result.get("changes", []):
        idx = next((i for i, n in enumerate(updated_notes) if n["id"] == change["noteId"]), None)
        if idx is None:
            continue

        note = {**updated_notes[idx]}
        note["timeline"] = list(note["timeline"])
        note["followUps"] = list(note["followUps"])

        if change.get("newEvents"):
            existing_keys = {
                e["date"] + e["action"][:30] for e in note["timeline"]
            }
            for ev in change["newEvents"]:
                key = ev["date"] + ev.get("action", "")[:30]
                if key not in existing_keys:
                    note["timeline"].append(ev)

        if change.get("newFollowUps"):
            for fu in change["newFollowUps"]:
                fu["completed"] = False
                note["followUps"].append(fu)

        if change.get("statusSuggestion"):
            note["status"] = change["statusSuggestion"]

        if change.get("summaryUpdate"):
            note["summary"] = change["summaryUpdate"]

        updated_notes[idx] = note

    for n in result.get("notifications", []):
        new_notifs.insert(0, n)

    return updated_notes, new_notifs


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');

    .stApp { font-family: 'DM Sans', sans-serif; }

    .metric-card {
        background: #f8f7f4;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-card .label { font-size: 12px; color: #888; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-card .value { font-size: 28px; font-weight: 600; margin-top: 2px; }
    .metric-card .value.danger { color: #E24B4A; }

    .note-card {
        background: white;
        border: 1px solid #e8e6e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
        transition: border-color 0.2s;
    }
    .note-card:hover { border-color: #378ADD; }
    .note-card .title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
    .note-card .subtitle { font-size: 13px; color: #888; }
    .note-card .summary { font-size: 13px; color: #666; margin-top: 8px; line-height: 1.6; }
    .note-card .meta { font-size: 12px; color: #aaa; margin-top: 10px; display: flex; gap: 16px; }
    .note-card .meta .overdue { color: #E24B4A; font-weight: 600; }

    .status-pill {
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
    }

    .timeline-item {
        position: relative;
        padding-left: 24px;
        padding-bottom: 16px;
        border-left: 2px solid #e8e6e0;
        margin-left: 8px;
    }
    .timeline-item:last-child { border-left: 2px solid transparent; }
    .timeline-item .dot {
        position: absolute;
        left: -7px;
        top: 4px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 2px solid white;
    }
    .timeline-item .date { font-size: 12px; color: #aaa; }
    .timeline-item .from { font-size: 11px; color: #999; }
    .timeline-item .action { font-size: 13px; line-height: 1.5; margin-top: 2px; }

    .type-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }

    .notif-item {
        padding: 12px 16px;
        border-bottom: 1px solid #f0efe8;
        display: flex;
        gap: 12px;
        align-items: flex-start;
    }
    .notif-dot {
        width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; flex-shrink: 0;
    }

    .contact-row {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        border: 1px solid #e8e6e0;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    .contact-avatar {
        width: 38px; height: 38px; border-radius: 50%;
        background: #E6F1FB; color: #378ADD;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; font-size: 13px; flex-shrink: 0;
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def render_status_pill(status):
    cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["on_hold"])
    return f'<span class="status-pill" style="background:{cfg["bg"]};color:{cfg["color"]}">{cfg["label"]}</span>'


def render_type_badge(event_type):
    color = TYPE_COLORS.get(event_type, "#888")
    label = event_type.replace("_", " ").title()
    return f'<span class="type-badge" style="background:{color}15;color:{color}">{label}</span>'


# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
if "notes" not in st.session_state:
    st.session_state.notes = load_notes()
if "notifications" not in st.session_state:
    st.session_state.notifications = load_notifications()
if "selected_note" not in st.session_state:
    st.session_state.selected_note = None
if "show_upload_results" not in st.session_state:
    st.session_state.show_upload_results = None

inject_css()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📋 NPL Note Tracker")
    st.caption("Notecraft Capital")
    st.divider()

    # ---- Notifications ----
    notif_count = len(st.session_state.notifications)
    with st.expander(f"🔔 Notifications ({notif_count})", expanded=notif_count > 0):
        if notif_count == 0:
            st.caption("No new notifications.")
        else:
            if st.button("Clear all", key="clear_notifs"):
                st.session_state.notifications = []
                save_notifications([])
                st.rerun()
            for i, n in enumerate(st.session_state.notifications[:10]):
                sev_color = {"high": "#E24B4A", "medium": "#BA7517", "low": "#378ADD"}.get(n.get("severity", "low"), "#888")
                st.markdown(f"""
                <div class="notif-item">
                    <div class="notif-dot" style="background:{sev_color}"></div>
                    <div>
                        <div style="font-size:13px;line-height:1.4">{n['message']}</div>
                        <div style="font-size:11px;color:#aaa;margin-top:4px">{n.get('noteLabel','')} · {n.get('date','')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # ---- Upload ----
    st.markdown("### 📤 Weekly email upload")
    st.caption("Supports: .docx, .eml, .msg, .txt")

    uploaded_files = st.file_uploader(
        "Drop email files here",
        type=["docx", "eml", "msg", "txt"],
        accept_multiple_files=True,
        key="email_upload",
    )

    api_key = st.text_input(
        "Anthropic API key (for AI parsing)",
        type="password",
        help="Without a key, files are logged but not AI-parsed.",
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} file(s) ready**")
        for uf in uploaded_files:
            note_id, note_label = detect_note_id(uf.name)
            tag = note_label or "?"
            st.caption(f"`{tag}` — {uf.name} ({uf.size // 1024} KB)")

        if st.button("🚀 Process emails", type="primary", use_container_width=True):
            with st.spinner("Extracting and parsing emails..."):
                file_contents = []
                for uf in uploaded_files:
                    raw = uf.read()
                    text = extract_text(raw, uf.name)
                    note_id, note_label = detect_note_id(uf.name)
                    file_contents.append({
                        "name": uf.name,
                        "content": text,
                        "note_id": note_id,
                        "note_label": note_label or "Unknown",
                    })

                if api_key:
                    try:
                        result = parse_with_claude(
                            file_contents,
                            st.session_state.notes,
                            api_key,
                        )
                    except Exception as e:
                        st.warning(f"AI parsing failed: {e}. Using fallback.")
                        result = fallback_parse(file_contents, st.session_state.notes)
                else:
                    result = fallback_parse(file_contents, st.session_state.notes)

                updated_notes, updated_notifs = apply_changes(
                    st.session_state.notes,
                    st.session_state.notifications,
                    result,
                )
                st.session_state.notes = updated_notes
                st.session_state.notifications = updated_notifs
                save_notes(updated_notes)
                save_notifications(updated_notifs)

                meta = load_meta()
                meta["last_upload"] = datetime.now().isoformat()
                meta["total_uploads"] = meta.get("total_uploads", 0) + len(uploaded_files)
                save_meta(meta)

                change_count = len(result.get("changes", []))
                notif_count = len(result.get("notifications", []))
                st.session_state.show_upload_results = {
                    "files": len(uploaded_files),
                    "changes": change_count,
                    "notifications": notif_count,
                }

            st.rerun()

    st.divider()

    # ---- Quick filters ----
    st.markdown("### Filter by status")
    filter_status = st.radio(
        "Status",
        options=["all"] + list(STATUS_CONFIG.keys()),
        format_func=lambda x: f"All ({len(st.session_state.notes)})" if x == "all" else f"{STATUS_CONFIG[x]['label']} ({sum(1 for n in st.session_state.notes if n['status'] == x)})",
        label_visibility="collapsed",
    )

    st.divider()
    meta = load_meta()
    if meta.get("last_upload"):
        try:
            last = datetime.fromisoformat(meta["last_upload"])
            st.caption(f"Last upload: {last.strftime('%b %d, %Y %I:%M %p')}")
        except Exception:
            pass
    st.caption(f"Total uploads: {meta.get('total_uploads', 0)}")


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
if st.session_state.show_upload_results:
    r = st.session_state.show_upload_results
    st.success(f"✅ Processed {r['files']} file(s) — {r['changes']} note(s) updated, {r['notifications']} notification(s) generated.")
    st.session_state.show_upload_results = None

# ---- Detail view ----
if st.session_state.selected_note:
    note = next((n for n in st.session_state.notes if n["id"] == st.session_state.selected_note), None)
    if not note:
        st.session_state.selected_note = None
        st.rerun()

    if st.button("← Back to all notes"):
        st.session_state.selected_note = None
        st.rerun()

    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.markdown(f"## {note['label']} — {note['category']}")
        st.caption(f"{note['property']}  ·  Loan: {note['loanNumber']}  ·  Note: {note['noteId']}")
    with col_status:
        new_status = st.selectbox(
            "Status",
            options=list(STATUS_CONFIG.keys()),
            index=list(STATUS_CONFIG.keys()).index(note["status"]),
            format_func=lambda x: STATUS_CONFIG[x]["label"],
            key="detail_status",
        )
        if new_status != note["status"]:
            idx = next(i for i, n in enumerate(st.session_state.notes) if n["id"] == note["id"])
            st.session_state.notes[idx]["status"] = new_status
            save_notes(st.session_state.notes)
            st.rerun()

    tab_overview, tab_timeline, tab_tasks, tab_contacts = st.tabs([
        "📄 Overview",
        f"📅 Timeline ({len(note['timeline'])})",
        f"✅ Tasks ({sum(1 for f in note['followUps'] if not f['completed'])})",
        f"👤 Contacts ({len(note['contacts'])})",
    ])

    with tab_overview:
        st.markdown("#### Summary")
        st.info(note["summary"])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Servicer</div>
                <div style="font-size:14px;font-weight:500;margin-top:4px">{note['servicer']}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">Attorney</div>
                <div style="font-size:14px;font-weight:500;margin-top:4px">{note['attorney']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card" style="margin-top:12px">
            <div class="label">Property Management</div>
            <div style="font-size:14px;font-weight:500;margin-top:4px">{note['propertyMgmt']}</div>
        </div>
        """, unsafe_allow_html=True)

    with tab_timeline:
        for ev in reversed(note["timeline"]):
            dot_color = TYPE_COLORS.get(ev.get("type", "update"), "#888")
            badge = render_type_badge(ev.get("type", "update"))
            st.markdown(f"""
            <div class="timeline-item">
                <div class="dot" style="background:{dot_color}"></div>
                <div>
                    {badge}
                    <span class="date" style="margin-left:8px">{ev['date']}</span>
                    <span class="from" style="margin-left:8px">— {ev['from']}</span>
                </div>
                <div class="action">{ev['action']}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_tasks:
        for i, fu in enumerate(note["followUps"]):
            overdue = not fu["completed"] and datetime.strptime(fu["dueDate"], "%Y-%m-%d") < datetime.now()
            pri_color = PRIORITY_COLORS.get(fu["priority"], "#888")

            col_check, col_task = st.columns([0.05, 0.95])
            with col_check:
                checked = st.checkbox(
                    "",
                    value=fu["completed"],
                    key=f"task_{note['id']}_{i}",
                )
                if checked != fu["completed"]:
                    idx = next(j for j, n in enumerate(st.session_state.notes) if n["id"] == note["id"])
                    st.session_state.notes[idx]["followUps"][i]["completed"] = checked
                    save_notes(st.session_state.notes)
                    st.rerun()
            with col_task:
                task_style = "text-decoration:line-through;opacity:0.5" if fu["completed"] else ""
                overdue_tag = '<span style="color:#E24B4A;font-weight:600;font-size:11px"> (OVERDUE)</span>' if overdue else ""
                st.markdown(
                    f'<div style="{task_style};font-size:14px">{fu["task"]}</div>'
                    f'<div style="font-size:12px;color:#999;margin-top:2px">'
                    f'Due: {fu["dueDate"]}{overdue_tag} · '
                    f'<span style="color:{pri_color};font-weight:600">{fu["priority"].upper()}</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown("#### Add task")
        col_input, col_date, col_pri, col_btn = st.columns([3, 1, 1, 0.5])
        with col_input:
            new_task = st.text_input("Task", placeholder="Describe the follow-up...", label_visibility="collapsed", key="new_task_input")
        with col_date:
            new_date = st.date_input("Due", value=datetime.now() + timedelta(days=7), label_visibility="collapsed", key="new_task_date")
        with col_pri:
            new_pri = st.selectbox("Priority", ["high", "medium", "low"], index=1, label_visibility="collapsed", key="new_task_pri")
        with col_btn:
            if st.button("Add", key="add_task_btn"):
                if new_task.strip():
                    idx = next(j for j, n in enumerate(st.session_state.notes) if n["id"] == note["id"])
                    st.session_state.notes[idx]["followUps"].append({
                        "task": new_task.strip(),
                        "dueDate": new_date.strftime("%Y-%m-%d"),
                        "priority": new_pri,
                        "completed": False,
                    })
                    save_notes(st.session_state.notes)
                    st.rerun()

    with tab_contacts:
        for c in note["contacts"]:
            initials = "".join(w[0] for w in c["name"].split() if w)[:2].upper()
            email_line = f'<div style="font-size:12px;color:#378ADD">{c["email"]}</div>' if c.get("email") else ""
            phone_line = f'<div style="font-size:12px;color:#888">{c["phone"]}</div>' if c.get("phone") else ""
            st.markdown(f"""
            <div class="contact-row">
                <div class="contact-avatar">{initials}</div>
                <div style="flex:1">
                    <div style="font-weight:600;font-size:14px">{c['name']}</div>
                    <div style="font-size:12px;color:#888">{c['role']}</div>
                </div>
                <div style="text-align:right">
                    {email_line}
                    {phone_line}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ---- List view ----
else:
    st.markdown("## NPL Note Tracker")

    notes = st.session_state.notes
    overdue_total = sum(
        1 for n in notes for f in n["followUps"]
        if not f["completed"] and datetime.strptime(f["dueDate"], "%Y-%m-%d") < datetime.now()
    )
    pending_total = sum(1 for n in notes for f in n["followUps"] if not f["completed"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Total notes</div>
            <div class="value">{len(notes)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Pending tasks</div>
            <div class="value">{pending_total}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        danger_class = " danger" if overdue_total > 0 else ""
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">Overdue</div>
            <div class="value{danger_class}">{overdue_total}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    filtered = notes if filter_status == "all" else [n for n in notes if n["status"] == filter_status]

    for note in filtered:
        s_cfg = STATUS_CONFIG.get(note["status"], STATUS_CONFIG["on_hold"])
        status_html = render_status_pill(note["status"])
        pend = sum(1 for f in note["followUps"] if not f["completed"])
        od = sum(
            1 for f in note["followUps"]
            if not f["completed"] and datetime.strptime(f["dueDate"], "%Y-%m-%d") < datetime.now()
        )
        last_date = note["timeline"][-1]["date"] if note["timeline"] else "—"
        overdue_html = f'<span class="overdue">{od} overdue</span>' if od > 0 else ""

        st.markdown(f"""
        <div class="note-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                    <div class="title">{note['label']} — {note['category']}</div>
                    <div class="subtitle">{note['property']}</div>
                </div>
                {status_html}
            </div>
            <div class="summary">{note['summary'][:160]}{'...' if len(note['summary']) > 160 else ''}</div>
            <div class="meta">
                <span>{pend} pending</span>
                {overdue_html}
                <span>{len(note['timeline'])} events</span>
                <span>Last: {last_date}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Open {note['label']} →", key=f"open_{note['id']}"):
            st.session_state.selected_note = note["id"]
            st.rerun()
