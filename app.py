# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny
# Stack: Streamlit + Groq (Llama) + Google Sheets + Gmail
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time
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
    initial_sidebar_state="collapsed",
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
Jesteś Sofią – profesjonalną konsultantką studia kosmetycznego BeautyFlow w Warszawie.
Rozmawiasz wyłącznie po polsku.

STYL KOMUNIKACJI:
- Odpowiedzi KRÓTKIE i konkretne – maksymalnie 2-3 zdania na raz
- Jedno pytanie na raz, nigdy kilka naraz
- Żaden żargon medyczny
- Nie wymyślaj informacji spoza bazy
- Pytania spoza zakresu: odsyłaj na +48 500 123 456
- IMIĘ klientki używaj TYLKO raz – przy pierwszym przywitaniu po tym jak je poda. Potem już NIGDY nie wstawiaj imienia do wiadomości, żadnych "Aniu," ani "Dziękuję, Kasiu" – to brzmi sztucznie. Wyjątek: ostatnie pożegnanie na końcu rozmowy.

ETAPY ROZMOWY (przestrzegaj kolejności, po jednym pytaniu na raz):
1. Przywitaj się, zapytaj o imię. (1 zdanie)
2. Po otrzymaniu imienia – użyj go JEDEN raz w odpowiedzi, potem zapomnij o nim.
3. Zapytaj: "Czy była już Pani u nas w salonie?"
4. Zadawaj pytania kwalifikujące po 1 sztuce, naturalnie.
5. Po zebraniu odpowiedzi: krótko (1 zdanie) podsumuj czy zabieg jest wskazany.
6. Zapytaj wprost: "Czy chciałaby Pani wybrać termin?"
7. Jeśli TAK – napisz dokładnie i tylko to słowo: SHOW_SLOTS
8. Jeśli przeciwwskazanie – zaznacz delikatnie, zaproponuj konsultację.
9. Przed końcem poproś o email na podsumowanie, możesz użyć imienia po raz ostatni.

{zabiegi}

PROMOCJE:
{chr(10).join(f"- {p}" for p in PROMOTIONS)}

KONTAKT:
ul. Złota 12, Warszawa | +48 500 123 456 | hello@beautyflow.pl | Pon–Pt 9–20, Sob 9–16
"""

KNOWLEDGE_BASE = build_knowledge_base()

# ─────────────────────────────────────────────
# CSS
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

    [data-testid="stAppViewBlockContainer"] {
        max-width: 860px !important;
        padding: 0 2rem !important;
        margin: 0 auto !important;
    }

    @media (max-width: 900px) {
        [data-testid="stAppViewBlockContainer"] {
            max-width: 100% !important;
            padding: 0 1rem !important;
        }
    }

    /* ── SIDEBAR – widoczny i stylowany ── */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
        display: flex !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--text) !important;
        font-family: 'Outfit', sans-serif !important;
    }
    /* Przycisk wysuwania sidebara zawsze widoczny */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    button[kind="header"] {
        display: flex !important;
        visibility: visible !important;
    }

    h1, h2, h3 {
        font-family: 'Cormorant', serif !important;
        color: var(--text) !important;
        font-weight: 500 !important;
    }

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
        font-size: 1.05rem !important;
        line-height: 1.75 !important;
    }
    [data-testid="stChatMessage"] strong {
        color: var(--accent2) !important;
        font-weight: 600 !important;
    }

    [data-testid="stChatInputTextArea"] {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border2) !important;
        border-radius: 10px !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 1.05rem !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
    }
    [data-testid="stChatInputTextArea"]:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 3px rgba(184,150,62,0.1) !important;
    }

    .stButton > button {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        letter-spacing: 0.03em !important;
        padding: 0.55rem 1.2rem !important;
        transition: background 0.15s, transform 0.1s !important;
    }
    .stButton > button:hover {
        background: var(--accent2) !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #ffffff !important;
    }

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

    [data-testid="stSidebar"] [data-testid="stDateInput"] input,
    [data-testid="stSidebar"] [data-testid="stTimeInput"] input {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-family: 'Outfit', sans-serif !important;
    }

    [data-testid="stSidebar"] [data-testid="stDateInput"] label,
    [data-testid="stSidebar"] [data-testid="stTimeInput"] label {
        display: none !important;
    }

    .proc-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 12px;
        transition: box-shadow 0.2s, border-color 0.2s;
        cursor: default;
    }
    .proc-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.07);
        border-color: var(--border2);
    }
    .proc-card .name  {
        font-family: 'Cormorant', serif;
        font-size: 1.2rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 4px;
    }
    .proc-card .tag   { font-size: 0.86rem; color: var(--text3); }
    .proc-card .meta  {
        font-size: 0.84rem;
        color: var(--text2);
        margin-top: 10px;
        display: flex;
        gap: 12px;
    }
    .proc-card .meta span {
        background: var(--surface2);
        border-radius: 4px;
        padding: 3px 10px;
    }

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

    hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

    #MainMenu, header, footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    @media (max-width: 640px) {
        .proc-card { padding: 0.85rem 1rem; }
        .proc-card .name { font-size: 0.95rem; }
    }

    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div style="padding: 2rem 0 0.6rem;">
        <div style="font-family:'Cormorant',serif;font-size:2.6rem;font-weight:500;
                    color:#1a1a1a;letter-spacing:0.04em;line-height:1.0;">
            BeautyFlow
        </div>
        <div style="font-size:0.75rem;letter-spacing:0.22em;color:#a8a49a;
                    text-transform:uppercase;margin-top:7px;">
            Konsultant AI — Studio Urody
        </div>
    </div>
    """, unsafe_allow_html=True)

    promo_txt = " &nbsp;·&nbsp; ".join(PROMOTIONS)
    st.markdown(f"""
    <div style="background:#f5f4f0;border:1px solid #e8e6e0;border-radius:10px;
                padding:0.85rem 1.3rem;margin:1rem 0 1.6rem;font-size:0.88rem;
                color:#6b6860;line-height:2.0;">
      <span style="color:#1a1a1a;font-weight:500;">ul. Złota 12, Warszawa</span>
      &nbsp;·&nbsp; +48 500 123 456
      &nbsp;·&nbsp; Pon–Pt 9–20, Sob 9–16
      <br>
      <span style="color:#b8963e;font-size:0.8rem;">Promocje:</span>
      <span style="color:#a8a49a;font-size:0.8rem;">{promo_txt}</span>
    </div>
    <div class="loading-bar"></div>
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
            max_tokens=300,
            temperature=0.6,
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
  .btn-ok  { background:#3d7a5a; color:#fff !important; }
  .btn-no  { background:#c0392b; color:#fff !important; }
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
        st.warning(f"Email error: {e}")
        return False


def send_consultation_emails(procedure: str, info: dict, messages: list) -> dict:
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
        gmail_user = st.secrets["email"]["gmail_user"]
    except Exception:
        return {"error": "brak konfiguracji email"}

    proc    = PROCEDURES.get(procedure, {})
    imie    = info.get("imie", "Klientko")
    email   = info.get("email", "")
    termin  = info.get("termin", "")
    podsum  = info.get("podsumowanie", "—")
    token   = info.get("token", "")
    teraz   = datetime.now().strftime("%d.%m.%Y, %H:%M")

    if email and "@" in email:
        termin_line = f"<br>Proponowany termin: <strong>{termin}</strong>" if termin else ""
        html_client = f"""<!DOCTYPE html><html><head>{EMAIL_STYLE}</head><body>
        <div class="wrap">
          <div class="hdr"><h1>BeautyFlow</h1><p>Zgłoszenie przyjęte</p></div>
          <div class="body">
            <p>Cześć, <strong>{imie}</strong>!</p>
            <p>Twoje zgłoszenie dotarło do nas. Umówiłaś się na:</p>
            <div class="box">
              <strong>{procedure}</strong><br>
              Czas: {proc.get('time','—')} &nbsp;·&nbsp; Cena: {proc.get('price','—')}
              {termin_line}
            </div>
            <p>Specjalistka potwierdzi termin — dostaniesz osobnego maila z potwierdzeniem i wskazówkami jak się przygotować.</p>
            <p>Masz pytania? Zadzwoń: <strong>+48 500 123 456</strong></p>
            <p style="color:#a8a49a;font-size:0.82rem;">— Zespół BeautyFlow</p>
          </div>
          <div class="ftr">ul. Złota 12, Warszawa · +48 500 123 456 · hello@beautyflow.pl</div>
        </div></body></html>"""
        results["client"] = _send_email(email, f"BeautyFlow – zgłoszenie: {procedure}", html_client)

    if owner_email:
        if token and app_url:
            confirm_url = f"{app_url}?action=confirm&token={token}"
            reject_url  = f"{app_url}?action=reject&token={token}"
            action_html = f"""
            <div style="margin:24px 0 8px;">
              <p style="font-size:0.85rem;color:#6b6860;margin-bottom:14px;">
                Kliknij poniżej aby podjąć decyzję — klientka automatycznie dostanie maila z odpowiedzią:
              </p>
              <a href="{confirm_url}" class="btn btn-ok" style="font-size:0.9rem;padding:13px 30px;">✓ Potwierdź termin</a>
              &nbsp;&nbsp;
              <a href="{reject_url}"  class="btn btn-no" style="font-size:0.9rem;padding:13px 30px;">✗ Odrzuć</a>
            </div>
            <p style="color:#a8a49a;font-size:0.75rem;margin-top:20px;">
              Linki są jednorazowe · po kliknięciu otworzy się aplikacja i wykona akcję automatycznie.
            </p>
            <p style="margin-top:16px;">
              <a href="{app_url}" style="font-size:0.82rem;color:#b8963e;text-decoration:none;">
                → Otwórz panel aplikacji
              </a>
            </p>"""
        elif termin:
            panel_link = f'<p style="margin-top:12px;"><a href="{app_url}" style="font-size:0.82rem;color:#b8963e;text-decoration:none;">→ Otwórz panel aplikacji</a></p>' if app_url else ""
            action_html = f"<p style='color:#6b6860;'>Zaloguj się do panelu aby potwierdzić termin: <strong>{termin}</strong></p>{panel_link}"
        else:
            action_html = ""

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
            <div class="box" style="font-size:0.83rem;color:#6b6860;">{podsum}</div>
            {action_html}
          </div>
          <div class="ftr">BeautyFlow AI · System automatyczny</div>
        </div></body></html>"""
        results["owner"] = _send_email(owner_email, f"🌿 Nowa rezerwacja: {imie} — {procedure} ({termin or 'brak terminu'})", html_owner)

    return results


def send_status_email(booking: dict, confirmed: bool) -> bool:
    email = booking.get("email", "")
    if not email or "@" not in email:
        return False
    imie   = booking.get("imie", "Klientko")
    zabieg = booking.get("zabieg", "—")
    termin = booking.get("termin", "—")
    proc   = PROCEDURES.get(zabieg, {})
    if confirmed:
        subj = "BeautyFlow – Twój termin potwierdzony ✓"
        body = f"""<p>Twój termin jest potwierdzony!</p>
        <div class="box">
          Zabieg: <strong>{zabieg}</strong><br>
          Termin: <strong>{termin}</strong><br>
          Adres: ul. Złota 12, Warszawa
        </div>
        <div class="box">
          <strong>Jak się przygotować:</strong><br>{proc.get('prep','—')}
        </div>
        <p>Do zobaczenia! W razie pytań: <strong>+48 500 123 456</strong></p>"""
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
# OBSŁUGA LINKÓW AKCJI W URL
# ─────────────────────────────────────────────
def handle_url_action():
    params = st.query_params
    action = params.get("action", "")
    token  = params.get("token", "")
    if not action or not token:
        return

    pending = st.session_state.get("pending_bookings", [])
    booking = next((b for b in pending if b.get("token") == token), None)

    if action == "confirm" and booking:
        save_slot(booking.get("termin", ""), "zajęty")
        update_booking_in_sheet(token, "potwierdzona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"):
                s["zajety"] = True
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=True)
        st.success(f"Rezerwacja potwierdzona — {booking.get('imie')} · {booking.get('termin')}")
        st.query_params.clear()

    elif action == "reject" and booking:
        save_slot(booking.get("termin", ""), "wolny")
        update_booking_in_sheet(token, "odrzucona")
        for s in st.session_state.get("available_slots", []):
            if s["termin"] == booking.get("termin"):
                s["zajety"] = False
        st.session_state.pending_bookings = [b for b in pending if b.get("token") != token]
        send_status_email(booking, confirmed=False)
        st.info("Rezerwacja odrzucona — klientka poinformowana emailem.")
        st.query_params.clear()

    elif booking is None and token:
        st.warning("Link wygasł lub rezerwacja już została przetworzona.")
        st.query_params.clear()

# ─────────────────────────────────────────────
# PANEL WŁAŚCICIELKI – w sidebarze (wysuwany)
# ─────────────────────────────────────────────
def render_owner_panel():
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 0 0.6rem;">
          <div style="font-family:'Cormorant',serif;font-size:1.4rem;font-weight:500;color:#1a1a1a;">
            BeautyFlow
          </div>
          <div style="font-size:0.62rem;letter-spacing:0.18em;color:#a8a49a;
                      text-transform:uppercase;margin-top:4px;margin-bottom:14px;">
            Panel właścicielki
          </div>
        </div>
        <div style="height:1px;background:#e8e6e0;margin-bottom:1rem;"></div>
        """, unsafe_allow_html=True)

        if "owner_auth" not in st.session_state:
            st.session_state.owner_auth = False

        if not st.session_state.owner_auth:
            pw = st.text_input(
                "Hasło",
                type="password",
                key="opw",
                placeholder="Hasło dostępu...",
                label_visibility="collapsed",
            )
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

        st.markdown('<div style="font-size:0.74rem;color:#3d7a5a;margin-bottom:10px;">✓ Zalogowano</div>',
                    unsafe_allow_html=True)

        # ── Status integracji ──
        groq_ok   = "app" in st.secrets and "groq_api_key" in st.secrets.get("app", {})
        sheets_ok = "gcp_service_account" in st.secrets
        email_ok  = "email" in st.secrets
        def dot(ok): return f'<span style="color:{"#3d7a5a" if ok else "#c0392b"};font-size:0.55rem;">&#9679;</span>'
        st.markdown(
            f'<div style="font-size:0.72rem;color:#a8a49a;margin-bottom:14px;">'
            f'{dot(groq_ok)} Groq &nbsp; {dot(sheets_ok)} Sheets &nbsp; {dot(email_ok)} Gmail</div>',
            unsafe_allow_html=True
        )

        # ── Dodaj termin ──
        st.markdown('<div style="font-size:0.76rem;font-weight:500;color:#1a1a1a;margin-bottom:6px;">Dodaj termin</div>',
                    unsafe_allow_html=True)

        proc_names = list(PROCEDURES.keys())
        sel_proc = st.selectbox("Zabieg", proc_names, key="slot_proc", label_visibility="collapsed")

        dc1, dc2 = st.columns([3, 2])
        with dc1:
            slot_date = st.date_input(
                "Data", value=date.today(), key="slot_date_picker",
                label_visibility="collapsed", format="DD.MM.YYYY",
            )
        with dc2:
            available_hours = [f"{h:02d}:{m:02d}" for h in range(9, 20) for m in [0, 30]]
            sel_hour = st.selectbox("Godzina", available_hours, key="slot_hour_picker",
                                    label_visibility="collapsed")

        ca, cb = st.columns(2)
        with ca:
            if st.button("Dodaj", key="addslot", use_container_width=True):
                termin_str = f"{slot_date.strftime('%d.%m.%Y')}, {sel_hour}"
                existing = [s["termin"] for s in st.session_state.get("available_slots", [])]
                if termin_str in existing:
                    st.warning("Ten termin już istnieje")
                else:
                    new_slot = {"termin": termin_str, "zabieg": sel_proc, "zajety": False}
                    st.session_state.available_slots.append(new_slot)
                    save_slot(termin_str, "wolny", sel_proc)
                    st.rerun()
        with cb:
            if st.button("Wyczyść", key="clrslot", use_container_width=True):
                st.session_state.available_slots = [
                    s for s in st.session_state.available_slots if s["zajety"]
                ]
                try:
                    sp = get_spreadsheet()
                    if sp:
                        ws = sp.worksheet("Terminy")
                        rows = ws.get_all_records()
                        to_delete = [i+2 for i, r in enumerate(rows) if r.get("Status") == "wolny"]
                        for i in reversed(to_delete):
                            ws.delete_rows(i)
                except Exception:
                    pass
                st.rerun()

        # ── Lista terminów ──
        slots_all = st.session_state.get("available_slots", [])
        if slots_all:
            st.markdown('<div style="height:1px;background:#e8e6e0;margin:10px 0 6px;"></div>',
                        unsafe_allow_html=True)
            by_proc = {}
            for s in slots_all:
                key = s.get("zabieg", "Inne")
                by_proc.setdefault(key, []).append(s)
            for proc_name, proc_slots in by_proc.items():
                st.markdown(
                    f'<div style="font-size:0.63rem;letter-spacing:0.1em;color:#a8a49a;'
                    f'text-transform:uppercase;margin:8px 0 3px;">{proc_name}</div>',
                    unsafe_allow_html=True
                )
                for s in proc_slots:
                    dot_c  = "#c0392b" if s["zajety"] else "#3d7a5a"
                    status = " — zajęty" if s["zajety"] else ""
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#6b6860;padding:2px 0;">'
                        f'<span style="color:{dot_c};font-size:0.55rem;">&#9679;</span> '
                        f'{s["termin"]}<span style="color:#bbb">{status}</span></div>',
                        unsafe_allow_html=True
                    )

        # ── Rezerwacje do potwierdzenia ──
        pending = st.session_state.get("pending_bookings", [])
        if pending:
            st.markdown('<div style="height:1px;background:#e8e6e0;margin:12px 0 6px;"></div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.63rem;letter-spacing:0.15em;text-transform:uppercase;'
                        f'color:#a8a49a;margin-bottom:8px;">Do potwierdzenia ({len(pending)})</div>',
                        unsafe_allow_html=True)
            for i, b in enumerate(pending):
                st.markdown(
                    f'<div style="font-size:0.76rem;color:#1a1a1a;line-height:1.7;'
                    f'background:#fafaf8;border:1px solid #e8e6e0;border-radius:8px;'
                    f'padding:8px 10px;margin-bottom:8px;">'
                    f'<strong>{b.get("imie","?")}</strong><br>'
                    f'<span style="color:#6b6860;font-size:0.70rem;">{b.get("zabieg","?")}</span><br>'
                    f'<span style="color:#a8a49a;font-size:0.70rem;">{b.get("termin","?")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✓ Potwierdź", key=f"ok_{i}", use_container_width=True):
                        save_slot(b.get("termin",""), "zajęty")
                        update_booking_in_sheet(b.get("token",""), "potwierdzona")
                        for s in st.session_state.available_slots:
                            if s["termin"] == b.get("termin"):
                                s["zajety"] = True
                        send_status_email(b, confirmed=True)
                        st.session_state.pending_bookings.pop(i)
                        st.rerun()
                with c2:
                    if st.button("✗ Odrzuć", key=f"no_{i}", use_container_width=True):
                        save_slot(b.get("termin",""), "wolny")
                        update_booking_in_sheet(b.get("token",""), "odrzucona")
                        for s in st.session_state.available_slots:
                            if s["termin"] == b.get("termin"):
                                s["zajety"] = False
                        send_status_email(b, confirmed=False)
                        st.session_state.pending_bookings.pop(i)
                        st.rerun()

        st.markdown('<div style="height:1px;background:#e8e6e0;margin:14px 0 8px;"></div>',
                    unsafe_allow_html=True)
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
    if st.session_state.get("_picker_loading"):
        name = st.session_state["_picker_loading"]
        st.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)
        intro = ask_groq(
            messages=[{"role": "user", "content": f"Interesuję się zabiegiem: {name}"}],
            system=KNOWLEDGE_BASE + f"\nKlientka wybrała: {name}. Przywitaj się (1 zdanie), zadaj PIERWSZE pytanie kwalifikujące."
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
      <div style="font-family:'Cormorant',serif;font-size:2rem;font-weight:500;
                  color:#1a1a1a;line-height:1.2;margin-bottom:10px;">
        Na co chcesz się umówić?
      </div>
      <div style="font-size:1rem;color:#a8a49a;">
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

    col_title, col_back = st.columns([5, 1])
    with col_title:
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
          <div style="font-family:'Cormorant',serif;font-size:1.6rem;font-weight:500;color:#1a1a1a;">
            {procedure}
          </div>
          <div style="font-size:0.9rem;color:#a8a49a;margin-top:3px;">{p.get('tagline','')} · Sofia</div>
        </div>
        """, unsafe_allow_html=True)
    with col_back:
        if st.button("← Zmień", key="back"):
            st.session_state.chat_stage  = "pick"
            st.session_state.messages    = []
            st.session_state.saved       = False
            st.session_state.slot_chosen = None
            st.rerun()

    st.markdown('<div style="height:1px;background:#e8e6e0;margin-bottom:1rem;"></div>',
                unsafe_allow_html=True)

    # Historia czatu
    for msg in messages:
        avatar  = "🌿" if msg["role"] == "assistant" else "👤"
        content = msg["content"]
        if content.strip() == "SHOW_SLOTS":
            content = "Poniżej dostępne terminy — proszę wybrać:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(content)

    # Przyciski terminów
    show_slots = (
        not saved
        and not st.session_state.get("slot_chosen")
        and any(m["content"].strip() == "SHOW_SLOTS"
                for m in messages if m["role"] == "assistant")
    )
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
                                "Powiedz krótko (1-2 zdania) że zgłoszenie zostało przyjęte i CZEKA NA POTWIERDZENIE przez specjalistkę — NIE mów że jest już umówiona ani że termin jest potwierdzony. "
                                "Poproś o email do wysłania podsumowania. "
                                "Na końcu wiadomości napisz dokładnie to zdanie: 'Gdy wszystko gotowe, kliknij przycisk „Zapisz i wyślij podsumowanie\" poniżej.'"
                            )
                        )
                        loading.empty()
                        messages.append({"role": "assistant", "content": reply})
                        st.session_state.messages = messages
                        st.rerun()
        else:
            st.info("Brak dostępnych terminów. Możemy zapisać Twoje dane — specjalistka oddzwoni.")

    # ── Oblicz can_save ──
    can_save_now = (
        not saved
        and len(messages) >= 5
        and (st.session_state.get("slot_chosen") or len(messages) >= 8)
    )

    # ── Input czatu ──
    if not saved and not show_slots:
        if prompt := st.chat_input("Napisz do Sofii..."):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            loading = st.empty()
            loading.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

            extra_system = f"\nAktualnie omawiany zabieg: {procedure}"
            if can_save_now:
                extra_system += (
                    "\nROZMOWA DOBIEGŁA KOŃCA. Zakończ rozmowę naturalnie i na końcu swojej "
                    "odpowiedzi KONIECZNIE dodaj (jako osobny akapit) dokładnie to zdanie: "
                    "'Gdy wszystko gotowe, kliknij przycisk „Zapisz i wyślij podsumowanie\" poniżej.'"
                )

            with st.chat_message("assistant", avatar="🌿"):
                reply = ask_groq(
                    messages=messages,
                    system=KNOWLEDGE_BASE + extra_system
                )
                display = "Poniżej dostępne terminy — proszę wybrać:" \
                          if reply.strip() == "SHOW_SLOTS" else reply
                st.markdown(display)

            loading.empty()
            messages.append({"role": "assistant", "content": reply})
            st.session_state.messages = messages
            st.rerun()

    # ── Przycisk "Zapisz i wyślij" ──
    if can_save_now:
        st.markdown('<div style="height:1px;background:#e8e6e0;margin:1.5rem 0 0.8rem;"></div>',
                    unsafe_allow_html=True)
        _, col_btn, _ = st.columns([1, 2, 1])
        with col_btn:
            if st.button("💾 Zapisz i wyślij podsumowanie", use_container_width=True, key="save_btn"):
                loading = st.empty()
                loading.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

                info = extract_client_info(messages)
                if st.session_state.get("slot_chosen"):
                    info["termin"] = st.session_state.slot_chosen

                tok = secrets.token_urlsafe(16)
                info["token"] = tok

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

                lines = []
                if sheet_ok:
                    lines.append("Zapisano w arkuszu")
                if email_r.get("client"):
                    lines.append(f"Email wysłany do klientki ({info.get('email','')})")
                if email_r.get("owner"):
                    lines.append("Powiadomienie wysłane do właścicielki")
                if st.session_state.get("slot_chosen"):
                    lines.append(f"Rezerwacja {st.session_state.slot_chosen} oczekuje na potwierdzenie")

                st.success("  \n".join(lines) if lines else "Zapisano!")
                st.session_state.saved = True
                st.rerun()

    # Zakończono
    if saved:
        st.success("Konsultacja zakończona i zapisana.")
        _, col_new, _ = st.columns([1, 2, 1])
        with col_new:
            if st.button("Nowa konsultacja", use_container_width=True, key="new_btn"):
                st.session_state.messages         = []
                st.session_state.saved            = False
                st.session_state.slot_chosen      = None
                st.session_state.chat_stage       = "pick"
                st.session_state.chosen_procedure = ""
                st.rerun()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
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
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    handle_url_action()

    # Panel właścicielki w sidebarze – całkowicie poza głównym layoutem strony
    render_owner_panel()

    render_header()

    if st.session_state.chat_stage == "pick":
        render_picker()
    else:
        render_chat()


if __name__ == "__main__":
    main()
