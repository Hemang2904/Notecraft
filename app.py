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
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(
    page_title="NPL Note Tracker — Notecraft Capital",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

PRIORITY_COLORS = {"high": "#E24B4A", "medium": "#BA7517", "low": "#888780"}

TYPE_COLORS = {
    "update": "#378ADD", "decision": "#534AB7", "follow_up": "#BA7517",
    "milestone": "#639922", "issue": "#E24B4A", "acknowledgment": "#888780",
    "new_upload": "#0F6E56",
}

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
        "summary": "Yard brush/tree cleanup required for HOA compliance. First bid $1,920 (Left Coast Pres), deemed too high. Contractor revised to $700. Waiting on 2nd bid. HOA treasurer John Giovanni flagged rodent concerns from overgrowth. Goal: minimal work — property may become REO (in foreclosure). Russell Wilde offered bi-weekly maintenance schedule option.",
        "contacts": [
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Russell Wilde", "role": "Senior Asset Manager (South Watuppa)", "email": "rwilde@reo-consult.com", "phone": "503-855-7252"},
            {"name": "Cliff Ponte", "role": "Default Consultant / Broker (KW)", "email": "cponte@kw.com", "phone": ""},
            {"name": "Nishit", "role": "Notecraft Team", "email": "nishit@notecraftcapital.com", "phone": ""},
            {"name": "Rushabh Sheth", "role": "Notecraft Team", "email": "rushabh@notecraftcapital.com", "phone": ""},
            {"name": "John Giovanni", "role": "HOA Treasurer", "email": "", "phone": ""},
            {"name": "Rachel Mott", "role": "Foreclosure Specialist (LandHome)", "email": "Rachel.Mott@LHFS.com", "phone": "+1 562-203-7949"},
            {"name": "Constantine Pavlakis", "role": "LandHome Rep", "email": "Constantine.Pavlakis@LHFS.com", "phone": ""},
        ],
        "timeline": [
            {"date": "2026-01-30", "action": "Abhi requested reinstatement and payoff figures for Loan 5926000002. Cross-reference with FL property.", "from": "Abhi Sheth", "type": "update"},
            {"date": "2026-01-30", "action": "Rachel Mott confirmed FL loan (#5926000001) already in foreclosure with Waldman Law. Property managed by Cliff Pointe Inc.", "from": "Rachel Mott", "type": "update"},
            {"date": "2026-01-31", "action": "Constantine acknowledged loan transfer and foreclosure status.", "from": "Constantine Pavlakis", "type": "acknowledgment"},
            {"date": "2026-02-10", "action": "Abhi contacted Cliff Ponte about HOA overgrowth complaint. John Giovanni (HOA treasurer) flagged rodent concerns. Photos attached.", "from": "Abhi Sheth", "type": "issue"},
            {"date": "2026-02-10", "action": "Cliff introduced Russell Wilde as assigned asset manager for Notecraft properties. Requested local agent to get bid on rush.", "from": "Cliff Ponte", "type": "update"},
            {"date": "2026-02-10", "action": "Russell acknowledged and began requesting estimates from local agent.", "from": "Russell Wilde", "type": "acknowledgment"},
            {"date": "2026-02-12", "action": "First bid received: Left Coast Pres at $1,920 for exterior cleanup. Photos attached. Russell requested 2nd bid due to high amount. Offered bi-weekly maintenance schedule option.", "from": "Russell Wilde", "type": "milestone"},
            {"date": "2026-02-18", "action": "Abhi followed up on 2nd bid status. Emphasized minimal/simple cleanup needed — just to keep HOA from complaining. Property may become REO.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-02-18", "action": "Original contractor revised bid down to $700 for major HOA issues. 2nd contractor bid expected in 1-2 days. Revised bid PDF attached.", "from": "Russell Wilde", "type": "update"},
            {"date": "2026-02-18", "action": "Abhi acknowledged revised $700 quote. Agreed to wait for 2nd bid before making decision.", "from": "Abhi Sheth", "type": "decision"},
        ],
        "followUps": [
            {"task": "Receive 2nd contractor bid for yard cleanup", "dueDate": "2026-02-22", "priority": "high", "completed": False},
            {"task": "Compare both bids and approve one (target: under $700)", "dueDate": "2026-02-25", "priority": "high", "completed": False},
            {"task": "Consider bi-weekly maintenance schedule for ongoing HOA compliance", "dueDate": "2026-03-01", "priority": "medium", "completed": False},
            {"task": "Confirm HOA compliance after cleanup completed", "dueDate": "2026-03-15", "priority": "medium", "completed": False},
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
        "summary": "Forced Place Insurance needed for all 3 newly boarded loans at LandHome. FPI thread started Dec 30, 2025. Multiple follow-ups by Abhi (Jan 6, 12, 26, 27, Feb 5). Jeanne Drake responded Jan 12 with status. Constantine touched base Jan 27. Constantine shared quotes Feb 5 — awaiting: (1) ACH/wiring instructions, (2) confirmation coverage began at loan boarding. Separately, Loan 5926000002 transferred to ZBS per Rachel Mott. FL and TX loans in foreclosure with Waldman Law.",
        "contacts": [
            {"name": "Constantine Pavlakis", "role": "LandHome Rep", "email": "Constantine.Pavlakis@LHFS.com", "phone": ""},
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Rachel Mott", "role": "Foreclosure Specialist (LandHome)", "email": "Rachel.Mott@LHFS.com", "phone": "+1 562-203-7949"},
            {"name": "Jeanne Drake", "role": "LandHome Insurance", "email": "Jeanne.Drake@LHFS.com", "phone": ""},
            {"name": "Crystin Sims", "role": "LandHome Insurance", "email": "Crystin.Sims@LHFS.com", "phone": ""},
            {"name": "Samantha Schechter", "role": "LandHome", "email": "Samantha.Schechter@LHFS.com", "phone": ""},
            {"name": "Joe LaBruna", "role": "LandHome", "email": "Joe.LaBruna@lhfs.com", "phone": ""},
            {"name": "Jennifer Lavoie", "role": "ZBS Law", "email": "jlavoie@zbslaw.com", "phone": ""},
            {"name": "Gonzalo Bozo Valenzuela", "role": "Oak Harbor Capital", "email": "GValenzuela@oakharborcapital.com", "phone": ""},
            {"name": "Chris Wittrig", "role": "LandHome", "email": "chris.wittrig@lhfs.com", "phone": ""},
            {"name": "Emma Brookman", "role": "Oak Harbor Capital", "email": "EBrookman@oakharborcapital.com", "phone": ""},
        ],
        "timeline": [
            {"date": "2025-12-30", "action": "Abhi initiated FPI follow-up for all 3 newly boarded LandHome loans (#5926000001, #5926000002, #5926000003).", "from": "Abhi Sheth", "type": "milestone"},
            {"date": "2026-01-06", "action": "Abhi followed up on FPI status with Jeanne Drake and Crystin Sims.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-01-12", "action": "Abhi followed up again on FPI with Jeanne and Crystin.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-01-12", "action": "Jeanne Drake responded with FPI status update.", "from": "Jeanne Drake", "type": "update"},
            {"date": "2026-01-12", "action": "Abhi thanked Jeanne for the update on FPI status.", "from": "Abhi Sheth", "type": "acknowledgment"},
            {"date": "2026-01-26", "action": "Abhi circled back — 2 weeks since last update. Requested FPI status from Jeanne and Crystin.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-01-27", "action": "Abhi added Constantine for awareness and follow-up on FPI.", "from": "Abhi Sheth", "type": "update"},
            {"date": "2026-01-27", "action": "Constantine touched base with Abhi. Will gather info and get back.", "from": "Constantine Pavlakis", "type": "acknowledgment"},
            {"date": "2026-01-30", "action": "Jennifer Lavoie (ZBS Law) involved in loan reinstatement/payoff discussion for Loan 5926000002.", "from": "Jennifer Lavoie", "type": "update"},
            {"date": "2026-01-30", "action": "Rachel Mott confirmed loan 5926000002 transfer to ZBS. FL and TX loans in foreclosure with Waldman Law / Cliff Pointe Inc.", "from": "Rachel Mott", "type": "milestone"},
            {"date": "2026-01-31", "action": "Constantine acknowledged Rachel's update on loan transfers.", "from": "Constantine Pavlakis", "type": "acknowledgment"},
            {"date": "2026-02-05", "action": "Abhi followed up requesting FPI status update from Constantine.", "from": "Abhi Sheth", "type": "follow_up"},
            {"date": "2026-02-05", "action": "Constantine shared FPI insurance quotes with Abhi. Requested from Jeanne: (1) ACH/wiring instructions for payment, (2) confirmation coverage began at loan boarding.", "from": "Constantine Pavlakis", "type": "update"},
        ],
        "followUps": [
            {"task": "Jeanne Drake to provide ACH/wiring instructions for FPI payment", "dueDate": "2026-02-12", "priority": "high", "completed": False},
            {"task": "Confirm FPI coverage retroactive to loan boarding date", "dueDate": "2026-02-12", "priority": "high", "completed": False},
            {"task": "Make FPI payment once instructions received", "dueDate": "2026-02-15", "priority": "high", "completed": False},
            {"task": "Follow up with ZBS Law on Loan 5926000002 reinstatement/payoff", "dueDate": "2026-02-15", "priority": "medium", "completed": False},
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
        "summary": "HECM NPL legal review. Extended exchange Jan 6-Feb 3. Damian provided HE Affidavit for review and signing. Indemnity letter from Old Republic received Jan 31 (Fcl Indem TEXAS Wolfson.pdf) — insurance covers the lien, clearing foreclosure path. However, address has transposed digits (Divinia Sabal error). Damian agreed Feb 3 to request correction. Invoice for title claim requested under 'Notecraft Capital Special Opportunities Fund I' referencing property and HECM loan 511-048346 for HUD reimbursement.",
        "contacts": [
            {"name": "Damian Waldman", "role": "Attorney (Waldman Law)", "email": "damian@dwaldmanlaw.com", "phone": "(727) 538-4160"},
            {"name": "Abhi Sheth", "role": "Asset Manager (Notecraft)", "email": "abhi@notecraftcapital.com", "phone": "206-679-8734"},
            {"name": "Nishit", "role": "Notecraft Team", "email": "nishit@notecraftcapital.com", "phone": ""},
            {"name": "Rushabh Sheth", "role": "Notecraft Team", "email": "rushabh@notecraftcapital.com", "phone": ""},
            {"name": "Divinia Sabal", "role": "Claims Admin (Old Republic)", "email": "", "phone": ""},
            {"name": "Waldman Law Accounting", "role": "Accounting Dept", "email": "accounting@dwaldmanlaw.com", "phone": ""},
            {"name": "Waldman Texas Office", "role": "Texas Affiliate", "email": "texasforeclosures@dwaldmanlaw.com", "phone": "(844) 899-4162"},
        ],
        "timeline": [
            {"date": "2026-01-06", "action": "Damian provided initial update on HECM NPL legal review for TX property.", "from": "Damian Waldman", "type": "update"},
            {"date": "2026-01-06", "action": "Abhi responded to Damian's legal review update.", "from": "Abhi Sheth", "type": "acknowledgment"},
            {"date": "2026-01-25", "action": "Damian sent HE Affidavit for review and signing. Marked URGENT.", "from": "Damian Waldman", "type": "milestone"},
            {"date": "2026-01-26", "action": "Abhi responded regarding the affidavit.", "from": "Abhi Sheth", "type": "update"},
            {"date": "2026-01-26", "action": "Damian acknowledged and provided further update.", "from": "Damian Waldman", "type": "acknowledgment"},
            {"date": "2026-01-28", "action": "Damian discussed title claim and asked about sending invoice for HUD reimbursement.", "from": "Damian Waldman", "type": "update"},
            {"date": "2026-01-28", "action": "Abhi confirmed — invoice under 'Notecraft Capital Special Opportunities Fund I', referencing 511-048346 and property address.", "from": "Abhi Sheth", "type": "decision"},
            {"date": "2026-01-28", "action": "Damian confirmed he will prepare the invoice as specified.", "from": "Damian Waldman", "type": "acknowledgment"},
            {"date": "2026-01-31", "action": "Damian sent letter of indemnity from Old Republic (Fcl Indem TEXAS Wolfson.pdf). Insurance covers the lien — free to foreclose.", "from": "Damian Waldman", "type": "milestone"},
            {"date": "2026-02-02", "action": "Abhi flagged incorrect address in indemnity letter — digits transposed by Divinia Sabal (Claims Admin). Requested corrected letter from Old Republic.", "from": "Abhi Sheth", "type": "issue"},
            {"date": "2026-02-03", "action": "Damian confirmed: will request corrected letter from Old Republic.", "from": "Damian Waldman", "type": "acknowledgment"},
        ],
        "followUps": [
            {"task": "Receive corrected indemnity letter with correct property address from Old Republic", "dueDate": "2026-02-10", "priority": "high", "completed": False},
            {"task": "Receive invoice for title claim (Notecraft Capital SOF I) for HUD reimbursement", "dueDate": "2026-02-15", "priority": "medium", "completed": False},
            {"task": "Proceed with foreclosure once corrected letter confirmed", "dueDate": "2026-02-20", "priority": "high", "completed": False},
            {"task": "Coordinate with LandHome on foreclosure timeline", "dueDate": "2026-02-28", "priority": "medium", "completed": False},
        ],
    },
]


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


def extract_text_from_docx(file_bytes, filename):
    import docx, io
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

def extract_text_from_eml(file_bytes, filename):
    import email as emailmod
    from email import policy
    msg = emailmod.message_from_bytes(file_bytes, policy=policy.default)
    parts = [f"{h}: {msg[h]}" for h in ["Subject","From","To","Date"] if msg[h]]
    parts.append("")
    body = msg.get_body(preferencelist=("plain","html"))
    if body:
        c = body.get_content()
        parts.append(c.decode("utf-8", errors="replace") if isinstance(c, bytes) else c)
    return "\n".join(parts)

def extract_text_from_msg(file_bytes, filename):
    try:
        import extract_msg, tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tmp:
            tmp.write(file_bytes)
            tp = tmp.name
        try:
            msg = extract_msg.Message(tp)
            parts = [f"{l}: {getattr(msg,a,'')}" for a,l in [("subject","Subject"),("sender","From"),("to","To"),("date","Date")] if getattr(msg,a,None)]
            parts.append("")
            if msg.body:
                parts.append(msg.body)
            msg.close()
            return "\n".join(parts)
        finally:
            os.unlink(tp)
    except ImportError:
        return f"[Cannot parse .msg — install extract-msg]\nFilename: {filename}"

def extract_text(file_bytes, filename):
    ext = Path(filename).suffix.lower()
    if ext == ".docx": return extract_text_from_docx(file_bytes, filename)
    elif ext == ".eml": return extract_text_from_eml(file_bytes, filename)
    elif ext == ".msg": return extract_text_from_msg(file_bytes, filename)
    return file_bytes.decode("utf-8", errors="replace")

def detect_note_id(filename):
    name = filename.upper()
    if "FL" in name or "FLORIDA" in name: return "FL-095108177", "Florida"
    elif "OR" in name or "ORLANDO" in name: return "OR-431445777", "Orlando"
    elif "TX" in name or "TEXAS" in name: return "TX-511048346", "Texas"
    return None, None


def parse_with_claude(file_contents, existing_notes, api_key):
    import anthropic
    es = [{"id":n["id"],"state":n["state"],"label":n["label"],"property":n["property"],"category":n["category"],"lastDate":(n["timeline"][-1]["date"] if n["timeline"] else "?"),"lastAction":(n["timeline"][-1]["action"][:60] if n["timeline"] else "none"),"pending":[f["task"] for f in n["followUps"] if not f["completed"]]} for n in existing_notes]
    ft = "\n\n".join(f"--- {fc['name']} ({fc['note_label']}) ---\n{fc['content'][:8000]}" for fc in file_contents)
    prompt = f"""Email parser for NPL tracking. EXISTING:\n{json.dumps(es,indent=2)}\n\nNEW EMAILS:\n{ft}\n\nReturn ONLY JSON: {{"changes":[{{"noteId":"...","newEvents":[{{"date":"YYYY-MM-DD","action":"...","from":"...","type":"update|decision|follow_up|milestone|issue|acknowledgment"}}],"newFollowUps":[{{"task":"...","dueDate":"YYYY-MM-DD","priority":"high|medium|low"}}],"statusSuggestion":"...|null","summaryUpdate":"...|null"}}],"notifications":[{{"message":"...","noteLabel":"...","noteStatus":"...","severity":"high|medium|low","date":"YYYY-MM-DD"}}]}}
Only NEW events. FL->FL-095108177, OR->OR-431445777, TX->TX-511048346."""
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=2000, messages=[{"role":"user","content":prompt}])
    text = "".join(b.text for b in msg.content if hasattr(b,"text"))
    return json.loads(re.sub(r"```json\s*|```\s*$","",text).strip())

def fallback_parse(file_contents, existing_notes):
    today = datetime.now().strftime("%Y-%m-%d")
    ch, no = [], []
    for fc in file_contents:
        nid, nl = fc.get("note_id"), fc.get("note_label","?")
        if not nid: continue
        note = next((n for n in existing_notes if n["id"]==nid), None)
        if not note: continue
        ch.append({"noteId":nid,"newEvents":[{"date":today,"action":f"Email uploaded: {fc['name']}","from":"System","type":"new_upload"}],"newFollowUps":[],"statusSuggestion":None,"summaryUpdate":None})
        no.append({"message":f"Email file for {nl}: {fc['name']}","noteLabel":nl,"noteStatus":note["status"],"severity":"low","date":today})
    return {"changes":ch,"notifications":no}

def apply_changes(notes, notifs, result):
    updated = [dict(n) for n in notes]
    nn = list(notifs)
    for c in result.get("changes",[]):
        idx = next((i for i,n in enumerate(updated) if n["id"]==c["noteId"]), None)
        if idx is None: continue
        note = {**updated[idx], "timeline":list(updated[idx]["timeline"]), "followUps":list(updated[idx]["followUps"])}
        if c.get("newEvents"):
            ek = {e["date"]+e["action"][:30] for e in note["timeline"]}
            for ev in c["newEvents"]:
                if ev["date"]+ev.get("action","")[:30] not in ek:
                    note["timeline"].append(ev)
        if c.get("newFollowUps"):
            for fu in c["newFollowUps"]:
                note["followUps"].append({**fu,"completed":False})
        if c.get("statusSuggestion"): note["status"] = c["statusSuggestion"]
        if c.get("summaryUpdate"): note["summary"] = c["summaryUpdate"]
        updated[idx] = note
    for n in result.get("notifications",[]): nn.insert(0,n)
    return updated, nn


def inject_css():
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; }
    .mc { border-radius:12px;padding:16px 20px;text-align:center; }
    .mc .l { font-size:12px;color:#888;font-weight:500;text-transform:uppercase;letter-spacing:.5px; }
    .mc .v { font-size:28px;font-weight:600;margin-top:2px; }
    .mc .v.d { color:#E24B4A; }
    .nc { border:1px solid rgba(128,128,128,.2);border-radius:12px;padding:20px;margin-bottom:12px; }
    .sp { display:inline-block;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px; }
    .tli { padding:0 0 16px 24px;border-left:2px solid rgba(128,128,128,.2);margin-left:8px;position:relative; }
    .tli:last-child { border-left-color:transparent; }
    .tld { position:absolute;left:-7px;top:4px;width:12px;height:12px;border-radius:50%; }
    .tb { display:inline-block;font-size:10px;font-weight:600;padding:2px 8px;border-radius:4px;text-transform:uppercase;letter-spacing:.3px; }
    </style>""", unsafe_allow_html=True)


def sp_html(s):
    c = STATUS_CONFIG.get(s, STATUS_CONFIG["on_hold"])
    return f'<span class="sp" style="background:{c["bg"]};color:{c["color"]}">{c["label"]}</span>'

def tb_html(t):
    c = TYPE_COLORS.get(t,"#888")
    return f'<span class="tb" style="background:{c}15;color:{c}">{t.replace("_"," ").title()}</span>'


if "notes" not in st.session_state: st.session_state.notes = load_notes()
if "notifications" not in st.session_state: st.session_state.notifications = load_notifications()
if "selected_note" not in st.session_state: st.session_state.selected_note = None
if "upload_result" not in st.session_state: st.session_state.upload_result = None

inject_css()


with st.sidebar:
    st.markdown("### 📋 NPL Note Tracker")
    st.caption("Notecraft Capital")
    st.divider()
    nc = len(st.session_state.notifications)
    with st.expander(f"🔔 Notifications ({nc})", expanded=nc > 0):
        if nc == 0: st.caption("No new notifications.")
        else:
            if st.button("Clear all", key="cn"):
                st.session_state.notifications = []
                save_notifications([])
                st.rerun()
            for n in st.session_state.notifications[:10]:
                sc = {"high":"#E24B4A","medium":"#BA7517"}.get(n.get("severity"),"#378ADD")
                st.markdown(f'<div style="padding:10px 0;border-bottom:1px solid rgba(128,128,128,.15)"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{sc};margin-right:8px;vertical-align:middle"></span><span style="font-size:13px">{n["message"]}</span><div style="font-size:11px;color:#aaa;margin-top:4px">{n.get("noteLabel","")} &middot; {n.get("date","")}</div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### 📤 Weekly email upload")
    st.caption("Supports: .docx, .eml, .msg, .txt")
    uploaded = st.file_uploader("Drop email files", type=["docx","eml","msg","txt"], accept_multiple_files=True, key="up")
    api_key = st.text_input("Anthropic API key", type="password", help="Optional. Without key, files logged but not AI-parsed.")
    if uploaded:
        st.markdown(f"**{len(uploaded)} file(s) ready**")
        for uf in uploaded:
            _,nl = detect_note_id(uf.name)
            st.caption(f"`{nl or '?'}` — {uf.name} ({uf.size//1024} KB)")
        if st.button("🚀 Process emails", type="primary", use_container_width=True):
            with st.spinner("Parsing..."):
                fcs = []
                for uf in uploaded:
                    raw = uf.read()
                    text = extract_text(raw, uf.name)
                    nid,nl = detect_note_id(uf.name)
                    fcs.append({"name":uf.name,"content":text,"note_id":nid,"note_label":nl or "?"})
                try:
                    result = parse_with_claude(fcs, st.session_state.notes, api_key) if api_key else fallback_parse(fcs, st.session_state.notes)
                except Exception as e:
                    st.warning(f"AI parse failed: {e}. Fallback used.")
                    result = fallback_parse(fcs, st.session_state.notes)
                un,unot = apply_changes(st.session_state.notes, st.session_state.notifications, result)
                st.session_state.notes = un; st.session_state.notifications = unot
                save_notes(un); save_notifications(unot)
                m = load_meta(); m["last_upload"] = datetime.now().isoformat(); m["total_uploads"] = m.get("total_uploads",0)+len(uploaded); save_meta(m)
                st.session_state.upload_result = {"f":len(uploaded),"c":len(result.get("changes",[])),"n":len(result.get("notifications",[]))}
            st.rerun()
    st.divider()
    st.markdown("### Filter by status")
    fst = st.radio("Status",["all"]+list(STATUS_CONFIG.keys()), format_func=lambda x: f"All ({len(st.session_state.notes)})" if x=="all" else f"{STATUS_CONFIG[x]['label']} ({sum(1 for n in st.session_state.notes if n['status']==x)})", label_visibility="collapsed")
    st.divider()
    m = load_meta()
    if m.get("last_upload"):
        try: st.caption(f"Last upload: {datetime.fromisoformat(m['last_upload']).strftime('%b %d, %Y %I:%M %p')}")
        except: pass
    st.caption(f"Total uploads: {m.get('total_uploads',0)}")


if st.session_state.upload_result:
    r = st.session_state.upload_result
    st.success(f"✅ Processed {r['f']} file(s) — {r['c']} note(s) updated, {r['n']} notification(s).")
    st.session_state.upload_result = None

if st.session_state.selected_note:
    note = next((n for n in st.session_state.notes if n["id"]==st.session_state.selected_note), None)
    if not note: st.session_state.selected_note = None; st.rerun()

    if st.button("← Back to all notes"): st.session_state.selected_note = None; st.rerun()

    c1,c2 = st.columns([3,1])
    with c1:
        st.markdown(f"## {note['label']} — {note['category']}")
        st.caption(f"{note['property']}  ·  Loan: {note['loanNumber']}  ·  Note: {note['noteId']}")
    with c2:
        ns = st.selectbox("Status", list(STATUS_CONFIG.keys()), index=list(STATUS_CONFIG.keys()).index(note["status"]), format_func=lambda x: STATUS_CONFIG[x]["label"], key="ds")
        if ns != note["status"]:
            ix = next(i for i,n in enumerate(st.session_state.notes) if n["id"]==note["id"])
            st.session_state.notes[ix]["status"] = ns; save_notes(st.session_state.notes); st.rerun()

    t1,t2,t3,t4 = st.tabs(["📄 Overview", f"📅 Timeline ({len(note['timeline'])})", f"✅ Tasks ({sum(1 for f in note['followUps'] if not f['completed'])})", f"👤 Contacts ({len(note['contacts'])})"])

    with t1:
        st.markdown("#### Summary")
        st.info(note["summary"])
        co1,co2 = st.columns(2)
        with co1: st.metric("Servicer", note["servicer"])
        with co2: st.metric("Attorney", note["attorney"])
        st.metric("Property Management", note["propertyMgmt"])

    with t2:
        for ev in reversed(note["timeline"]):
            dc = TYPE_COLORS.get(ev.get("type","update"),"#888")
            st.markdown(f'<div class="tli"><div class="tld" style="background:{dc}"></div>{tb_html(ev.get("type","update"))}<span style="font-size:12px;color:#aaa;margin-left:8px">{ev["date"]}</span><span style="font-size:11px;color:#999;margin-left:8px">— {ev["from"]}</span><div style="font-size:13px;line-height:1.5;margin-top:2px">{ev["action"]}</div></div>', unsafe_allow_html=True)

    with t3:
        for i,fu in enumerate(note["followUps"]):
            od = not fu["completed"] and datetime.strptime(fu["dueDate"],"%Y-%m-%d") < datetime.now()
            pc = PRIORITY_COLORS.get(fu["priority"],"#888")
            ck,tx = st.columns([0.05,0.95])
            with ck:
                ch = st.checkbox("", value=fu["completed"], key=f"t_{note['id']}_{i}")
                if ch != fu["completed"]:
                    ix = next(j for j,n in enumerate(st.session_state.notes) if n["id"]==note["id"])
                    st.session_state.notes[ix]["followUps"][i]["completed"] = ch; save_notes(st.session_state.notes); st.rerun()
            with tx:
                s = "text-decoration:line-through;opacity:0.5" if fu["completed"] else ""
                ot = ' <span style="color:#E24B4A;font-weight:600;font-size:11px">(OVERDUE)</span>' if od else ""
                st.markdown(f'<div style="{s};font-size:14px">{fu["task"]}</div><div style="font-size:12px;color:#999;margin-top:2px">Due: {fu["dueDate"]}{ot} &middot; <span style="color:{pc};font-weight:600">{fu["priority"].upper()}</span></div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("#### Add task")
        a1,a2,a3,a4 = st.columns([3,1,1,0.5])
        with a1: nt = st.text_input("Task", placeholder="Describe follow-up...", label_visibility="collapsed", key="ni")
        with a2: nd = st.date_input("Due", value=datetime.now()+timedelta(days=7), label_visibility="collapsed", key="nd")
        with a3: np_ = st.selectbox("Pri",["high","medium","low"], index=1, label_visibility="collapsed", key="np")
        with a4:
            if st.button("Add", key="nb") and nt.strip():
                ix = next(j for j,n in enumerate(st.session_state.notes) if n["id"]==note["id"])
                st.session_state.notes[ix]["followUps"].append({"task":nt.strip(),"dueDate":nd.strftime("%Y-%m-%d"),"priority":np_,"completed":False})
                save_notes(st.session_state.notes); st.rerun()

    with t4:
        for c in note["contacts"]:
            ini = "".join(w[0] for w in c["name"].split() if w)[:2].upper()
            info = []
            if c.get("email"): info.append(f'<span style="color:#378ADD;font-size:12px">{c["email"]}</span>')
            if c.get("phone"): info.append(f'<span style="color:#888;font-size:12px">{c["phone"]}</span>')
            ih = "<br>".join(info) if info else ""
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid rgba(128,128,128,.2);border-radius:10px;margin-bottom:8px">'
                f'<div style="width:38px;height:38px;border-radius:50%;background:#E6F1FB;color:#378ADD;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:13px;flex-shrink:0">{ini}</div>'
                f'<div style="flex:1"><div style="font-weight:600;font-size:14px">{c["name"]}</div><div style="font-size:12px;color:#888">{c["role"]}</div></div>'
                f'<div style="text-align:right">{ih}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

else:
    st.markdown("## NPL Note Tracker")
    notes = st.session_state.notes
    ot = sum(1 for n in notes for f in n["followUps"] if not f["completed"] and datetime.strptime(f["dueDate"],"%Y-%m-%d")<datetime.now())
    pt = sum(1 for n in notes for f in n["followUps"] if not f["completed"])
    c1,c2,c3 = st.columns(3)
    with c1: st.markdown(f'<div class="mc"><div class="l">Total notes</div><div class="v">{len(notes)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="mc"><div class="l">Pending tasks</div><div class="v">{pt}</div></div>', unsafe_allow_html=True)
    with c3:
        dc = " d" if ot>0 else ""
        st.markdown(f'<div class="mc"><div class="l">Overdue</div><div class="v{dc}">{ot}</div></div>', unsafe_allow_html=True)
    st.markdown("")
    filtered = notes if fst=="all" else [n for n in notes if n["status"]==fst]
    for note in filtered:
        sp = sp_html(note["status"])
        pn = sum(1 for f in note["followUps"] if not f["completed"])
        od = sum(1 for f in note["followUps"] if not f["completed"] and datetime.strptime(f["dueDate"],"%Y-%m-%d")<datetime.now())
        ld = note["timeline"][-1]["date"] if note["timeline"] else "—"
        oh = f'<span style="color:#E24B4A;font-weight:600;margin-right:16px">{od} overdue</span>' if od>0 else ""
        st.markdown(
            f'<div class="nc">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
            f'<div><div style="font-size:16px;font-weight:600;margin-bottom:4px">{note["label"]} — {note["category"]}</div>'
            f'<div style="font-size:13px;color:#888">{note["property"]}</div></div>{sp}</div>'
            f'<div style="font-size:13px;color:#999;margin-top:8px;line-height:1.6">{note["summary"][:180]}{"..." if len(note["summary"])>180 else ""}</div>'
            f'<div style="font-size:12px;color:#aaa;margin-top:10px"><span style="margin-right:16px">{pn} pending</span>{oh}<span style="margin-right:16px">{len(note["timeline"])} events</span><span>Last: {ld}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(f"Open {note['label']} →", key=f"o_{note['id']}"): st.session_state.selected_note = note["id"]; st.rerun()
