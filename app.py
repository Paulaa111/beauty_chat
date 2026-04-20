# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny
# Stack: Streamlit + Groq (Llama) + Google Sheets + Gmail
# ============================================================
#
# STREAMLIT SECRETS:
#
# [app]
# groq_api_key    = "gsk_..."
# owner_password  = "TwojeHaslo"
# owner_email     = "wlascicielka@gmail.com"
# app_url         = "https://TWOJA-APKA.streamlit.app"   ← URL apki (do linków w emailu)
#
# [email]
# gmail_user      = "twoj@gmail.com"
# gmail_password  = "abcd efgh ijkl mnop"
#
# [sheets]
# sheet_id        = "ID_ARKUSZA"
#
# [gcp_service_account]
# type = "service_account"
# ... (reszta z JSON)
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BeautyFlow",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# BAZA WIEDZY
# ─────────────────────────────────────────────
PROCEDURES = {
    "Makijaż okolicznościowy": {
        "tagline": "Ślubny, wieczorowy, sesja foto",
        "time": "60–90 min",
        "price": "od 250 zł",
        "series": "jednorazowy",
        "effects": "Profesjonalny, trwały makijaż dopasowany do okazji i karnacji",
        "contraindications": "Aktywne stany zapalne skóry, alergia na kosmetyki do makijażu, łupież powieki",
        "prep": "Przyjść z oczyszczoną, nawilżoną twarzą, bez makijażu",
        "questions": [
            "Jaka to będzie okazja – ślub, event, sesja zdjęciowa, a może coś innego?",
            "Czy ma Pani jakieś alergie na kosmetyki lub konkretne składniki?",
            "Czy nosi Pani soczewki kontaktowe?",
            "Czy ma Pani zdjęcia inspiracji lub preferowany styl makijażu?",
        ],
    },
    "Laminacja Brwi": {
        "tagline": "Naturalne uniesienie i wypełnienie na 6–8 tyg.",
        "time": "60 min",
        "price": "od 160 zł",
        "series": "powtarzać co 6–8 tygodni",
        "effects": "Brwi wyglądają gęściej, są trwale uniesione i ułożone",
        "contraindications": "Alergia na składniki utleniaczy, aktywne stany zapalne w okolicy brwi, ciąża (pierwsza trymestry), chemioterapia",
        "prep": "Nie farbować brwi 2 tygodnie przed, przyjść bez makijażu brwi",
        "questions": [
            "Czy miała Pani wcześniej laminację brwi lub jakikolwiek zabieg chemiczny na brwiach?",
            "Czy miała Pani kiedyś reakcję alergiczną na kosmetyki w okolicy oczu lub brwi?",
            "Jak określiłaby Pani swoje brwi – rzadkie, gęste, z lukami, asymetryczne?",
            "Czy jest Pani w ciąży lub karmi piersią?",
        ],
    },
    "Laminacja Rzęs": {
        "tagline": "Naturalne podkręcenie na 6–8 tygodni",
        "time": "75 min",
        "price": "od 180 zł",
        "series": "powtarzać co 6–8 tygodni",
        "effects": "Rzęsy naturalnie podkręcone, optycznie dłuższe i gęstsze",
        "contraindications": "Alergia na kleje i utleniacze, aktywne infekcje oczu, chemioterapia, rzęsy krótsze niż 4mm",
        "prep": "Bez tuszu do rzęs i odżywek 24h przed, bez soczewek w dniu zabiegu",
        "questions": [
            "Czy miała Pani wcześniej laminację lub lifting rzęs?",
            "Czy miała Pani kiedyś reakcję alergiczną w okolicy oczu po zabiegu kosmetycznym?",
            "Czy stosuje Pani krople do oczu lub leki okulistyczne?",
            "Jak długie są Pani naturalne rzęsy – krótkie, średnie, długie?",
        ],
    },
    "Henna + Regulacja Brwi": {
        "tagline": "Koloryzacja i nadanie kształtu brwiom",
        "time": "45 min",
        "price": "od 80 zł",
        "series": "powtarzać co 3–4 tygodnie",
        "effects": "Zabarwione, wyraźne brwi z precyzyjnym kształtem dopasowanym do twarzy",
        "contraindications": "Alergia na hennę lub PPD, aktywne stany zapalne, łuszczyca w okolicy brwi, ciąża",
        "prep": "Nie farbować brwi 2 tygodnie przed, przyjść z naturalną twarzą",
        "questions": [
            "Czy robiła Pani kiedyś hennę i czy wystąpiła jakaś reakcja alergiczna?",
            "Jaki kolor brwi Pani preferuje – naturalny, ciemniejszy, czy może modny ombre?",
            "Czy ma Pani określony kształt brwi w głowie, czy zostawia Pani decyzję specjalistce?",
            "Czy jest Pani w ciąży?",
        ],
    },
    "Przedłużanie Rzęs (1:1)": {
        "tagline": "Klasyczne przedłużanie metodą włosek po włosku",
        "time": "120 min",
        "price": "od 220 zł",
        "series": "uzupełnienia co 3–4 tygodnie",
        "effects": "Dłuższe, gęstsze rzęsy – naturalny lub dramatyczny efekt zależnie od wyboru",
        "contraindications": "Alergia na klej cyjanoakrylowy, aktywne infekcje oczu, trichotillomania, zbyt krótkie lub słabe rzęsy naturalne",
        "prep": "Bez tuszu, odżywek i olejków na rzęsach, bez soczewek kontaktowych",
        "questions": [
            "Czy nosiła Pani wcześniej przedłużane rzęsy? Jeśli tak, jak długo i jak reagowała skóra?",
            "Czy miała Pani kiedyś alergię lub podrażnienie po kleju do rzęs?",
            "Jaki efekt Panią interesuje – naturalne, cat eye, lisia, a może coś innego?",
            "Czy nosi Pani na co dzień soczewki kontaktowe?",
        ],
    },
}

PROMOTIONS = [
    "Laminacja Brwi + Henna: 220 zł (oszczędzasz 20 zł)",
    "Laminacja Brwi + Laminacja Rzęs: 320 zł",
    "Nowe klientki: -15% na pierwszy zabieg",
]

def build_knowledge_base():
    zabiegi = ""
    for name, p in PROCEDURES.items():
        zabiegi += f"""
ZABIEG: {name}
Czas: {p['time']} | Cena: {p['price']}
Efekty: {p['effects']}
Przeciwwskazania: {p['contraindications']}
Przygotowanie: {p['prep']}
Pytania kwalifikujące: {" | ".join(p['questions'])}
"""
    return f"""
Jesteś Sofią – spokojną, profesjonalną konsultantką studia kosmetycznego BeautyFlow w Warszawie.
Rozmawiasz wyłącznie po polsku. Jesteś pomocna, konkretna, nigdy nie używasz żargonu medycznego.
Nie wymyślaj informacji spoza bazy poniżej. Pytania wykraczające poza bazę odsyłaj na +48 500 123 456.

ETAPY ROZMOWY – przestrzegaj kolejności:
1. Przywitaj się, zapytaj o imię.
2. ZAWSZE jako drugie pytanie zapytaj: "Czy była już Pani u nas w salonie?" – to ważne dla specjalistki.
3. Prowadź wywiad – pytania kwalifikujące STOPNIOWO, 1–2 naraz, naturalnie.
4. Po zebraniu odpowiedzi krótko podsumuj czy zabieg jest wskazany.
5. Zapytaj wprost: "Czy chciałaby Pani od razu wybrać termin?"
6. Jeśli TAK – napisz dokładnie i tylko to słowo: SHOW_SLOTS
7. Jeśli pojawi się przeciwwskazanie – zaznacz delikatnie, zaproponuj konsultację.
8. Przed końcem poproś o imię (jeśli nie podała) i email na podsumowanie.

{zabiegi}

PROMOCJE:
{chr(10).join(f"- {p}" for p in PROMOTIONS)}

KONTAKT:
ul. Złota 12, Warszawa | +48 500 123 456 | hello@beautyflow.pl | Pon–Pt 9–20, Sob 9–16
"""

KNOWLEDGE_BASE = build_knowledge_base()

# ─────────────────────────────────────────────
# CSS – JASNY MINIMALISTYCZNY DESIGN
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Cormorant:ital,wght@0,400;0,500;1,400&display=swap');

    :root {
        --bg:       #fafaf8;
        --surface:  #ffffff;
        --surface2: #f5f4f0;
        --border:   #e8e6e0;
        --border2:  #d4d1c8;
        --accent:   #2d2d2d;
        --accent2:  #1a1a1a;
        --gold:     #b8963e;
        --gold-lt:  #f0e8d0;
        --text:     #1a1a1a;
        --text2:    #6b6860;
        --text3:    #a8a49a;
        --green:    #3d7a5a;
        --red:      #c0392b;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--text) !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* ── Headings ── */
    h1, h2, h3 {
        font-family: 'Cormorant', serif !important;
        color: var(--text) !important;
        font-weight: 500 !important;
    }

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        margin-bottom: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        animation: slideIn 0.25s ease forwards;
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] li {
        color: var(--text) !important;
        font-size: 0.95rem !important;
        line-height: 1.7 !important;
    }
    [data-testid="stChatMessage"] strong {
        color: var(--accent2) !important;
        font-weight: 600 !important;
    }

    /* ── Chat input ── */
    [data-testid="stChatInputTextArea"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border2) !important;
        border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 0.95rem !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stChatInputTextArea"]:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 3px rgba(184,150,62,0.1) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--accent) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.03em !important;
        padding: 0.5rem 1.1rem !important;
        transition: background 0.15s, transform 0.1s !important;
    }
    .stButton > button:hover {
        background: var(--accent2) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ── Text inputs ── */
    .stTextInput > div > div > input {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 0.9rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 3px rgba(184,150,62,0.08) !important;
    }

    /* ── Procedure cards ── */
    .proc-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        margin-bottom: 10px;
        transition: box-shadow 0.2s, border-color 0.2s;
        cursor: default;
    }
    .proc-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.07);
        border-color: var(--border2);
    }
    .proc-card .name  {
        font-family: 'Cormorant', serif;
        font-size: 1.05rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 3px;
    }
    .proc-card .tag   { font-size: 0.78rem; color: var(--text3); }
    .proc-card .meta  {
        font-size: 0.78rem;
        color: var(--text2);
        margin-top: 8px;
        display: flex;
        gap: 12px;
    }
    .proc-card .meta span {
        background: var(--surface2);
        border-radius: 4px;
        padding: 2px 8px;
    }

    /* ── Slot buttons ── */
    .slot-btn { margin-bottom: 6px; }

    /* ── Status dots ── */
    .dot-green { color: #3d7a5a; font-size: 0.6rem; }
    .dot-red   { color: #c0392b; font-size: 0.6rem; }

    /* ── Alerts ── */
    .stAlert {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    .stAlert p { color: var(--text) !important; }

    /* ── Section labels ── */
    .section-label {
        font-size: 0.68rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--text3);
        margin-bottom: 10px;
        margin-top: 4px;
    }

    /* ── Loading bar animation ── */
    @keyframes shimmer {
        0%   { background-position: -200% 0; }
        100% { background-position:  200% 0; }
    }
    .loading-bar {
        height: 2px;
        background: linear-gradient(90deg, var(--border) 25%, var(--gold) 50%, var(--border) 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 2px;
        margin: 8px 0 16px;
    }

    /* ── Dividers ── */
    hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

    #MainMenu, header, footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
def render_logo():
    st.markdown("""
    <div style="padding: 2rem 0 1.2rem;">
        <div style="font-family:'Cormorant',serif;font-size:2rem;font-weight:500;
                    color:#1a1a1a;letter-spacing:0.04em;line-height:1.0;">
            BeautyFlow
        </div>
        <div style="font-size:0.68rem;letter-spacing:0.22em;color:#a8a49a;
                    text-transform:uppercase;margin-top:6px;">
            Konsultant AI — Studio Urody
        </div>
        <div class="loading-bar" style="margin-top:14px;"></div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GROQ API
# ─────────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    try:
        return OpenAI(
            api_key=st.secrets["app"]["groq_api_key"],
            base_url="https://api.groq.com/openai/v1",
        )
    except Exception as e:
        st.error(f"Brak klucza Groq API: {e}")
        return None


def ask_groq(messages: list, system: str = None) -> str:
    client = get_groq_client()
    if not client:
        return "Przepraszam, problem techniczny. Proszę zadzwonić: +48 500 123 456."
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system or KNOWLEDGE_BASE}] + messages,
            max_tokens=500,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Przepraszam, błąd: {e}"


def extract_client_info(messages: list) -> dict:
    client = get_groq_client()
    if not client:
        return {}
    try:
        history = "\n".join([f"{m['role'].upper()}: {m['content'][:150]}" for m in messages[-12:]])
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": (
                f"Z tej rozmowy wyciągnij dane. Odpowiedz TYLKO w tym formacie:\n"
                f"IMIE: xxx\nEMAIL: xxx lub brak\nTELEFON: xxx lub brak\n"
                f"PODSUMOWANIE: 2 zdania co klientka chce i jakie odpowiedzi udzieliła\n\n{history}"
            )}],
            max_tokens=120,
            temperature=0,
        )
        text = resp.choices[0].message.content
        result = {}
        for line in text.strip().split("\n"):
            if "IMIE:" in line:
                result["imie"] = line.split("IMIE:")[1].strip()
            elif "EMAIL:" in line:
                val = line.split("EMAIL:")[1].strip()
                result["email"] = val if "@" in val else ""
            elif "TELEFON:" in line:
                result["telefon"] = line.split("TELEFON:")[1].strip()
            elif "PODSUMOWANIE:" in line:
                result["podsumowanie"] = line.split("PODSUMOWANIE:")[1].strip()
        return result
    except Exception:
        return {}

# ─────────────────────────────────────────────
# EMAIL – GMAIL SMTP
# ─────────────────────────────────────────────
EMAIL_STYLE = """
<style>
  body { font-family: 'Georgia', serif; background:#fafaf8; margin:0; padding:0; }
  .wrap { max-width:540px; margin:32px auto; background:#fff;
          border-radius:12px; overflow:hidden; border:1px solid #e8e6e0; }
  .hdr  { background:#1a1a1a; padding:28px 36px; }
  .hdr h1 { color:#f0e8d0; font-size:1.4rem; margin:0; letter-spacing:0.06em; font-weight:400; }
  .hdr p  { color:#777; font-size:0.7rem; letter-spacing:0.2em; text-transform:uppercase;
             margin:6px 0 0; }
  .body { padding:28px 36px; color:#1a1a1a; line-height:1.75; font-size:0.92rem; }
  .box  { background:#fafaf8; border-left:3px solid #b8963e; border-radius:6px;
          padding:12px 16px; margin:14px 0; font-size:0.88rem; }
  .btn  { display:inline-block; padding:10px 24px; border-radius:6px;
          font-family:sans-serif; font-size:0.82rem; font-weight:600;
          letter-spacing:0.04em; text-decoration:none; margin:6px 4px 0 0; }
  .btn-ok  { background:#3d7a5a; color:#fff; }
  .btn-no  { background:#c0392b; color:#fff; }
  .ftr  { background:#fafaf8; padding:16px 36px; text-align:center;
          color:#a8a49a; font-size:0.75rem; border-top:1px solid #e8e6e0; }
</style>
"""

def _send_email(to: str, subject: str, html: str) -> bool:
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
        return False


def send_consultation_emails(procedure: str, info: dict, messages: list) -> dict:
    """Email do klientki (podsumowanie) + do właścicielki (nowa konsultacja z linkami akcji)."""
    results = {}
    owner_email  = st.secrets.get("app", {}).get("owner_email", "")
    app_url      = st.secrets.get("app", {}).get("app_url", "")
    gmail_user   = st.secrets.get("email", {}).get("gmail_user", "")
    if not gmail_user:
        return {"error": "brak konfiguracji email"}

    proc    = PROCEDURES.get(procedure, {})
    imie    = info.get("imie", "Klientko")
    email   = info.get("email", "")
    termin  = info.get("termin", "")
    podsum  = info.get("podsumowanie", "—")
    token   = info.get("token", "")
    teraz   = datetime.now().strftime("%d.%m.%Y, %H:%M")

    # ── Email do klientki ──────────────────────
    if email:
        html_client = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
        <div class="wrap">
          <div class="hdr"><h1>BeautyFlow</h1><p>Podsumowanie konsultacji</p></div>
          <div class="body">
            <p>Dziękujemy, <strong>{imie}</strong>!</p>
            <p>Oto podsumowanie Twojej konsultacji z {teraz}.</p>
            <div class="box">
              <strong>{procedure}</strong><br>
              Czas: {proc.get('time','—')} &nbsp;·&nbsp; Cena: {proc.get('price','—')}
              {"<br>Wybrany termin: <strong>" + termin + "</strong>" if termin else ""}
            </div>
            <div class="box">{podsum}</div>
            <div class="box">
              <strong>Jak się przygotować:</strong><br>{proc.get('prep','—')}
            </div>
            <p>Nasza specjalistka potwierdzi termin wkrótce.</p>
            <p style="color:#a8a49a;font-size:0.82rem;">— Zespół BeautyFlow</p>
          </div>
          <div class="ftr">ul. Złota 12, Warszawa · +48 500 123 456 · hello@beautyflow.pl</div>
        </div></body></html>"""
        results["client"] = _send_email(email, f"BeautyFlow – podsumowanie: {procedure}", html_client)

    # ── Email do właścicielki z przyciskami akcji ──
    if owner_email and token and app_url:
        confirm_url = f"{app_url}?action=confirm&token={token}"
        reject_url  = f"{app_url}?action=reject&token={token}"
        html_owner = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
        <div class="wrap">
          <div class="hdr"><h1>BeautyFlow</h1><p>Nowa rezerwacja do potwierdzenia</p></div>
          <div class="body">
            <p><strong>Nowa konsultacja</strong> — {teraz}</p>
            <div class="box">
              Imię: <strong>{imie}</strong><br>
              Email: {email or '—'} &nbsp;·&nbsp; Tel: {info.get('telefon','—')}<br>
              Zabieg: <strong>{procedure}</strong><br>
              {"Termin: <strong>" + termin + "</strong>" if termin else "Termin: nie wybrany"}
            </div>
            <div class="box">{podsum}</div>
            <p>Kliknij aby podjąć akcję:</p>
            <a href="{confirm_url}" class="btn btn-ok">Potwierdź rezerwację</a>
            <a href="{reject_url}"  class="btn btn-no">Odrzuć</a>
            <p style="color:#a8a49a;font-size:0.78rem;margin-top:16px;">
              Linki są jednorazowe. Po kliknięciu otworzy się aplikacja i automatycznie wykona akcję.
            </p>
          </div>
          <div class="ftr">BeautyFlow AI · System automatyczny</div>
        </div></body></html>"""
        results["owner"] = _send_email(owner_email, f"Nowa rezerwacja: {imie} — {procedure}", html_owner)

    return results


def send_status_email(booking: dict, confirmed: bool) -> bool:
    """Email do klientki po zatwierdzeniu lub odrzuceniu przez właścicielkę."""
    email = booking.get("email", "")
    if not email or "@" not in email:
        return False
    imie   = booking.get("imie", "Klientko")
    zabieg = booking.get("zabieg", "—")
    termin = booking.get("termin", "—")
    proc   = PROCEDURES.get(zabieg, {})
    if confirmed:
        subj = "BeautyFlow – Twój termin potwierdzony"
        body = f"""<p>Twoja rezerwacja jest <strong>potwierdzona</strong>, {imie}!</p>
        <div class="box">
          Zabieg: <strong>{zabieg}</strong><br>
          Termin: <strong>{termin}</strong><br>
          Adres: ul. Złota 12, Warszawa
        </div>
        <div class="box"><strong>Przygotowanie:</strong><br>{proc.get('prep','—')}</div>
        <p>Do zobaczenia! W razie pytań: +48 500 123 456</p>"""
    else:
        subj = "BeautyFlow – informacja o rezerwacji"
        body = f"""<p>Niestety wybrany termin (<strong>{termin}</strong>) nie jest już dostępny.</p>
        <div class="box">Zabieg: <strong>{zabieg}</strong></div>
        <p>Zapraszamy do ponownego umówienia się:<br>
        +48 500 123 456 · hello@beautyflow.pl</p>
        <p>Przepraszamy za utrudnienia!</p>"""

    html = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
    <div class="wrap">
      <div class="hdr"><h1>BeautyFlow</h1>
      <p>{"Potwierdzenie" if confirmed else "Informacja o rezerwacji"}</p></div>
      <div class="body">{body}<p style="color:#a8a49a;font-size:0.82rem;">— Zespół BeautyFlow</p></div>
      <div class="ftr">ul. Złota 12, Warszawa · +48 500 123 456</div>
    </div></body></html>"""
    return _send_email(email, subj, html)

# ─────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"],
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def get_spreadsheet():
    gc = get_sheets_client()
    if not gc:
        return None
    try:
        return gc.open_by_key(st.secrets["sheets"]["sheet_id"])
    except Exception:
        return None


def _get_ws(sp, name: str, headers: list):
    try:
        return sp.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sp.add_worksheet(name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        ws.format(f"A1:{chr(64+len(headers))}1", {"textFormat": {"bold": True}})
        return ws


def save_consultation(procedure: str, info: dict, messages: list) -> bool:
    try:
        sp = get_spreadsheet()
        if not sp:
            return False
        ws = _get_ws(sp, "Konsultacje",
                     ["Data", "Imię", "Email", "Telefon", "Zabieg", "Termin", "Wiadomości", "Podsumowanie", "Status"])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            info.get("imie", "—"), info.get("email", "—"), info.get("telefon", "—"),
            procedure, info.get("termin", "—"), len(messages),
            info.get("podsumowanie", "—"),
            "oczekuje" if info.get("termin") else "bez terminu",
        ])
        return True
    except Exception:
        return False


def load_slots_from_sheet():
    try:
        sp = get_spreadsheet()
        if not sp:
            return [], []
        ws_t = _get_ws(sp, "Terminy",    ["Termin", "Status"])
        ws_r = _get_ws(sp, "Rezerwacje", ["Data", "Token", "Termin", "Imię", "Email", "Telefon", "Zabieg", "Status"])
        slots   = [{"termin": r["Termin"], "zabieg": r.get("Zabieg",""), "zajety": r.get("Status","wolny") != "wolny"}
                   for r in ws_t.get_all_records() if r.get("Termin")]
        pending = [{"token": r.get("Token",""), "imie": r.get("Imię","?"), "email": r.get("Email",""),
                    "telefon": r.get("Telefon",""), "zabieg": r.get("Zabieg",""), "termin": r.get("Termin","")}
                   for r in ws_r.get_all_records() if r.get("Status") == "oczekuje"]
        return slots, pending
    except Exception:
        return [], []


def save_slot(termin: str, status: str = "wolny", zabieg: str = ""):
    try:
        sp = get_spreadsheet()
        if not sp:
            return
        ws = _get_ws(sp, "Terminy", ["Termin", "Zabieg", "Status"])
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Termin") == termin:
                ws.update(f"C{i}", [[status]])
                return
        ws.append_row([termin, zabieg, status])
    except Exception:
        pass


def save_pending(booking: dict):
    try:
        sp = get_spreadsheet()
        if not sp:
            return
        ws = _get_ws(sp, "Rezerwacje",
                     ["Data", "Token", "Termin", "Imię", "Email", "Telefon", "Zabieg", "Status"])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            booking.get("token", ""),
            booking.get("termin", ""),
            booking.get("imie", ""),
            booking.get("email", ""),
            booking.get("telefon", ""),
            booking.get("zabieg", ""),
            "oczekuje",
        ])
    except Exception:
        pass


def update_booking_in_sheet(token: str, new_status: str):
    try:
        sp = get_spreadsheet()
        if not sp:
            return
        ws = sp.worksheet("Rezerwacje")
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Token") == token:
                ws.update(f"H{i}", [[new_status]])
                return
    except Exception:
        pass

# ─────────────────────────────────────────────
# OBSŁUGA LINKÓW AKCJI W URL (confirm/reject)
# ─────────────────────────────────────────────
def handle_url_action():
    """
    Właścicielka klika link w emailu → apka otwiera się z ?action=confirm&token=xxx
    Tu obsługujemy tę akcję automatycznie.
    """
    params = st.query_params
    action = params.get("action", "")
    token  = params.get("token", "")
    if not action or not token:
        return

    # Znajdź rezerwację po tokenie
    pending = st.session_state.get("pending_bookings", [])
    booking = next((b for b in pending if b.get("token") == token), None)

    if action == "confirm" and booking:
        # Wykonaj potwierdzenie
        save_slot(booking.get("termin", ""), "zajęty")
        update_booking_in_sheet(token, "potwierdzona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"):
                s["zajety"] = True
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=True)
        st.success(f"Rezerwacja potwierdzona — {booking.get('imie')} · {booking.get('termin')}")
        # Wyczyść params
        st.query_params.clear()

    elif action == "reject" and booking:
        save_slot(booking.get("termin", ""), "wolny")
        update_booking_in_sheet(token, "odrzucona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"):
                s["zajety"] = False
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=False)
        st.info(f"Rezerwacja odrzucona — klientka poinformowana emailem.")
        st.query_params.clear()

    elif booking is None and token:
        st.warning("Link wygasł lub rezerwacja już została przetworzona.")
        st.query_params.clear()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.5rem 0 1rem;">
          <div style="font-family:'Cormorant',serif;font-size:1.2rem;font-weight:500;color:#1a1a1a;">
            BeautyFlow
          </div>
          <div style="font-size:0.62rem;letter-spacing:0.18em;color:#a8a49a;
                      text-transform:uppercase;margin-top:4px;">Studio Urody</div>
        </div>
        <div style="height:1px;background:#e8e6e0;margin-bottom:1rem;"></div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:0.82rem;color:#6b6860;line-height:2.0;">'
            'ul. Złota 12, Warszawa<br>+48 500 123 456<br>'
            'hello@beautyflow.pl<br>Pon–Pt 9–20 · Sob 9–16</div>',
            unsafe_allow_html=True
        )
        st.markdown('<div style="height:1px;background:#e8e6e0;margin:1rem 0;"></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">Aktualne promocje</div>', unsafe_allow_html=True)
        for p in PROMOTIONS:
            st.markdown(
                f'<div style="font-size:0.8rem;color:#6b6860;padding:5px 0;'
                f'border-bottom:1px solid #f0ede6;">{p}</div>',
                unsafe_allow_html=True
            )

        st.markdown('<div style="height:1px;background:#e8e6e0;margin:1rem 0;"></div>', unsafe_allow_html=True)
        render_owner_panel()

        st.markdown('<div style="height:1px;background:#e8e6e0;margin:1rem 0;"></div>', unsafe_allow_html=True)
        groq_ok   = "app" in st.secrets and "groq_api_key" in st.secrets.get("app", {})
        sheets_ok = "gcp_service_account" in st.secrets
        email_ok  = "email" in st.secrets
        def dot(ok): return f'<span style="color:{"#3d7a5a" if ok else "#c0392b"};font-size:0.55rem;">&#9679;</span>'
        st.markdown(
            f'<div style="font-size:0.75rem;color:#a8a49a;line-height:2.2;">'
            f'{dot(groq_ok)} Groq API<br>{dot(sheets_ok)} Google Sheets<br>{dot(email_ok)} Gmail</div>',
            unsafe_allow_html=True
        )


def render_owner_panel():
    st.markdown('<div class="section-label">Panel właścicielki</div>', unsafe_allow_html=True)
    if "owner_auth" not in st.session_state:
        st.session_state.owner_auth = False

    if not st.session_state.owner_auth:
        pw = st.text_input("", type="password", key="opw",
                           placeholder="Hasło dostępu...", label_visibility="collapsed")
        if st.button("Zaloguj", key="ologin", use_container_width=True):
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

    st.markdown('<div style="font-size:0.75rem;color:#3d7a5a;margin-bottom:10px;">Zalogowano</div>',
                unsafe_allow_html=True)

    # ── Dodaj termin do harmonogramu ──────────
    st.markdown('<div style="font-size:0.75rem;color:#6b6860;margin-bottom:6px;">Dodaj termin</div>',
                unsafe_allow_html=True)

    # Wybór zabiegu
    proc_names = list(PROCEDURES.keys())
    sel_proc = st.selectbox("Zabieg", proc_names, key="slot_proc",
                            label_visibility="collapsed")

    # Data i godzina w dwóch kolumnach
    dc1, dc2 = st.columns([3, 2])
    with dc1:
        slot_date = st.text_input("", key="slot_date",
                                  placeholder="dd.mm.rrrr",
                                  label_visibility="collapsed")
    with dc2:
        slot_hour = st.text_input("", key="slot_hour",
                                  placeholder="godz. HH:MM",
                                  label_visibility="collapsed")

    ca, cb = st.columns(2)
    with ca:
        if st.button("Dodaj", key="addslot", use_container_width=True):
            if slot_date.strip() and slot_hour.strip():
                termin_str = f"{slot_date.strip()}, {slot_hour.strip()}"
                new_slot = {"termin": termin_str, "zabieg": sel_proc, "zajety": False}
                st.session_state.available_slots.append(new_slot)
                save_slot(termin_str, "wolny", sel_proc)
                st.rerun()
            else:
                st.warning("Wpisz datę i godzinę")
    with cb:
        if st.button("Wyczyść wolne", key="clrslot", use_container_width=True):
            st.session_state.available_slots = [
                s for s in st.session_state.available_slots if s["zajety"]
            ]
            try:
                sp = get_spreadsheet()
                if sp:
                    ws = sp.worksheet("Terminy")
                    rows = ws.get_all_records()
                    # Usuń od końca żeby nie przesuwać indeksów
                    to_delete = [i+2 for i, r in enumerate(rows) if r.get("Status") == "wolny"]
                    for i in reversed(to_delete):
                        ws.delete_rows(i)
            except Exception:
                pass
            st.rerun()

    # Lista harmonogramu – pogrupowana po zabiegu
    slots_all = st.session_state.get("available_slots", [])
    if slots_all:
        st.markdown('<div style="height:1px;background:#e8e6e0;margin:8px 0 6px;"></div>',
                    unsafe_allow_html=True)
        # Grupuj po zabiegu
        by_proc = {}
        for s in slots_all:
            key = s.get("zabieg", "Inne")
            by_proc.setdefault(key, []).append(s)

        for proc_name, proc_slots in by_proc.items():
            st.markdown(
                f'<div style="font-size:0.68rem;letter-spacing:0.12em;color:#a8a49a;'
                f'text-transform:uppercase;margin:8px 0 4px;">{proc_name}</div>',
                unsafe_allow_html=True
            )
            for s in proc_slots:
                dot_c  = "#c0392b" if s["zajety"] else "#3d7a5a"
                status = " — zajęty" if s["zajety"] else ""
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#6b6860;padding:2px 0;">'
                    f'<span style="color:{dot_c};font-size:0.55rem;">&#9679;</span> '
                    f'{s["termin"]}<span style="color:#bbb">{status}</span></div>',
                    unsafe_allow_html=True
                )

    # ── Rezerwacje do potwierdzenia ──
    pending = st.session_state.get("pending_bookings", [])
    if pending:
        st.markdown('<div style="height:1px;background:#e8e6e0;margin:10px 0 6px;"></div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="section-label">Do potwierdzenia ({len(pending)})</div>',
                    unsafe_allow_html=True)
        for i, b in enumerate(pending):
            st.markdown(
                f'<div style="font-size:0.8rem;color:#1a1a1a;line-height:1.8;'
                f'background:#fafaf8;border:1px solid #e8e6e0;border-radius:8px;'
                f'padding:8px 10px;margin-bottom:6px;">'
                f'<strong>{b.get("imie","?")}</strong><br>'
                f'<span style="color:#6b6860">{b.get("zabieg","?")}</span><br>'
                f'<span style="color:#a8a49a">{b.get("termin","?")}</span><br>'
                f'<span style="color:#a8a49a;font-size:0.75rem;">{b.get("email","-")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Potwierdź", key=f"ok_{i}", use_container_width=True):
                    save_slot(b.get("termin",""), "zajęty")
                    update_booking_in_sheet(b.get("token",""), "potwierdzona")
                    for s in st.session_state.available_slots:
                        if s["termin"] == b.get("termin"):
                            s["zajety"] = True
                    send_status_email(b, confirmed=True)
                    st.session_state.pending_bookings.pop(i)
                    st.rerun()
            with c2:
                if st.button("Odrzuć", key=f"no_{i}", use_container_width=True):
                    save_slot(b.get("termin",""), "wolny")
                    update_booking_in_sheet(b.get("token",""), "odrzucona")
                    for s in st.session_state.available_slots:
                        if s["termin"] == b.get("termin"):
                            s["zajety"] = False
                    send_status_email(b, confirmed=False)
                    st.session_state.pending_bookings.pop(i)
                    st.rerun()

    ca2, cb2 = st.columns(2)
    with ca2:
        if st.button("Odśwież", key="refresh", use_container_width=True):
            slots, pending = load_slots_from_sheet()
            st.session_state.available_slots  = slots
            st.session_state.pending_bookings = pending
            st.rerun()
    with cb2:
        if st.button("Wyloguj", key="ologout", use_container_width=True):
            st.session_state.owner_auth = False
            st.rerun()
# ─────────────────────────────────────────────
# EKRAN WYBORU ZABIEGU
# ─────────────────────────────────────────────
def render_picker():
    # Sprawdź czy ktoś właśnie kliknął – jeśli tak, pokaż loading i nie renderuj kart
    if st.session_state.get("_picker_loading"):
        name = st.session_state["_picker_loading"]
        st.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)
        intro = ask_groq(
            messages=[{"role": "user", "content": f"Interesuję się zabiegiem: {name}"}],
            system=KNOWLEDGE_BASE + f"\nKlientka wybrała: {name}. Przywitaj się, 1-2 zdania o zabiegu, zacznij pierwsze pytanie kwalifikujące."
        )
        st.session_state.chosen_procedure    = name
        st.session_state.messages            = [{"role": "assistant", "content": intro}]
        st.session_state.saved               = False
        st.session_state.slot_chosen         = None
        st.session_state.chat_stage          = "chat"
        del st.session_state["_picker_loading"]
        st.rerun()
        return

    st.markdown("""
    <div style="margin-bottom:2rem;">
      <div style="font-family:'Cormorant',serif;font-size:1.6rem;font-weight:500;
                  color:#1a1a1a;line-height:1.2;margin-bottom:8px;">
        Na co chcesz się umówić?
      </div>
      <div style="font-size:0.88rem;color:#a8a49a;">
        Wybierz zabieg — Sofia przeprowadzi krótką konsultację i wyśle podsumowanie na email.
      </div>
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
              <div class="meta">
                <span>{p['time']}</span>
                <span>{p['price']}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Wybierz →", key=f"pick_{name}", use_container_width=True):
                # Zapisz wybór i przeładuj – loading pokaże się w następnym cyklu
                st.session_state["_picker_loading"] = name
                st.rerun()

# ─────────────────────────────────────────────
# CZAT
# ─────────────────────────────────────────────
def render_chat():
    procedure = st.session_state.get("chosen_procedure", "")
    messages  = st.session_state.get("messages", [])
    saved     = st.session_state.get("saved", False)
    p         = PROCEDURES.get(procedure, {})

    # Nagłówek z przyciskiem powrotu w tej samej linii
    col_title, col_back = st.columns([5, 1])
    with col_title:
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
          <div style="font-family:'Cormorant',serif;font-size:1.3rem;font-weight:500;color:#1a1a1a;">
            {procedure}
          </div>
          <div style="font-size:0.78rem;color:#a8a49a;margin-top:3px;">{p.get('tagline','')} · Sofia</div>
        </div>
        """, unsafe_allow_html=True)
    with col_back:
        if st.button("← Zmień", key="back"):
            st.session_state.chat_stage = "pick"
            st.session_state.messages   = []
            st.session_state.saved      = False
            st.session_state.slot_chosen = None
            st.rerun()

    st.markdown('<div style="height:1px;background:#e8e6e0;margin-bottom:1rem;"></div>',
                unsafe_allow_html=True)

    # ── Historia czatu ─────────────────────────
    for msg in messages:
        avatar  = "🌿" if msg["role"] == "assistant" else "👤"
        content = msg["content"]
        if content.strip() == "SHOW_SLOTS":
            content = "Poniżej dostępne terminy — proszę wybrać:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(content)

    # ── Przyciski terminów ─────────────────────
    show_slots = (
        not saved
        and not st.session_state.get("slot_chosen")
        and any(m["content"].strip() == "SHOW_SLOTS"
                for m in messages if m["role"] == "assistant")
    )
    # Filtruj terminy – tylko pasujące do wybranego zabiegu (lub bez przypisanego)
    available = [
        s for s in st.session_state.get("available_slots", [])
        if not s["zajety"] and (not s.get("zabieg") or s.get("zabieg") == procedure)
    ]

    if show_slots:
        if available:
            st.markdown(
                '<div style="font-size:0.78rem;color:#a8a49a;letter-spacing:0.1em;'
                'text-transform:uppercase;margin:12px 0 8px;">Dostępne terminy</div>',
                unsafe_allow_html=True
            )
            # Dynamiczne kolumny – max 3 w rzędzie
            n = min(len(available), 3)
            slot_cols = st.columns(n, gap="small")
            for i, s in enumerate(available):
                with slot_cols[i % n]:
                    if st.button(s["termin"], key=f"slot_{i}", use_container_width=True):
                        loading = st.empty()
                        loading.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)
                        s["zajety"] = True
                        st.session_state.slot_chosen = s["termin"]
                        messages.append({"role": "user", "content": f"Wybieram termin: {s['termin']}"})
                        reply = ask_groq(
                            messages=messages,
                            system=KNOWLEDGE_BASE + (
                                f"\nKlientka wybrała termin {s['termin']}. "
                                "Potwierdź ciepło. Poproś o imię i email (wyślemy podsumowanie). "
                                "Poinformuj że właścicielka potwierdzi termin."
                            )
                        )
                        loading.empty()
                        messages.append({"role": "assistant", "content": reply})
                        st.session_state.messages = messages
                        st.rerun()
        else:
            st.info("Brak dostępnych terminów. Możemy zapisać Twoje dane — specjalistka oddzwoni.")

    # ── Przycisk zapisz ────────────────────────
    can_save = (
        not saved
        and len(messages) >= 5
        and (st.session_state.get("slot_chosen") or len(messages) >= 8)
    )
    if can_save:
        st.markdown("")
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            if st.button("Zapisz i wyślij podsumowanie", use_container_width=True, key="save_btn"):
                loading = st.empty()
                loading.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

                info = extract_client_info(messages)
                if st.session_state.get("slot_chosen"):
                    info["termin"] = st.session_state.slot_chosen

                # Token do linków akcji w emailu
                tok = secrets.token_urlsafe(16)
                info["token"] = tok

                # Rezerwacja pending
                if st.session_state.get("slot_chosen"):
                    booking = {
                        "token":   tok,
                        "imie":    info.get("imie", "?"),
                        "email":   info.get("email", ""),
                        "telefon": info.get("telefon", ""),
                        "zabieg":  procedure,
                        "termin":  st.session_state.slot_chosen,
                    }
                    if "pending_bookings" not in st.session_state:
                        st.session_state.pending_bookings = []
                    st.session_state.pending_bookings.append(booking)
                    save_pending(booking)
                    save_slot(st.session_state.slot_chosen, "zarezerwowany")

                sheet_ok = save_consultation(procedure, info, messages)
                email_r  = send_consultation_emails(procedure, info, messages)
                loading.empty()

                # Feedback przez st.empty() – animowany
                fb = st.empty()
                lines = []
                if sheet_ok:
                    lines.append("Zapisano w arkuszu")
                if email_r.get("client"):
                    lines.append(f"Email wysłany do klientki ({info.get('email','')})")
                if email_r.get("owner"):
                    lines.append("Powiadomienie wysłane do właścicielki (z przyciskami akcji)")
                if st.session_state.get("slot_chosen"):
                    lines.append(f"Rezerwacja {st.session_state.slot_chosen} oczekuje na potwierdzenie")

                fb.success("  \n".join(lines) if lines else "Zapisano!")
                st.session_state.saved = True
                st.rerun()

    # ── Zakończono ─────────────────────────────
    if saved:
        st.success("Konsultacja zakończona i zapisana.")
        _, col_new, _ = st.columns([1, 2, 1])
        with col_new:
            if st.button("Nowa konsultacja", use_container_width=True, key="new_btn"):
                st.session_state.messages        = []
                st.session_state.saved           = False
                st.session_state.slot_chosen     = None
                st.session_state.chat_stage      = "pick"
                st.session_state.chosen_procedure = ""
                st.rerun()
        return

    # ── Input ──────────────────────────────────
    if not saved and not show_slots:
        if prompt := st.chat_input("Napisz do Sofii..."):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            loading = st.empty()
            loading.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

            with st.chat_message("assistant", avatar="🌿"):
                reply = ask_groq(
                    messages=messages,
                    system=KNOWLEDGE_BASE + f"\nAktualnie omawiany zabieg: {procedure}"
                )
                display = "Poniżej dostępne terminy — proszę wybrać:" \
                          if reply.strip() == "SHOW_SLOTS" else reply
                st.markdown(display)

            loading.empty()
            messages.append({"role": "assistant", "content": reply})
            st.session_state.messages = messages
            st.rerun()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()

    # Inicjalizacja stanu
    if "slots_loaded" not in st.session_state:
        slots, pending = load_slots_from_sheet()
        st.session_state.available_slots  = slots
        st.session_state.pending_bookings = pending
        st.session_state.slots_loaded     = True

    for key, default in [
        ("chat_stage", "pick"), ("chosen_procedure", ""),
        ("messages", []), ("saved", False), ("slot_chosen", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    render_sidebar()

    # Obsłuż linki akcji z emaila (?action=confirm&token=xxx)
    handle_url_action()

    # Layout: środkowa kolumna z paddingiem
    _, main_col, _ = st.columns([1, 5, 1])
    with main_col:
        render_logo()
        if st.session_state.chat_stage == "pick":
            render_picker()
        else:
            render_chat()


if __name__ == "__main__":
    main()
