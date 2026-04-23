# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import smtplib
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

st.set_page_config(
    page_title="BeautyFlow",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PROCEDURES = {
    "Makijaż okolicznościowy": {
        "tagline": "Ślubny, wieczorowy, sesja foto",
        "time": "60–90 min",
        "price": "od 250 zł",
        "effects": "Profesjonalny, trwały makijaż dopasowany do okazji i karnacji",
        "contraindications": ["alergia na kosmetyki do makijażu", "łupież powieki", "aktywne stany zapalne skóry"],
        "prep": "Przyjść z oczyszczoną, nawilżoną twarzą, bez makijażu",
        "script": [
            {"q": "Jaka to będzie okazja — ślub, event, sesja zdjęciowa?", "key": "okazja"},
            {"q": "Czy ma Pani jakieś alergie na kosmetyki lub konkretne składniki?", "key": "alergie",
             "contraindication_keywords": ["alergia", "uczulenie", "reakcja"]},
            {"q": "Czy nosi Pani soczewki kontaktowe?", "key": "soczewki"},
            {"q": "Czy ma Pani zdjęcia inspiracji lub preferowany styl makijażu?", "key": "styl"},
        ],
        "ok_message": "Wszystko brzmi dobrze — zabieg jest jak najbardziej wskazany. Chciałaby Pani wybrać termin?",
        "contraindication_message": "Rozumiem — w takim razie warto najpierw skonsultować się z naszą specjalistką. Można do nas zadzwonić: +48 500 123 456.",
    },
    "Laminacja Brwi": {
        "tagline": "Naturalne uniesienie i wypełnienie na 6–8 tyg.",
        "time": "60 min",
        "price": "od 160 zł",
        "effects": "Brwi wyglądają gęściej, są trwale uniesione i ułożone",
        "contraindications": ["alergia na utleniacze", "ciąża", "chemioterapia", "stany zapalne"],
        "prep": "Nie farbować brwi 2 tygodnie przed, przyjść bez makijażu brwi",
        "script": [
            {"q": "Czy miała Pani wcześniej laminację brwi lub inny zabieg chemiczny na brwiach?", "key": "historia_zabiegow"},
            {"q": "Czy zdarzyła się kiedyś reakcja alergiczna na kosmetyki w okolicy oczu lub brwi?", "key": "alergie",
             "contraindication_keywords": ["alergia", "uczulenie", "reakcja", "podrażnienie"]},
            {"q": "Jak określiłaby Pani swoje brwi — rzadkie, gęste, z lukami?", "key": "typ_brwi"},
            {"q": "Czy jest Pani w ciąży lub karmi piersią?", "key": "ciaza",
             "contraindication_keywords": ["tak", "jestem w ciąży", "ciąża", "karmię"]},
        ],
        "ok_message": "Wszystko brzmi dobrze — laminacja będzie świetnym wyborem. Chciałaby Pani wybrać termin?",
        "contraindication_message": "Dziękuję za szczerość — przy tym przeciwwskazaniu nie możemy wykonać zabiegu. Zapraszamy po zakończeniu ciąży lub po ustąpieniu dolegliwości. Tel: +48 500 123 456.",
    },
    "Laminacja Rzęs": {
        "tagline": "Naturalne podkręcenie na 6–8 tygodni",
        "time": "75 min",
        "price": "od 180 zł",
        "effects": "Rzęsy naturalnie podkręcone, optycznie dłuższe i gęstsze",
        "contraindications": ["alergia na kleje", "infekcje oczu", "chemioterapia"],
        "prep": "Bez tuszu do rzęs i odżywek 24h przed, bez soczewek w dniu zabiegu",
        "script": [
            {"q": "Czy miała Pani wcześniej laminację lub lifting rzęs?", "key": "historia_zabiegow"},
            {"q": "Czy zdarzyła się kiedyś reakcja alergiczna w okolicy oczu po zabiegu kosmetycznym?", "key": "alergie",
             "contraindication_keywords": ["alergia", "uczulenie", "reakcja", "podrażnienie"]},
            {"q": "Czy stosuje Pani krople do oczu lub leki okulistyczne?", "key": "krople"},
            {"q": "Jak długie są Pani naturalne rzęsy — krótkie (poniżej 4mm), średnie czy długie?", "key": "dlugosc_rzes",
             "contraindication_keywords": ["krótkie", "bardzo krótkie", "4mm", "poniżej"]},
        ],
        "ok_message": "Rzęsy nadają się do laminacji. Chciałaby Pani wybrać termin?",
        "contraindication_message": "Niestety przy takich rzęsach lub reakcji alergicznej zabieg nie byłby bezpieczny. Zapraszamy na konsultację: +48 500 123 456.",
    },
    "Henna + Regulacja Brwi": {
        "tagline": "Koloryzacja i nadanie kształtu brwiom",
        "time": "45 min",
        "price": "od 80 zł",
        "effects": "Zabarwione, wyraźne brwi z precyzyjnym kształtem",
        "contraindications": ["alergia na hennę", "PPD", "łuszczyca", "ciąża"],
        "prep": "Nie farbować brwi 2 tygodnie przed, przyjść z naturalną twarzą",
        "script": [
            {"q": "Czy robiła Pani kiedyś hennę i czy wystąpiła jakaś reakcja alergiczna?", "key": "alergie",
             "contraindication_keywords": ["alergia", "uczulenie", "reakcja", "swędzenie", "opuchlizna"]},
            {"q": "Jaki kolor brwi Pani preferuje — naturalny, ciemniejszy, ombre?", "key": "kolor"},
            {"q": "Czy ma Pani określony kształt brwi w głowie, czy zostawia Pani decyzję specjalistce?", "key": "ksztalt"},
            {"q": "Czy jest Pani w ciąży?", "key": "ciaza",
             "contraindication_keywords": ["tak", "jestem w ciąży", "ciąża"]},
        ],
        "ok_message": "Henna z regulacją to świetny wybór. Chciałaby Pani wybrać termin?",
        "contraindication_message": "Przy alergii na hennę lub ciąży nie możemy bezpiecznie wykonać zabiegu. Kontakt: +48 500 123 456.",
    },
    "Przedłużanie Rzęs (1:1)": {
        "tagline": "Klasyczne przedłużanie metodą włosek po włosku",
        "time": "120 min",
        "price": "od 220 zł",
        "effects": "Dłuższe, gęstsze rzęsy — naturalny lub dramatyczny efekt",
        "contraindications": ["alergia na klej", "infekcje oczu", "trichotillomania"],
        "prep": "Bez tuszu, odżywek i olejków na rzęsach, bez soczewek kontaktowych",
        "script": [
            {"q": "Czy nosiła Pani wcześniej przedłużane rzęsy? Jeśli tak — jak skóra reagowała?", "key": "historia_zabiegow"},
            {"q": "Czy miała Pani kiedyś alergię lub podrażnienie po kleju do rzęs?", "key": "alergie",
             "contraindication_keywords": ["alergia", "uczulenie", "reakcja", "podrażnienie", "opuchlizna"]},
            {"q": "Jaki efekt Panią interesuje — naturalne, cat eye, lisie, a może coś innego?", "key": "efekt"},
            {"q": "Czy nosi Pani na co dzień soczewki kontaktowe?", "key": "soczewki"},
        ],
        "ok_message": "Dobierzemy idealny efekt. Chciałaby Pani wybrać termin?",
        "contraindication_message": "Przy alergii na klej cyjanoakrylowy zabieg niestety nie jest możliwy. Konsultacja: +48 500 123 456.",
    },
}

PROMOTIONS = [
    "Laminacja Brwi + Henna: 220 zł (oszczędzasz 20 zł)",
    "Laminacja Brwi + Laminacja Rzęs: 320 zł",
    "Nowe klientki: -15% na pierwszy zabieg",
]

STAGE_GREETING  = "greeting"
STAGE_RETURNING = "returning"
STAGE_QUESTIONS = "questions"
STAGE_OK        = "ok"
STAGE_CONTRA    = "contra"
STAGE_SLOTS     = "slots"
STAGE_EMAIL     = "email"
STAGE_DONE      = "done"

def conversation_next(procedure, user_msg, state):
    p      = PROCEDURES[procedure]
    script = p["script"]
    stage  = state.get("stage", STAGE_GREETING)
    state  = dict(state)

    if stage == STAGE_GREETING:
        name = user_msg.strip().split()[0].capitalize() if user_msg.strip() else "Pani"
        state["name"]  = name
        state["stage"] = STAGE_RETURNING
        return f"Miło Cię poznać, {name}! Czy była już Pani u nas w salonie?", state

    if stage == STAGE_RETURNING:
        lower = user_msg.lower()
        state["returning"] = any(w in lower for w in ["tak","byłam","byłem","znam","już","bywam"])
        state["q_index"] = 0
        state["answers"] = {}
        state["stage"]   = STAGE_QUESTIONS
        first_q = script[0]["q"]
        if state["returning"]:
            return f"Miło znowu! Zadam kilka krótkich pytań przed zabiegiem.\n\n{first_q}", state
        else:
            return f"Witamy serdecznie! Zadam kilka krótkich pytań, żeby dobrze się przygotować.\n\n{first_q}", state

    if stage == STAGE_QUESTIONS:
        q_index = state.get("q_index", 0)
        answers = state.get("answers", {})
        current_q = script[q_index]
        answers[current_q["key"]] = user_msg
        state["answers"] = answers
        contra_kw = current_q.get("contraindication_keywords", [])
        if contra_kw and any(kw in user_msg.lower() for kw in contra_kw):
            state["stage"] = STAGE_CONTRA
            state["contraindication"] = True
            return p["contraindication_message"], state
        next_index = q_index + 1
        if next_index < len(script):
            state["q_index"] = next_index
            return script[next_index]["q"], state
        else:
            state["stage"] = STAGE_OK
            return p["ok_message"], state

    if stage == STAGE_OK:
        lower = user_msg.lower()
        if any(w in lower for w in ["tak","chcę","chciałabym","chciałbym","proszę","oczywiście","super","ok","yes","jasne"]):
            state["stage"] = STAGE_SLOTS
            return "__SHOW_SLOTS__", state
        else:
            state["stage"] = STAGE_EMAIL
            return "Rozumiem — może poproszę o adres email, żebym mogła przesłać podsumowanie naszej rozmowy?", state

    if stage == STAGE_EMAIL:
        if "@" in user_msg:
            state["email"] = user_msg.strip()
            state["stage"] = STAGE_DONE
            return "Dziękuję! Wyślę podsumowanie na podany adres. Gdy wszystko gotowe — kliknij przycisk **Zapisz i wyślij podsumowanie** poniżej.", state
        else:
            return "Nie rozpoznałam adresu email — czy może Pani wpisać go jeszcze raz?", state

    if stage == STAGE_SLOTS:
        return "Proszę wybrać termin z listy powyżej.", state

    return "Przepraszam, coś poszło nie tak. Proszę zadzwonić: +48 500 123 456.", state

def get_greeting_message(procedure):
    p = PROCEDURES[procedure]
    return (
        f"Cześć! Jestem Sofia, konsultantka BeautyFlow. "
        f"Zanim umówimy termin na **{procedure}**, zadam kilka krótkich pytań. "
        f"Jak mam się do Pani zwracać?"
    )

@st.cache_resource
def get_groq_client():
    try:
        return OpenAI(api_key=st.secrets["app"]["groq_api_key"], base_url="https://api.groq.com/openai/v1")
    except Exception as e:
        st.error(f"Brak klucza Groq API: {e}")
        return None

def extract_client_info(procedure, conv_state, messages):
    answers = conv_state.get("answers", {})
    result = {
        "imie":        conv_state.get("name", "—"),
        "email":       conv_state.get("email", ""),
        "telefon":     "—",
        "podsumowanie": f"Zabieg: {procedure}. " + " | ".join(f"{k}: {v}" for k, v in answers.items()),
    }
    if not result["email"]:
        for m in messages:
            if "@" in m.get("content", ""):
                for word in m["content"].split():
                    if "@" in word:
                        result["email"] = word.strip(".,!?")
                        break
    return result

# ─── CSS ───────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap');

    :root {
        --bg:       #faf9f6;
        --surface:  #ffffff;
        --surface2: #f3f2ed;
        --border:   #e6e4dc;
        --border2:  #ccc9be;
        --accent:   #1c1c1a;
        --accent2:  #0e0e0c;
        --gold:     #d4a843;
        --gold-lt:  #fdf3d8;
        --gold-dk:  #b8902e;
        --text:     #1c1c1a;
        --text2:    #6a6860;
        --text3:    #aaa89e;
        --green:    #2d6e4a;
        --red:      #b83232;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Ogranicz szerokość i wyśrodkuj */
    [data-testid="stAppViewBlockContainer"] {
        max-width: 900px !important;
        padding: 0 2rem !important;
        margin: 0 auto !important;
    }
    @media (max-width: 700px) {
        [data-testid="stAppViewBlockContainer"] { padding: 0 1rem !important; }
    }

    /* Ukryj sidebar toggle i sidebar całkowicie dla klientek */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; font-family: 'DM Sans', sans-serif !important; }

    /* Ukryj "Press Enter to apply" i keyboard hint */
    [data-testid="InputInstructions"],
    .st-emotion-cache-1gulkj5,
    small[data-testid="stWidgetLabel"] small { display: none !important; }
    .stTextInput [data-baseweb="input"] ~ div[style*="font-size"] { display: none !important; }

    h1, h2, h3 {
        font-family: 'Cormorant Garamond', serif !important;
        color: var(--text) !important;
        font-weight: 500 !important;
    }

    /* ── LOGO MARK ── */
    .bf-logo { display:flex; align-items:center; gap:12px; padding:0.4rem 0 1rem; }
    .bf-logo-mark {
        width:42px; height:42px;
        background: var(--gold);
        border-radius: 10px;
        display:flex; align-items:center; justify-content:center;
        font-family: 'Cormorant Garamond', serif;
        font-weight: 600;
        font-size: 1.1rem;
        color: #fff;
        letter-spacing: 0.01em;
        flex-shrink: 0;
        box-shadow: 0 2px 12px rgba(212,168,67,0.4);
    }
    .bf-logo-text { font-family:'Cormorant Garamond',serif; font-size:1.3rem; font-weight:500; color:#1c1c1a; letter-spacing:0.03em; line-height:1.1; }
    .bf-logo-sub  { font-size:0.6rem; letter-spacing:0.18em; color:var(--text3); text-transform:uppercase; margin-top:2px; }

    /* ── CHAT ── */
    [data-testid="stChatMessage"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
        animation: msgIn 0.22s ease forwards;
    }
    @keyframes msgIn {
        from { opacity:0; transform:translateY(8px); }
        to   { opacity:1; transform:translateY(0); }
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div { color: var(--text) !important; font-size: 1.02rem !important; line-height: 1.75 !important; }
    [data-testid="stChatMessage"] strong { color: var(--accent2) !important; font-weight: 600 !important; }

    [data-testid="stChatInputTextArea"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border2) !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1rem !important;
    }
    [data-testid="stChatInputTextArea"]:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 3px rgba(212,168,67,0.15) !important;
    }

    /* ── BUTTONS – wszystkie ── */
    .stButton > button {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1.2rem !important;
        transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
    }
    .stButton > button:hover {
        background: #333 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.18) !important;
    }
    .stButton > button p, .stButton > button span, .stButton > button div { color:#ffffff !important; }

    /* ── CTA – złoty przycisk ── */
    .cta-save-wrap .stButton > button {
        background: var(--gold) !important;
        color: #fff !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        padding: 0.75rem 2rem !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 16px rgba(212,168,67,0.4) !important;
        letter-spacing: 0.01em !important;
    }
    .cta-save-wrap .stButton > button:hover {
        background: var(--gold-dk) !important;
        color: #fff !important;
        box-shadow: 0 8px 24px rgba(212,168,67,0.5) !important;
    }
    .cta-save-wrap .stButton > button p,
    .cta-save-wrap .stButton > button span,
    .cta-save-wrap .stButton > button div { color: #fff !important; }

    /* ── SLOT BUTTONS ── */
    .slot-btn .stButton > button {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1.5px solid var(--gold) !important;
        font-size: 0.9rem !important;
    }
    .slot-btn .stButton > button:hover {
        background: var(--gold-lt) !important;
        color: var(--accent) !important;
        border-color: var(--gold-dk) !important;
    }
    .slot-btn .stButton > button p,
    .slot-btn .stButton > button span { color: var(--text) !important; }

    /* ── PROC CARDS ── */
    .proc-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 12px;
        transition: box-shadow 0.2s, border-color 0.2s, transform 0.15s;
    }
    .proc-card:hover { box-shadow:0 6px 20px rgba(0,0,0,0.07); border-color:var(--gold); transform:translateY(-2px); }
    .proc-card .name { font-family:'Cormorant Garamond',serif; font-size:1.25rem; font-weight:500; color:var(--text); margin-bottom:5px; }
    .proc-card .tag  { font-size:0.87rem; color:var(--text3); }
    .proc-card .meta { font-size:0.84rem; color:var(--text2); margin-top:11px; display:flex; gap:10px; }
    .proc-card .meta span { background:var(--surface2); border-radius:5px; padding:3px 10px; border:1px solid var(--border); }

    /* ── TICKER ── */
    .ticker-wrap { overflow:hidden; white-space:nowrap; border-radius:8px;
                   background:var(--gold-lt); border:1px solid rgba(212,168,67,0.4); padding:8px 0; margin-bottom:1.4rem; }
    .ticker-inner { display:inline-block; animation:ticker 24s linear infinite; font-size:0.82rem; color:var(--text2); }
    @keyframes ticker { 0%{transform:translateX(100vw);} 100%{transform:translateX(-100%);} }
    .ticker-dot { color:var(--gold-dk); margin:0 14px; }

    /* ── TEXT INPUTS ── */
    .stTextInput > div > div > input {
        background:var(--surface) !important; color:var(--text) !important;
        border:1px solid var(--border) !important; border-radius:8px !important;
        font-family:'DM Sans',sans-serif !important; font-size:0.9rem !important;
    }
    .stTextInput > div > div > input:focus { border-color:var(--gold) !important; box-shadow:0 0 0 3px rgba(212,168,67,0.12) !important; }
    .stSelectbox > div > div { background:var(--surface) !important; border-color:var(--border) !important; border-radius:8px !important; }

    /* Ukryj "Press ↵ Enter to apply" w date/select inputach */
    [data-testid="InputInstructions"] { display:none !important; }
    .st-emotion-cache-1gulkj5 { display:none !important; }

    hr { border-color:var(--border) !important; margin:1rem 0 !important; }
    ::-webkit-scrollbar { width:4px; }
    ::-webkit-scrollbar-thumb { background:var(--border2); border-radius:4px; }
    #MainMenu, footer { visibility:hidden; }
    [data-testid="stDecoration"] { display:none; }

    /* Sidebar labels */
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stDateInput label { font-size:0.75rem !important; color:var(--text3) !important; }
    </style>
    """, unsafe_allow_html=True)


def render_logo(size="normal"):
    small = size == "small"
    mark_size = "30px" if small else "42px"
    font_main = "0.9rem" if small else "1.3rem"
    font_sub  = "0.52rem" if small else "0.6rem"
    st.markdown(f"""
    <div class="bf-logo">
      <div class="bf-logo-mark" style="width:{mark_size};height:{mark_size};font-size:{'0.85rem' if small else '1.1rem'};">✦</div>
      <div>
        <div class="bf-logo-text" style="font-size:{font_main};">BeautyFlow</div>
        <div class="bf-logo-sub" style="font-size:{font_sub};">Studio Urody · AI Konsultant</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─── EMAIL ────────────────────────────────────────────────
EMAIL_STYLE = """
<style>
  body { font-family:'Georgia',serif; background:#faf9f6; margin:0; padding:0; }
  .wrap { max-width:540px; margin:32px auto; background:#fff; border-radius:12px; overflow:hidden; border:1px solid #e6e4dc; }
  .hdr  { background:#1c1c1a; padding:28px 36px; }
  .hdr h1 { color:#d4a843; font-size:1.5rem; margin:0; letter-spacing:0.06em; font-weight:400; font-family:'Georgia',serif; }
  .hdr p  { color:#666; font-size:0.7rem; letter-spacing:0.2em; text-transform:uppercase; margin:6px 0 0; }
  .body { padding:28px 36px; color:#1c1c1a; line-height:1.75; font-size:0.92rem; }
  .box  { background:#faf9f6; border-left:3px solid #d4a843; border-radius:6px; padding:12px 16px; margin:14px 0; font-size:0.88rem; }
  .btn  { display:inline-block; padding:12px 28px; border-radius:8px; font-family:sans-serif; font-size:0.88rem; font-weight:600; letter-spacing:0.03em; text-decoration:none; margin:6px 6px 0 0; }
  .btn-ok { background:#2d6e4a; color:#fff !important; }
  .btn-no { background:#b83232; color:#fff !important; }
  .btn-app { background:#d4a843; color:#fff !important; }
  .ftr  { background:#faf9f6; padding:16px 36px; text-align:center; color:#aaa; font-size:0.75rem; border-top:1px solid #e6e4dc; }
</style>
"""

def _send_email(to, subject, html):
    try:
        gmail_user = st.secrets["email"]["gmail_user"]
        gmail_pass = st.secrets["email"]["gmail_password"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"BeautyFlow Studio <{gmail_user}>"
        msg["To"]      = to
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(gmail_user, gmail_pass)
            s.sendmail(gmail_user, to, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Email error: {e}")
        return False

def send_consultation_emails(procedure, info):
    results = {}
    try:
        owner_email = st.secrets["app"].get("owner_email", "")
    except Exception:
        owner_email = ""
    try:
        app_url = st.secrets["app"].get("app_url", "")
    except Exception:
        app_url = ""
    try:
        st.secrets["email"]["gmail_user"]
    except Exception:
        return {"error": "brak konfiguracji email"}

    proc   = PROCEDURES.get(procedure, {})
    imie   = info.get("imie", "Klientko")
    email  = info.get("email", "")
    termin = info.get("termin", "")
    podsum = info.get("podsumowanie", "—")
    token  = info.get("token", "")
    teraz  = datetime.now().strftime("%d.%m.%Y, %H:%M")

    # Email do klientki – styl oczekiwania na potwierdzenie
    if email and "@" in email:
        termin_line = f"<br>Proponowany termin: <strong>{termin}</strong>" if termin else ""
        html_client = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
        <div class="wrap">
          <div class="hdr"><h1>BeautyFlow</h1><p>Zgłoszenie przyjęte</p></div>
          <div class="body">
            <p>Cześć, <strong>{imie}</strong>!</p>
            <p>Twoje zgłoszenie dotarło do nas. Wybrałaś:</p>
            <div class="box"><strong>{procedure}</strong><br>Czas: {proc.get('time','—')} &nbsp;·&nbsp; Cena: {proc.get('price','—')}{termin_line}</div>
            <p>Specjalistka potwierdzi termin — dostaniesz osobnego maila z potwierdzeniem i wskazówkami jak się przygotować.</p>
            <p>Masz pytania? Zadzwoń: <strong>+48 500 123 456</strong></p>
            <p style="color:#aaa;font-size:0.82rem;">— Zespół BeautyFlow</p>
          </div>
          <div class="ftr">ul. Złota 12, Warszawa · +48 500 123 456 · hello@beautyflow.pl</div>
        </div></body></html>"""
        results["client"] = _send_email(email, f"BeautyFlow – zgłoszenie: {procedure}", html_client)

    # Email do właścicielki – zawsze, z przyciskami i linkiem do apki
    if owner_email:
        action_html = ""
        app_link_html = ""

        if app_url:
            app_link_html = f"""
            <div style="margin-top:20px;">
              <a href="{app_url}" class="btn btn-app">→ Otwórz panel aplikacji</a>
            </div>"""

        if token and app_url:
            confirm_url = f"{app_url}?action=confirm&token={token}"
            reject_url  = f"{app_url}?action=reject&token={token}"
            action_html = f"""
            <div style="margin:24px 0 8px;">
              <p style="font-size:0.85rem;color:#666;margin-bottom:14px;">
                Kliknij aby podjąć decyzję — klientka automatycznie dostanie maila:
              </p>
              <a href="{confirm_url}" class="btn btn-ok">✓ Potwierdź termin</a>
              &nbsp;
              <a href="{reject_url}"  class="btn btn-no">✗ Odrzuć</a>
            </div>
            <p style="color:#aaa;font-size:0.75rem;margin-top:10px;">Linki są jednorazowe.</p>"""

        html_owner = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
        <div class="wrap">
          <div class="hdr"><h1>BeautyFlow</h1><p>Nowa rezerwacja · {teraz}</p></div>
          <div class="body">
            <div class="box">
              Imię: <strong>{imie}</strong><br>
              Email: {email or '—'} &nbsp;·&nbsp; Tel: {info.get('telefon','—')}<br>
              Zabieg: <strong>{procedure}</strong><br>
              {"Termin: <strong>" + termin + "</strong>" if termin else "Termin: <em>nie wybrany</em>"}
            </div>
            <div class="box" style="font-size:0.83rem;color:#666;">{podsum}</div>
            {action_html}
            {app_link_html}
          </div>
          <div class="ftr">BeautyFlow AI · System automatyczny</div>
        </div></body></html>"""
        results["owner"] = _send_email(
            owner_email,
            f"Nowa rezerwacja: {imie} — {procedure} ({termin or 'brak terminu'})",
            html_owner
        )
    return results

def send_status_email(booking, confirmed):
    email = booking.get("email", "")
    if not email or "@" not in email:
        return False
    imie   = booking.get("imie", "Klientko")
    zabieg = booking.get("zabieg", "—")
    termin = booking.get("termin", "—")
    proc   = PROCEDURES.get(zabieg, {})
    if confirmed:
        subj = "BeautyFlow – Twój termin potwierdzony"
        body = f"""
        <p>Twój termin jest potwierdzony!</p>
        <div class="box">Zabieg: <strong>{zabieg}</strong><br>Termin: <strong>{termin}</strong><br>Adres: ul. Złota 12, Warszawa</div>
        <div class="box"><strong>Jak się przygotować:</strong><br>{proc.get('prep','—')}</div>
        <p>Do zobaczenia! W razie pytań: <strong>+48 500 123 456</strong></p>"""
    else:
        subj = "BeautyFlow – informacja o rezerwacji"
        body = f"""
        <p>Niestety wybrany termin (<strong>{termin}</strong>) nie jest już dostępny.</p>
        <div class="box">Zabieg: <strong>{zabieg}</strong></div>
        <p>Zapraszamy do ponownego umówienia: +48 500 123 456 · hello@beautyflow.pl</p>"""
    html = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
    <div class="wrap">
      <div class="hdr"><h1>BeautyFlow</h1><p>{"Potwierdzenie terminu" if confirmed else "Informacja o rezerwacji"}</p></div>
      <div class="body">{body}<p style="color:#aaa;font-size:0.82rem;">— Zespół BeautyFlow</p></div>
      <div class="ftr">ul. Złota 12, Warszawa · +48 500 123 456</div>
    </div></body></html>"""
    return _send_email(email, subj, html)

# ─── GOOGLE SHEETS ────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"],
        )
        return gspread.authorize(creds)
    except Exception:
        return None

def get_spreadsheet():
    gc = get_sheets_client()
    if not gc: return None
    try:
        return gc.open_by_key(st.secrets["sheets"]["sheet_id"])
    except Exception:
        return None

def _get_ws(sp, name, headers):
    try:
        return sp.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sp.add_worksheet(name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        ws.format(f"A1:{chr(64+len(headers))}1", {"textFormat": {"bold": True}})
        return ws

def save_consultation(procedure, info, messages):
    try:
        sp = get_spreadsheet()
        if not sp: return False
        ws = _get_ws(sp, "Konsultacje", ["Data","Imię","Email","Telefon","Zabieg","Termin","Wiadomości","Podsumowanie","Status"])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            info.get("imie","—"), info.get("email","—"), info.get("telefon","—"),
            procedure, info.get("termin","—"), len(messages),
            info.get("podsumowanie","—"),
            "oczekuje" if info.get("termin") else "bez terminu",
        ])
        return True
    except Exception:
        return False

def load_slots_from_sheet():
    try:
        sp = get_spreadsheet()
        if not sp: return [], []
        ws_t = _get_ws(sp, "Terminy",    ["Termin","Zabieg","Status"])
        ws_r = _get_ws(sp, "Rezerwacje", ["Data","Token","Termin","Imię","Email","Telefon","Zabieg","Status"])
        slots   = [{"termin": r["Termin"], "zabieg": r.get("Zabieg",""), "zajety": r.get("Status","wolny") != "wolny"}
                   for r in ws_t.get_all_records() if r.get("Termin")]
        pending = [{"token": r.get("Token",""), "imie": r.get("Imię","?"), "email": r.get("Email",""),
                    "telefon": r.get("Telefon",""), "zabieg": r.get("Zabieg",""), "termin": r.get("Termin","")}
                   for r in ws_r.get_all_records() if r.get("Status") == "oczekuje"]
        return slots, pending
    except Exception:
        return [], []

def save_slot(termin, status="wolny", zabieg=""):
    try:
        sp = get_spreadsheet()
        if not sp: return
        ws = _get_ws(sp, "Terminy", ["Termin","Zabieg","Status"])
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Termin") == termin:
                ws.update(f"C{i}", [[status]])
                return
        ws.append_row([termin, zabieg, status])
    except Exception:
        pass

def save_pending(booking):
    try:
        sp = get_spreadsheet()
        if not sp: return
        ws = _get_ws(sp, "Rezerwacje", ["Data","Token","Termin","Imię","Email","Telefon","Zabieg","Status"])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            booking.get("token",""), booking.get("termin",""),
            booking.get("imie",""), booking.get("email",""),
            booking.get("telefon",""), booking.get("zabieg",""), "oczekuje",
        ])
    except Exception:
        pass

def update_booking_in_sheet(token, new_status):
    try:
        sp = get_spreadsheet()
        if not sp: return
        ws = sp.worksheet("Rezerwacje")
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Token") == token:
                ws.update(f"H{i}", [[new_status]])
                return
    except Exception:
        pass

# ─── URL AKCJE ────────────────────────────────────────────
def handle_url_action():
    params  = st.query_params
    action  = params.get("action", "")
    token   = params.get("token", "")
    if not action or not token: return
    pending = st.session_state.get("pending_bookings", [])
    booking = next((b for b in pending if b.get("token") == token), None)
    if action == "confirm" and booking:
        save_slot(booking.get("termin",""), "zajęty")
        update_booking_in_sheet(token, "potwierdzona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"): s["zajety"] = True
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=True)
        st.success(f"Rezerwacja potwierdzona — {booking.get('imie')} · {booking.get('termin')}")
        st.query_params.clear()
    elif action == "reject" and booking:
        save_slot(booking.get("termin",""), "wolny")
        update_booking_in_sheet(token, "odrzucona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"): s["zajety"] = False
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=False)
        st.info("Rezerwacja odrzucona — klientka poinformowana emailem.")
        st.query_params.clear()
    elif booking is None and token:
        st.warning("Link wygasł lub rezerwacja już została przetworzona.")
        st.query_params.clear()

# ─── PANEL WŁAŚCICIELKI – sidebar ─────────────────────────
def render_owner_panel():
    with st.sidebar:
        render_logo()
        st.markdown('<div style="height:1px;background:#e6e4dc;margin-bottom:1rem;"></div>', unsafe_allow_html=True)

        if "owner_auth" not in st.session_state:
            st.session_state.owner_auth = False

        if not st.session_state.owner_auth:
            st.markdown('<div style="font-size:0.8rem;color:#aaa;margin-bottom:8px;">Panel właścicielki</div>', unsafe_allow_html=True)
            pw = st.text_input("Hasło dostępu", type="password", key="opw", placeholder="Wpisz hasło...", label_visibility="collapsed")
            if st.button("Zaloguj →", key="ologin", use_container_width=True):
                try:
                    correct = st.secrets["app"]["owner_password"]
                except Exception:
                    correct = "admin"
                if pw == correct:
                    st.session_state.owner_auth = True
                    slots, pending = load_slots_from_sheet()
                    st.session_state.available_slots  = slots
                    st.session_state.pending_bookings = pending
                    st.rerun()
                else:
                    st.error("Nieprawidłowe hasło")
            return

        st.markdown('<div style="font-size:0.74rem;color:#2d6e4a;margin-bottom:12px;font-weight:500;">✓ Zalogowano</div>', unsafe_allow_html=True)

        # Status integracji
        groq_ok   = "app" in st.secrets and "groq_api_key" in st.secrets.get("app", {})
        sheets_ok = "gcp_service_account" in st.secrets
        email_ok  = "email" in st.secrets
        def dot(ok): return f'<span style="color:{"#2d6e4a" if ok else "#b83232"};font-size:0.55rem;">●</span>'
        st.markdown(f'<div style="font-size:0.72rem;color:#aaa;margin-bottom:14px;">{dot(groq_ok)} Groq &nbsp; {dot(sheets_ok)} Sheets &nbsp; {dot(email_ok)} Gmail</div>', unsafe_allow_html=True)

        # ── Dodaj termin ──
        st.markdown('<div style="font-size:0.8rem;font-weight:600;color:#1c1c1a;margin-bottom:8px;">Dodaj termin</div>', unsafe_allow_html=True)
        proc_names = list(PROCEDURES.keys())
        sel_proc = st.selectbox("Zabieg", proc_names, key="slot_proc", label_visibility="visible")
        dc1, dc2 = st.columns([3,2])
        with dc1:
            slot_date = st.date_input("Data", value=date.today(), key="slot_date_picker", format="DD.MM.YYYY", label_visibility="collapsed")
        with dc2:
            available_hours = [f"{h:02d}:{m:02d}" for h in range(9,20) for m in [0,30]]
            sel_hour = st.selectbox("Godz.", available_hours, key="slot_hour_picker", label_visibility="collapsed")

        ca, cb = st.columns(2)
        with ca:
            if st.button("Dodaj", key="addslot", use_container_width=True):
                termin_str = f"{slot_date.strftime('%d.%m.%Y')}, {sel_hour}"
                existing = [s["termin"] for s in st.session_state.get("available_slots", [])]
                if termin_str in existing:
                    st.warning("Już istnieje")
                else:
                    # POPRAWKA: dodaj jako WOLNY (nie zajęty) – widoczny dla klientek
                    st.session_state.setdefault("available_slots", []).append(
                        {"termin": termin_str, "zabieg": sel_proc, "zajety": False}
                    )
                    save_slot(termin_str, "wolny", sel_proc)
                    st.success(f"Dodano: {termin_str}")
                    st.rerun()
        with cb:
            if st.button("Wyczyść wolne", key="clrslot", use_container_width=True):
                st.session_state.available_slots = [s for s in st.session_state.get("available_slots",[]) if s["zajety"]]
                try:
                    sp = get_spreadsheet()
                    if sp:
                        ws = sp.worksheet("Terminy")
                        rows = ws.get_all_records()
                        for i in reversed([i+2 for i,r in enumerate(rows) if r.get("Status")=="wolny"]):
                            ws.delete_rows(i)
                except Exception: pass
                st.rerun()

        # Lista terminów
        slots_all = st.session_state.get("available_slots", [])
        if slots_all:
            st.markdown('<div style="height:1px;background:#e6e4dc;margin:10px 0 8px;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="font-size:0.7rem;letter-spacing:0.1em;color:#aaa;text-transform:uppercase;margin-bottom:6px;">Terminy</div>', unsafe_allow_html=True)
            by_proc = {}
            for s in slots_all:
                by_proc.setdefault(s.get("zabieg","Inne"), []).append(s)
            for proc_name, proc_slots in by_proc.items():
                st.markdown(f'<div style="font-size:0.64rem;letter-spacing:0.08em;color:#aaa;text-transform:uppercase;margin:8px 0 3px;">{proc_name}</div>', unsafe_allow_html=True)
                for s in proc_slots:
                    dot_c  = "#b83232" if s["zajety"] else "#2d6e4a"
                    status = "zajęty" if s["zajety"] else "wolny"
                    st.markdown(f'<div style="font-size:0.76rem;color:#555;padding:2px 0;"><span style="color:{dot_c};">●</span> {s["termin"]} <span style="color:#bbb;font-size:0.7rem;">({status})</span></div>', unsafe_allow_html=True)

        # ── Rezerwacje do potwierdzenia ──
        pending = st.session_state.get("pending_bookings", [])
        if pending:
            st.markdown('<div style="height:1px;background:#e6e4dc;margin:14px 0 8px;"></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.7rem;letter-spacing:0.1em;text-transform:uppercase;color:#aaa;margin-bottom:8px;">Do potwierdzenia ({len(pending)})</div>', unsafe_allow_html=True)
            for i, b in enumerate(pending):
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#1c1c1a;line-height:1.7;'
                    f'background:#faf9f6;border:1px solid #e6e4dc;border-left:3px solid #d4a843;'
                    f'border-radius:8px;padding:8px 10px;margin-bottom:8px;">'
                    f'<strong>{b.get("imie","?")}</strong><br>'
                    f'<span style="color:#666;font-size:0.72rem;">{b.get("zabieg","?")}</span><br>'
                    f'<span style="color:#aaa;font-size:0.72rem;">{b.get("termin","?")}</span><br>'
                    f'<span style="color:#aaa;font-size:0.68rem;">{b.get("email","-")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✓ Tak", key=f"ok_{i}", use_container_width=True):
                        save_slot(b.get("termin",""), "zajęty")
                        update_booking_in_sheet(b.get("token",""), "potwierdzona")
                        for s in st.session_state.get("available_slots",[]):
                            if s["termin"] == b.get("termin"): s["zajety"] = True
                        send_status_email(b, confirmed=True)
                        st.session_state.pending_bookings.pop(i)
                        st.rerun()
                with c2:
                    if st.button("✗ Nie", key=f"no_{i}", use_container_width=True):
                        save_slot(b.get("termin",""), "wolny")
                        update_booking_in_sheet(b.get("token",""), "odrzucona")
                        for s in st.session_state.get("available_slots",[]):
                            if s["termin"] == b.get("termin"): s["zajety"] = False
                        send_status_email(b, confirmed=False)
                        st.session_state.pending_bookings.pop(i)
                        st.rerun()

        st.markdown('<div style="height:1px;background:#e6e4dc;margin:14px 0 8px;"></div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        with r1:
            if st.button("↻ Odśwież", key="refresh", use_container_width=True):
                slots, pending = load_slots_from_sheet()
                st.session_state.available_slots  = slots
                st.session_state.pending_bookings = pending
                st.rerun()
        with r2:
            if st.button("Wyloguj", key="ologout", use_container_width=True):
                st.session_state.owner_auth = False
                st.rerun()

# ─── HEADER ───────────────────────────────────────────────
def render_header():
    promo_items = " <span class='ticker-dot'>·</span> ".join(PROMOTIONS)
    st.markdown(f"""
    <div style="padding:2rem 0 0.4rem;">
      <div style="font-family:'Cormorant Garamond',serif;font-size:2.6rem;font-weight:500;color:#1c1c1a;letter-spacing:0.02em;line-height:1.1;">BeautyFlow</div>
      <div style="font-size:0.72rem;letter-spacing:0.22em;color:#aaa;text-transform:uppercase;margin-top:7px;">Studio Urody · Konsultant AI</div>
    </div>
    <div style="background:#f3f2ed;border:1px solid #e6e4dc;border-radius:10px;padding:0.85rem 1.3rem;margin:1rem 0 0.6rem;font-size:0.9rem;color:#555;line-height:2.0;">
      <span style="color:#1c1c1a;font-weight:500;">ul. Złota 12, Warszawa</span>
      &nbsp;·&nbsp; +48 500 123 456 &nbsp;·&nbsp; Pon–Pt 9–20, Sob 9–16
    </div>
    <div class="ticker-wrap">
      <div class="ticker-inner">✦ Promocje: {promo_items} &nbsp;&nbsp;&nbsp; ✦ Promocje: {promo_items}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── PICKER ───────────────────────────────────────────────
def render_picker():
    if st.session_state.get("_picker_loading"):
        name     = st.session_state["_picker_loading"]
        greeting = get_greeting_message(name)
        st.session_state.chosen_procedure = name
        st.session_state.messages         = [{"role": "assistant", "content": greeting}]
        st.session_state.conv_state       = {"stage": STAGE_GREETING}
        st.session_state.saved            = False
        st.session_state.slot_chosen      = None
        st.session_state.chat_stage       = "chat"
        del st.session_state["_picker_loading"]
        st.rerun()
        return

    render_header()

    st.markdown("""
    <div style="margin:1.2rem 0 1rem;">
      <div style="font-family:'Cormorant Garamond',serif;font-size:1.9rem;font-weight:500;color:#1c1c1a;line-height:1.2;margin-bottom:8px;">Na co chcesz się umówić?</div>
      <div style="font-size:0.96rem;color:#aaa;">Wybierz zabieg — Sofia przeprowadzi krótką konsultację i wyśle podsumowanie na email.</div>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="medium")
    items = list(PROCEDURES.items())
    for idx, (name, p) in enumerate(items):
        col = col_a if idx % 2 == 0 else col_b
        with col:
            st.markdown(f"""
            <div class="proc-card">
              <div class="name">{name}</div>
              <div class="tag">{p['tagline']}</div>
              <div class="meta"><span>⏱ {p['time']}</span><span>{p['price']}</span></div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Wybierz →", key=f"pick_{name}", use_container_width=True):
                st.session_state["_picker_loading"] = name
                st.rerun()

# ─── CHAT ─────────────────────────────────────────────────
def render_chat():
    procedure  = st.session_state.get("chosen_procedure", "")
    messages   = st.session_state.get("messages", [])
    conv_state = st.session_state.get("conv_state", {"stage": STAGE_GREETING})
    saved      = st.session_state.get("saved", False)
    p          = PROCEDURES.get(procedure, {})

    col_title, col_back = st.columns([5,1])
    with col_title:
        st.markdown(f"""
        <div style="margin-bottom:1rem;padding-top:1.5rem;">
          <div style="font-family:'Cormorant Garamond',serif;font-size:1.6rem;font-weight:500;color:#1c1c1a;">{procedure}</div>
          <div style="font-size:0.87rem;color:#aaa;margin-top:3px;">{p.get('tagline','')} · Sofia</div>
        </div>
        """, unsafe_allow_html=True)
    with col_back:
        st.write("")
        st.write("")
        if st.button("← Zmień", key="back"):
            for key in ["chat_stage","messages","saved","slot_chosen","conv_state","chosen_procedure"]:
                st.session_state.pop(key, None)
            st.session_state.chat_stage = "pick"
            st.rerun()

    st.markdown('<div style="height:1px;background:#e6e4dc;margin-bottom:1rem;"></div>', unsafe_allow_html=True)

    for msg in messages:
        avatar = "🌿" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    current_stage = conv_state.get("stage", STAGE_GREETING)

    # ── Wybór terminów ──
    if current_stage == STAGE_SLOTS and not saved and not st.session_state.get("slot_chosen"):
        available = [
            s for s in st.session_state.get("available_slots", [])
            if not s["zajety"] and (not s.get("zabieg") or s.get("zabieg") == procedure)
        ]
        st.markdown('<div style="font-size:0.78rem;color:#aaa;letter-spacing:0.1em;text-transform:uppercase;margin:12px 0 8px;">Dostępne terminy</div>', unsafe_allow_html=True)
        if available:
            n = min(len(available), 3)
            slot_cols = st.columns(n, gap="small")
            for i, s in enumerate(available):
                with slot_cols[i % n]:
                    st.markdown('<div class="slot-btn">', unsafe_allow_html=True)
                    if st.button(s["termin"], key=f"slot_{i}", use_container_width=True):
                        s["zajety"] = True
                        st.session_state.slot_chosen = s["termin"]
                        messages.append({"role": "user", "content": f"Wybieram termin: {s['termin']}"})
                        reply = (
                            f"Zapisałam termin **{s['termin']}**. "
                            "Zgłoszenie czeka na potwierdzenie przez specjalistkę — dostaniesz maila kiedy to nastąpi.\n\n"
                            "Proszę podaj adres email, żebym mogła wysłać podsumowanie.\n\n"
                            "Gdy wszystko gotowe — kliknij przycisk **Zapisz i wyślij podsumowanie** poniżej."
                        )
                        messages.append({"role": "assistant", "content": reply})
                        conv_state["stage"] = STAGE_EMAIL
                        st.session_state.messages   = messages
                        st.session_state.conv_state = conv_state
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Brak dostępnych terminów. Możemy zapisać Twoje dane — specjalistka oddzwoni.")
            if st.button("Zapisz moje dane i czekam na kontakt", key="no_slots_save"):
                reply = "Zapiszę Twoje dane i specjalistka oddzwoni. Proszę podaj adres email."
                messages.append({"role": "assistant", "content": reply})
                conv_state["stage"] = STAGE_EMAIL
                st.session_state.messages   = messages
                st.session_state.conv_state = conv_state
                st.rerun()

    slot_chosen    = st.session_state.get("slot_chosen")
    email_in_state = conv_state.get("email", "")

    can_save = (
        not saved
        and current_stage in [STAGE_EMAIL, STAGE_DONE, STAGE_CONTRA]
        and (
            (slot_chosen and email_in_state)
            or current_stage == STAGE_DONE
            or current_stage == STAGE_CONTRA
        )
        and len(messages) >= 4
    )

    if can_save:
        st.markdown('<div style="height:1px;background:#e6e4dc;margin:1.5rem 0 1rem;"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#fdf3d8;border:1px solid rgba(212,168,67,0.4);border-radius:10px;padding:1rem 1.3rem;margin-bottom:1rem;">
          <div style="font-size:1rem;font-weight:600;color:#1c1c1a;margin-bottom:4px;">Konsultacja zakończona</div>
          <div style="font-size:0.88rem;color:#555;line-height:1.6;">
            Kliknij poniższy przycisk, żeby <strong>zapisać rezerwację</strong> i otrzymać potwierdzenie na email.
          </div>
        </div>
        """, unsafe_allow_html=True)
        _, col_btn, _ = st.columns([1,2,1])
        with col_btn:
            st.markdown('<div class="cta-save-wrap">', unsafe_allow_html=True)
            if st.button("Zapisz i wyślij podsumowanie", use_container_width=True, key="save_btn"):
                info = extract_client_info(procedure, conv_state, messages)
                if slot_chosen:
                    info["termin"] = slot_chosen

                tok = secrets.token_urlsafe(16)
                info["token"] = tok

                if slot_chosen:
                    booking = {
                        "token": tok, "imie": info.get("imie","?"),
                        "email": info.get("email",""), "telefon": info.get("telefon",""),
                        "zabieg": procedure, "termin": slot_chosen,
                    }
                    st.session_state.setdefault("pending_bookings", []).append(booking)
                    save_pending(booking)
                    save_slot(slot_chosen, "zarezerwowany")

                sheet_ok = save_consultation(procedure, info, messages)
                email_r  = send_consultation_emails(procedure, info)

                lines = []
                if sheet_ok:              lines.append("✓ Zapisano")
                if email_r.get("client"): lines.append(f"✓ Email wysłany na {info.get('email','')}")
                if email_r.get("owner"):  lines.append("✓ Powiadomienie wysłane do właścicielki")
                if slot_chosen:           lines.append(f"✓ Termin {slot_chosen} oczekuje na potwierdzenie")

                st.success("\n\n".join(lines) if lines else "Zapisano!")
                st.session_state.saved = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Po zapisie ──
    if saved:
        st.markdown("""
        <div style="background:#fdf3d8;border:1px solid rgba(212,168,67,0.4);border-radius:12px;
                    padding:1.8rem;text-align:center;margin:1.5rem 0;">
          <div style="font-family:'Cormorant Garamond',serif;font-size:1.4rem;font-weight:500;color:#1c1c1a;margin-bottom:6px;">Rezerwacja zapisana</div>
          <div style="font-size:0.9rem;color:#666;">Sprawdź skrzynkę email — wysłałyśmy potwierdzenie z detalami.</div>
        </div>
        """, unsafe_allow_html=True)
        _, col_new, _ = st.columns([1,2,1])
        with col_new:
            if st.button("← Wróć na stronę główną", use_container_width=True, key="new_btn"):
                for key in ["messages","saved","slot_chosen","chat_stage","chosen_procedure","conv_state"]:
                    st.session_state.pop(key, None)
                st.session_state.chat_stage = "pick"
                st.rerun()

    # ── Input czatu ──
    if current_stage not in [STAGE_SLOTS, STAGE_DONE] and not saved:
        if prompt := st.chat_input("Napisz do Sofii..."):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            reply, conv_state = conversation_next(procedure, prompt, conv_state)
            display = "Poniżej znajdziesz dostępne terminy — wybierz ten, który Ci odpowiada:" if reply == "__SHOW_SLOTS__" else reply
            messages.append({"role": "assistant", "content": display})
            st.session_state.messages   = messages
            st.session_state.conv_state = conv_state
            st.rerun()

# ─── MAIN ─────────────────────────────────────────────────
def main():
    inject_css()

    if "slots_loaded" not in st.session_state:
        slots, pending = load_slots_from_sheet()
        st.session_state.available_slots  = slots
        st.session_state.pending_bookings = pending
        st.session_state.slots_loaded     = True

    for key, default in [
        ("chat_stage", "pick"), ("chosen_procedure", ""),
        ("messages", []), ("saved", False), ("slot_chosen", None),
        ("conv_state", {"stage": STAGE_GREETING}),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    handle_url_action()
    render_owner_panel()

    if st.session_state.chat_stage == "pick":
        render_picker()
    else:
        render_chat()

if __name__ == "__main__":
    main()
