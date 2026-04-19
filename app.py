# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny
# Stack: Streamlit + Grok (xAI) + Google Sheets + Gmail SMTP
# ============================================================
#
# STREAMLIT SECRETS – wklej DOKŁADNIE TO w App Settings → Secrets:
#
# [app]
# groq_api_key    = "gsk_TWÓJ_KLUCZ"         ← z console.groq.com (darmowe!)
# owner_password  = "TwojeHaslo123"
# owner_email     = "wlascicielka@gmail.com" ← Twój email – tu przyjdzie powiadomienie
#
# [email]
# gmail_user      = "twoj@gmail.com"         ← Gmail z którego wysyłasz
# gmail_password  = "abcd efgh ijkl mnop"    ← App Password z myaccount.google.com
#                                               → Bezpieczeństwo → Hasła do aplikacji
#
# [sheets]
# sheet_id        = "ID_ARKUSZA_Z_URL"       ← docs.google.com/spreadsheets/d/[TU]/edit
#
# [gcp_service_account]
# type            = "service_account"
# project_id      = "beautyflow-ai"
# private_key_id  = "..."
# private_key     = "-----BEGIN RSA PRIVATE KEY-----\nMII...\n-----END RSA PRIVATE KEY-----\n"
# client_email    = "beautyflow@beautyflow-ai.iam.gserviceaccount.com"
# client_id       = "..."
# auth_uri        = "https://accounts.google.com/o/oauth2/auth"
# token_uri       = "https://oauth2.googleapis.com/token"
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BeautyFlow AI",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# BAZA WIEDZY + ZABIEGI
# ─────────────────────────────────────────────
PROCEDURES = {
    "Mezoterapia Igłowa": {
        "emoji": "💉",
        "tagline": "Głęboka regeneracja & nawilżenie",
        "time": "60 min",
        "price": "od 350 zł",
        "series": "3–6 zabiegów co 2–3 tygodnie",
        "effects": "Nawilżenie, redukcja zmarszczek, rozjaśnienie, poprawa owalu twarzy",
        "contraindications": "Ciąża, karmienie, aktywna opryszczka, retinoidy lub leki rozrzedzające krew, choroby autoimmunologiczne, aktywne stany zapalne skóry",
        "prep": "Unikać alkoholu 24h przed, bez kwasów 3 dni przed",
        "questions": [
            "Czy stosuje Pani aktualnie retinoidy lub leki rozrzedzające krew (np. Aspirin)?",
            "Czy ma Pani aktywne stany zapalne skóry lub opryszczkę?",
            "Jak określiłaby Pani typ swojej skóry – sucha, normalna, tłusta czy mieszana?",
            "Czy miała już Pani mezoterapię wcześniej?",
        ],
    },
    "Laminacja Rzęs": {
        "emoji": "👁️",
        "tagline": "Naturalne podkręcenie na 6–8 tygodni",
        "time": "90 min",
        "price": "od 180 zł",
        "series": "jednorazowy, powtarzać co 6–8 tyg.",
        "effects": "Naturalne podkręcenie, optyczne pogrubienie i wydłużenie rzęs",
        "contraindications": "Alergia na kleje kosmetyczne, aktywne infekcje oczu, chemioterapia, rzęsy poniżej 4mm",
        "prep": "Bez tuszu do rzęs i odżywek 24h przed",
        "questions": [
            "Czy miała Pani kiedyś reakcję alergiczną po zabiegu kosmetycznym przy oczach?",
            "Czy stosuje Pani krople lub inne leki okulistyczne?",
            "Jak długie są Pani naturalne rzęsy – krótkie, średnie czy długie?",
            "Czy nosi Pani soczewki kontaktowe?",
        ],
    },
    "Powiększanie Ust": {
        "emoji": "💋",
        "tagline": "Kwas hialuronowy – kontur & objętość",
        "time": "45 min",
        "price": "od 600 zł (0.5ml) / 900 zł (1ml)",
        "series": "jednorazowy, powtarzać co 9–12 mies.",
        "effects": "Większa objętość, lepszy kontur, nawilżenie, symetria",
        "contraindications": "Ciąża, karmienie, skłonność do keloidów, choroby tkanki łącznej, aktywna opryszczka wargowa, ibuprofen/aspiryna 3 dni przed",
        "prep": "Bez makijażu ust, unikać leków rozrzedzających krew 3 dni przed",
        "questions": [
            "Czy miała Pani już wcześniej wypełnianie ust? Jeśli tak, kiedy ostatnio?",
            "Czy ma Pani skłonność do keloidów lub nadmiernego bliznowacenia?",
            "Czy choruje Pani na choroby autoimmunologiczne (np. toczeń, twardzina)?",
            "Jaki efekt Panią interesuje – subtelny, wyraźny, a może głównie poprawa konturu?",
        ],
    },
    "Peeling Kawitacyjny": {
        "emoji": "✨",
        "tagline": "Głębokie oczyszczanie ultradźwiękami",
        "time": "45 min",
        "price": "150 zł",
        "series": "jednorazowy lub seria co 2–4 tyg.",
        "effects": "Głęboko oczyszczona skóra, zwężone pory, wyrównana cera",
        "contraindications": "Rozrusznik serca, metalowe implanty w twarzy, aktywne stany zapalne, ciąża",
        "prep": "Przyjść z umytą twarzą, bez makijażu",
        "questions": [
            "Czy ma Pani rozrusznik serca lub metalowe implanty w okolicach twarzy?",
            "Czy skóra jest teraz w dobrym stanie, czy ma Pani aktywne stany zapalne lub trądzik?",
            "Czy to będzie Pani pierwszy peeling kawitacyjny?",
        ],
    },
}

PROMOTIONS = [
    "Pakiet 3× Mezoterapia: **900 zł** *(oszczędzasz 150 zł)*",
    "Laminacja Rzęs + Peeling Kawitacyjny: **300 zł**",
    "Nowe klientki: **-10%** na pierwszą wizytę",
]

KNOWLEDGE_BASE = f"""
Jesteś Sofią – elegancką, empatyczną konsultantką salonu kosmetycznego BeautyFlow w Warszawie.
Rozmawiasz WYŁĄCZNIE po polsku. Jesteś ciepła, profesjonalna, nigdy nie używasz żargonu medycznego.
Nie wymyślasz informacji spoza poniższej bazy. Jeśli pytanie wykracza poza bazę, odsyłasz do telefonu: +48 500 123 456.

ETAPY ROZMOWY – przestrzegaj kolejności:
1. WYWIAD: Przywitaj się, zapytaj o imię. Zadawaj pytania kwalifikujące STOPNIOWO (1-2 naraz).
2. PODSUMOWANIE: Po zebraniu wszystkich odpowiedzi powiedz krótko czy zabieg jest odpowiedni.
3. REZERWACJA: Zapytaj wprost "Czy chciałaby Pani od razu zarezerwować termin?" – NIE pokazuj terminów, system zrobi to automatycznie przyciskami.
4. EMAIL: Jeśli klientka chce rezerwację – poproś o imię (jeśli nie podała) i adres email na podsumowanie.
5. Jeśli pojawia się przeciwwskazanie – delikatnie sygnalizuj i sugeruj konsultację ze specjalistką.
6. Bądź naturalna, ciepła. Nie zadawaj wszystkich pytań naraz.

WAŻNE: Kiedy zapytasz o rezerwację i klientka odpowie TAK – napisz dokładnie to zdanie (nic więcej):
"SHOW_SLOTS"
To jest sygnał dla systemu żeby pokazał przyciski z terminami.

=== BAZA ZABIEGÓW ===
{chr(10).join([
    f"""
ZABIEG: {name}
Tagline: {p["tagline"]}
Czas: {p["time"]} | Cena: {p["price"]}
Seria: {p["series"]}
Efekty: {p["effects"]}
Przeciwwskazania: {p["contraindications"]}
Przygotowanie: {p["prep"]}
Pytania kwalifikujące (zadawaj stopniowo): {" / ".join(p["questions"])}
"""
    for name, p in PROCEDURES.items()
])}

=== PROMOCJE ===
- Pakiet 3x Mezoterapia: 900 zł (oszczędzasz 150 zł)
- Laminacja Rzęs + Peeling Kawitacyjny: 300 zł
- Nowe klientki: 10% zniżki na pierwszą wizytę

=== KONTAKT ===
Adres: ul. Złota 12, Warszawa (blisko metra Świętokrzyska)
Tel: +48 500 123 456
Email: hello@beautyflow.pl
Godziny: Pon–Pt 9:00–20:00, Sobota 9:00–16:00
"""

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500&display=swap');

    :root {
        --navy:   #0f1f3d;
        --navy2:  #162847;
        --navy3:  #1e3560;
        --butter: #f5d776;
        --butter2:#e8c94e;
        --white:  #f8f4ed;
        --muted:  rgba(248,244,237,0.55);
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--navy) !important;
        color: var(--white) !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stSidebar"] {
        background: var(--navy2) !important;
        border-right: 1px solid rgba(245,215,118,0.15) !important;
    }
    [data-testid="stSidebar"] * { color: var(--white) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(245,215,118,0.15) !important; }
    h1,h2,h3 {
        font-family: 'DM Serif Display', serif !important;
        color: var(--butter) !important;
    }
    [data-testid="stChatMessage"] {
        background: var(--navy2) !important;
        border: 1px solid rgba(245,215,118,0.12) !important;
        border-radius: 16px !important;
        margin-bottom: 0.5rem !important;
        animation: fadeUp 0.3s ease forwards;
    }
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] em {
        color: #f8f4ed !important;
        font-size: 0.97rem !important;
        line-height: 1.7 !important;
    }
    [data-testid="stChatMessage"] strong {
        color: #f5d776 !important;
        font-weight: 600 !important;
    }
    @keyframes fadeUp {
        from { opacity:0; transform: translateY(8px); }
        to   { opacity:1; transform: translateY(0); }
    }
    [data-testid="stChatInputTextArea"] {
        background: var(--navy2) !important;
        color: var(--white) !important;
        border: 1px solid rgba(245,215,118,0.3) !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stButton > button {
        background: var(--butter) !important;
        color: var(--navy) !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: var(--butter2) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(245,215,118,0.25) !important;
    }
    .stTextInput > div > div > input {
        background: var(--navy2) !important;
        color: var(--white) !important;
        border: 1px solid rgba(245,215,118,0.25) !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .proc-card {
        background: var(--navy2);
        border: 1px solid rgba(245,215,118,0.15);
        border-radius: 16px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.6rem;
        transition: all 0.2s ease;
        animation: fadeUp 0.4s ease forwards;
    }
    .proc-card:hover {
        border-color: var(--butter);
        background: var(--navy3);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(245,215,118,0.1);
    }
    .proc-card .card-emoji { font-size: 1.4rem; margin-right: 0.6rem; }
    .proc-card .card-title { font-family:'DM Serif Display',serif; color: var(--butter); font-size: 1.05rem; }
    .proc-card .card-tag   { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
    .proc-card .card-meta  { font-size: 0.76rem; color: var(--butter2); margin-top: 0.4rem; }
    .promo-pill {
        display: inline-block;
        background: rgba(245,215,118,0.1);
        border: 1px solid rgba(245,215,118,0.25);
        border-radius: 20px;
        padding: 0.25rem 0.75rem;
        font-size: 0.75rem;
        color: var(--butter);
        margin: 0.15rem 0;
    }
    hr { border-color: rgba(245,215,118,0.15) !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: rgba(245,215,118,0.3); border-radius: 2px; }
    #MainMenu, header, footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
def render_logo():
    st.markdown("""
    <div style="display:flex;align-items:center;gap:18px;padding:1.8rem 0 0.8rem;">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="14" fill="#f5d776" opacity="0.12"/>
            <path d="M24 6 L28 18 L40 18 L30 26 L34 38 L24 30 L14 38 L18 26 L8 18 L20 18 Z"
                  fill="#f5d776" opacity="0.9"/>
        </svg>
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.9rem;color:#f5d776;letter-spacing:0.06em;line-height:1.0;">
                BeautyFlow
            </div>
            <div style="font-family:'DM Sans',sans-serif;font-size:0.65rem;letter-spacing:0.3em;
                        color:rgba(248,244,237,0.45);text-transform:uppercase;margin-top:3px;">
                AI Konsultant · Sofia
            </div>
        </div>
    </div>
    <div style="height:1px;background:linear-gradient(90deg,rgba(245,215,118,0.4),transparent);margin-bottom:1.4rem;"></div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GROQ API (groq.com – darmowe!)
# ─────────────────────────────────────────────
@st.cache_resource
def get_groq_client():
    try:
        return OpenAI(
            api_key=st.secrets["app"]["groq_api_key"],
            base_url="https://api.groq.com/openai/v1",
        )
    except Exception as e:
        st.error(f"❌ Brak klucza Groq API: {e}")
        return None


def ask_groq(messages: list, system: str = None) -> str:
    client = get_groq_client()
    if not client:
        return "Przepraszam, wystąpił problem techniczny. Proszę zadzwonić: +48 500 123 456."
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system or KNOWLEDGE_BASE}] + messages,
            max_tokens=600,
            temperature=0.72,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Przepraszam, błąd: {e}"


def extract_client_info(messages: list) -> dict:
    """Grok wyciąga imię, email i telefon klientki z historii rozmowy."""
    client = get_groq_client()
    if not client:
        return {}
    try:
        history = "\n".join([f"{m['role'].upper()}: {m['content'][:150]}" for m in messages[-12:]])
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": (
                f"Z tej rozmowy wyciągnij dane klientki.\n"
                f"Odpowiedz TYLKO w tym formacie, bez żadnego dodatkowego tekstu:\n"
                f"IMIE: xxx\n"
                f"EMAIL: xxx lub brak\n"
                f"TELEFON: xxx lub brak\n"
                f"PODSUMOWANIE: 2-3 zdania co klientka chce i jakie odpowiedzi udzieliła\n\n"
                f"Rozmowa:\n{history}"
            )}],
            max_tokens=150,
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
def send_emails(procedure: str, client_info: dict, messages: list) -> dict:
    """
    Wysyła dwa emaile:
    1. Do klientki – piękne podsumowanie konsultacji w HTML
    2. Do właścicielki – powiadomienie z danymi klientki
    Zwraca {"client": bool, "owner": bool}
    """
    try:
        gmail_user = st.secrets["email"]["gmail_user"]
        gmail_pass = st.secrets["email"]["gmail_password"]
        owner_email = st.secrets["app"]["owner_email"]
    except Exception:
        return {"client": False, "owner": False, "error": "Brak konfiguracji email w Secrets"}

    imie = client_info.get("imie", "Klientko")
    client_email = client_info.get("email", "")
    podsumowanie = client_info.get("podsumowanie", "Konsultacja zakończona.")
    proc_data = PROCEDURES.get(procedure, {})
    teraz = datetime.now().strftime("%d.%m.%Y o %H:%M")

    results = {"client": False, "owner": False}

    # ── HTML template emaila ──────────────────
    def make_html(title: str, body_html: str) -> str:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Georgia', serif; background:#f8f4ed; margin:0; padding:0; }}
            .wrap {{ max-width:560px; margin:40px auto; background:#fff; border-radius:16px;
                     overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
            .header {{ background:#0f1f3d; padding:32px 40px; text-align:center; }}
            .header h1 {{ color:#f5d776; font-size:1.6rem; margin:0; letter-spacing:0.08em; }}
            .header p  {{ color:rgba(248,244,237,0.6); font-size:0.75rem;
                          letter-spacing:0.25em; text-transform:uppercase; margin:6px 0 0; }}
            .body {{ padding:32px 40px; color:#1a1a2e; line-height:1.7; }}
            .body h2 {{ color:#0f1f3d; font-size:1.1rem; margin-bottom:0.5rem; }}
            .pill {{ display:inline-block; background:#f5d776; color:#0f1f3d;
                     border-radius:20px; padding:4px 14px; font-size:0.8rem;
                     font-weight:600; margin-bottom:1rem; }}
            .info-box {{ background:#f8f4ed; border-left:3px solid #f5d776;
                         border-radius:8px; padding:14px 18px; margin:16px 0;
                         font-size:0.9rem; color:#333; }}
            .footer {{ background:#0f1f3d; padding:20px 40px; text-align:center;
                       color:rgba(248,244,237,0.45); font-size:0.75rem; }}
        </style>
        </head>
        <body>
        <div class="wrap">
            <div class="header">
                <h1>✦ BeautyFlow</h1>
                <p>Premium Beauty Studio · Warszawa</p>
            </div>
            <div class="body">
                {body_html}
            </div>
            <div class="footer">
                ul. Złota 12, Warszawa · +48 500 123 456 · hello@beautyflow.pl<br>
                Pon–Pt 9:00–20:00 · Sobota 9:00–16:00
            </div>
        </div>
        </body>
        </html>
        """

    # ── Email do KLIENTKI ─────────────────────
    if client_email:
        body_client = f"""
        <h2>Dziękujemy za konsultację, {imie}! 🌸</h2>
        <p>Oto podsumowanie Twojej rozmowy z Sofią z dnia <strong>{teraz}</strong>.</p>

        <div class="pill">{proc_data.get('emoji','✨')} {procedure}</div>

        <div class="info-box">
            <strong>Podsumowanie konsultacji:</strong><br>{podsumowanie}
        </div>

        <div class="info-box">
            ⏱ Czas zabiegu: <strong>{proc_data.get('time','–')}</strong><br>
            💰 Cena: <strong>{proc_data.get('price','–')}</strong><br>
            📋 Przygotowanie: <strong>{proc_data.get('prep','–')}</strong>
        </div>

        <p>Nasza specjalistka skontaktuje się z Tobą wkrótce w celu ustalenia terminu wizyty.</p>
        <p>Do zobaczenia w salonie! 💛</p>
        <p style="color:#999;font-size:0.85rem;">— Zespół BeautyFlow</p>
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"✦ BeautyFlow – podsumowanie konsultacji: {procedure}"
            msg["From"] = f"BeautyFlow AI <{gmail_user}>"
            msg["To"] = client_email
            msg.attach(MIMEText(make_html("Podsumowanie konsultacji", body_client), "html", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_pass)
                server.sendmail(gmail_user, client_email, msg.as_string())
            results["client"] = True
        except Exception as e:
            results["client_error"] = str(e)

    # ── Email do WŁAŚCICIELKI ─────────────────
    telefon = client_info.get("telefon", "–")
    body_owner = f"""
    <h2>🔔 Nowa konsultacja AI</h2>
    <p>Data: <strong>{teraz}</strong></p>

    <div class="pill">{proc_data.get('emoji','✨')} {procedure}</div>

    <div class="info-box">
        👤 Imię: <strong>{imie}</strong><br>
        📧 Email: <strong>{client_email or '–'}</strong><br>
        📞 Telefon: <strong>{telefon}</strong>
    </div>

    <div class="info-box">
        <strong>Podsumowanie rozmowy przez AI:</strong><br>
        {podsumowanie}
    </div>

    <p style="color:#999;font-size:0.85rem;">
        Wiadomość wygenerowana automatycznie przez system BeautyFlow AI.
    </p>
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🌸 BeautyFlow – nowa konsultacja: {imie} ({procedure})"
        msg["From"] = f"BeautyFlow AI <{gmail_user}>"
        msg["To"] = owner_email
        msg.attach(MIMEText(make_html("Nowa konsultacja", body_owner), "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, owner_email, msg.as_string())
        results["owner"] = True
    except Exception as e:
        results["owner_error"] = str(e)

    return results


def send_booking_status_email(booking: dict, confirmed: bool) -> bool:
    """
    Wysyła klientce email z potwierdzeniem lub odrzuceniem rezerwacji.
    Wywoływana przez właścicielkę z panelu po kliknięciu Potwierdź / Odrzuć.
    """
    client_email = booking.get("email", "")
    if not client_email or "@" not in client_email:
        return False  # brak emaila klientki – nic nie wysyłamy

    try:
        gmail_user = st.secrets["email"]["gmail_user"]
        gmail_pass = st.secrets["email"]["gmail_password"]
    except Exception:
        return False

    imie      = booking.get("imie", "Klientko")
    termin    = booking.get("termin", "–")
    zabieg    = booking.get("zabieg", "–")
    proc_data = PROCEDURES.get(zabieg, {})

    if confirmed:
        subject = f"✅ BeautyFlow – Twoja rezerwacja potwierdzona!"
        body = f"""
        <h2>Twoja rezerwacja jest potwierdzona, {imie}! 🎉</h2>
        <p>Cieszymy się, że wkrótce Cię zobaczymy w BeautyFlow.</p>

        <div class="pill">{proc_data.get('emoji','✨')} {zabieg}</div>

        <div class="info-box" style="border-left-color:#4caf50;">
            📅 <strong>Termin:</strong> {termin}<br>
            ⏱ <strong>Czas zabiegu:</strong> {proc_data.get('time','–')}<br>
            📍 <strong>Adres:</strong> ul. Złota 12, Warszawa
        </div>

        <div class="info-box">
            📋 <strong>Przygotowanie do zabiegu:</strong><br>
            {proc_data.get('prep','–')}
        </div>

        <p>W razie pytań zadzwoń: <strong>+48 500 123 456</strong> lub napisz na <strong>hello@beautyflow.pl</strong></p>
        <p>Do zobaczenia! 💛</p>
        <p style="color:#999;font-size:0.85rem;">— Zespół BeautyFlow</p>
        """
    else:
        subject = f"BeautyFlow – informacja o Twojej rezerwacji"
        body = f"""
        <h2>Informacja o rezerwacji, {imie}</h2>
        <p>Niestety musisz wiedzieć, że wybrany przez Ciebie termin nie jest już dostępny.</p>

        <div class="pill">{proc_data.get('emoji','✨')} {zabieg}</div>

        <div class="info-box" style="border-left-color:#e57373;">
            📅 <strong>Termin:</strong> {termin}<br>
            ℹ️ <strong>Status:</strong> niedostępny
        </div>

        <p>Zapraszamy do ponownego umówienia się – skontaktuj się z nami:</p>
        <p>📞 <strong>+48 500 123 456</strong><br>✉️ <strong>hello@beautyflow.pl</strong></p>
        <p>Przepraszamy za niedogodności i mamy nadzieję zobaczyć Cię wkrótce! 🌸</p>
        <p style="color:#999;font-size:0.85rem;">— Zespół BeautyFlow</p>
        """

    try:
        # Używamy tego samego make_html co w send_emails – budujemy go inline
        html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
        <style>
            body {{ font-family: 'Georgia', serif; background:#f8f4ed; margin:0; padding:0; }}
            .wrap {{ max-width:560px; margin:40px auto; background:#fff; border-radius:16px;
                     overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
            .header {{ background:#0f1f3d; padding:32px 40px; text-align:center; }}
            .header h1 {{ color:#f5d776; font-size:1.6rem; margin:0; letter-spacing:0.08em; }}
            .header p  {{ color:rgba(248,244,237,0.6); font-size:0.75rem;
                          letter-spacing:0.25em; text-transform:uppercase; margin:6px 0 0; }}
            .body {{ padding:32px 40px; color:#1a1a2e; line-height:1.7; }}
            .pill {{ display:inline-block; background:#f5d776; color:#0f1f3d;
                     border-radius:20px; padding:4px 14px; font-size:0.8rem;
                     font-weight:600; margin-bottom:1rem; }}
            .info-box {{ background:#f8f4ed; border-left:3px solid #f5d776;
                         border-radius:8px; padding:14px 18px; margin:16px 0;
                         font-size:0.9rem; color:#333; }}
            .footer {{ background:#0f1f3d; padding:20px 40px; text-align:center;
                       color:rgba(248,244,237,0.45); font-size:0.75rem; }}
        </style></head><body>
        <div class="wrap">
            <div class="header"><h1>✦ BeautyFlow</h1>
            <p>Premium Beauty Studio · Warszawa</p></div>
            <div class="body">{body}</div>
            <div class="footer">
                ul. Złota 12, Warszawa · +48 500 123 456 · hello@beautyflow.pl<br>
                Pon–Pt 9:00–20:00 · Sobota 9:00–16:00
            </div>
        </div></body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"BeautyFlow AI <{gmail_user}>"
        msg["To"]      = client_email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, client_email, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"Błąd wysyłki emaila do klientki: {e}")
        return False

# ─────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_sheets_client():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def get_or_create_ws(spreadsheet, name: str, headers: list):
    """Pobiera arkusz lub tworzy go z nagłówkami."""
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        ws.format(f"A1:{chr(64+len(headers))}1", {"textFormat": {"bold": True}})
    return ws


def get_spreadsheet():
    gc = get_sheets_client()
    if not gc:
        return None
    try:
        return gc.open_by_key(st.secrets["sheets"]["sheet_id"])
    except Exception:
        return None


def save_to_sheet(procedure: str, client_info: dict, messages: list) -> bool:
    """Zapisuje konsultację do arkusza Konsultacje."""
    try:
        sp = get_spreadsheet()
        if not sp:
            return False
        ws = get_or_create_ws(sp, "Konsultacje", [
            "Data", "Imię", "Email", "Telefon", "Zabieg",
            "Termin", "Wiadomości", "Podsumowanie AI", "Status"
        ])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            client_info.get("imie", "–"),
            client_info.get("email", "–"),
            client_info.get("telefon", "–"),
            procedure,
            client_info.get("termin", "–"),
            len(messages),
            client_info.get("podsumowanie", "–"),
            "oczekuje na potwierdzenie" if client_info.get("termin") else "bez terminu",
        ])
        return True
    except Exception as e:
        st.error(f"Błąd Sheets (konsultacje): {e}")
        return False


# ── TERMINY ──────────────────────────────────

def load_slots_from_sheet():
    """Wczytuje wolne terminy z arkusza Terminy."""
    try:
        sp = get_spreadsheet()
        if not sp:
            return [], []
        ws_t = get_or_create_ws(sp, "Terminy", ["Termin", "Status"])
        ws_r = get_or_create_ws(sp, "Rezerwacje", [
            "Data zgłoszenia", "Termin", "Imię", "Email", "Telefon", "Zabieg", "Status"
        ])

        # Wczytaj terminy
        slots = []
        rows_t = ws_t.get_all_records()
        for r in rows_t:
            if r.get("Termin"):
                slots.append({
                    "termin": r["Termin"],
                    "zajety": r.get("Status", "wolny") == "zajęty"
                })

        # Wczytaj rezerwacje oczekujące
        pending = []
        rows_r = ws_r.get_all_records()
        for r in rows_r:
            if r.get("Status") == "oczekuje":
                pending.append({
                    "imie":    r.get("Imię", "?"),
                    "email":   r.get("Email", "-"),
                    "telefon": r.get("Telefon", "-"),
                    "zabieg":  r.get("Zabieg", "-"),
                    "termin":  r.get("Termin", "-"),
                })
        return slots, pending
    except Exception as e:
        return [], []


def save_slot_to_sheet(termin: str, status: str = "wolny"):
    """Dodaje lub aktualizuje termin w arkuszu Terminy."""
    try:
        sp = get_spreadsheet()
        if not sp:
            return False
        ws = get_or_create_ws(sp, "Terminy", ["Termin", "Status"])
        # Sprawdź czy termin już istnieje
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Termin") == termin:
                ws.update(f"B{i}", [[status]])
                return True
        # Nowy termin
        ws.append_row([termin, status])
        return True
    except Exception as e:
        return False


def save_pending_to_sheet(booking: dict):
    """Zapisuje rezerwację oczekującą do arkusza Rezerwacje."""
    try:
        sp = get_spreadsheet()
        if not sp:
            return False
        ws = get_or_create_ws(sp, "Rezerwacje", [
            "Data zgłoszenia", "Termin", "Imię", "Email", "Telefon", "Zabieg", "Status"
        ])
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            booking.get("termin", "-"),
            booking.get("imie", "-"),
            booking.get("email", "-"),
            booking.get("telefon", "-"),
            booking.get("zabieg", "-"),
            "oczekuje",
        ])
        return True
    except Exception as e:
        return False


def update_booking_status(termin: str, imie: str, new_status: str):
    """Zmienia status rezerwacji w arkuszu Rezerwacje."""
    try:
        sp = get_spreadsheet()
        if not sp:
            return
        ws = sp.worksheet("Rezerwacje")
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if r.get("Termin") == termin and r.get("Imię") == imie and r.get("Status") == "oczekuje":
                ws.update(f"G{i}", [[new_status]])
                return
    except Exception:
        pass

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.2rem 0 0.6rem;text-align:center;">
            <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;color:#f5d776;">BeautyFlow</div>
            <div style="font-size:0.6rem;letter-spacing:0.28em;color:rgba(248,244,237,0.4);text-transform:uppercase;margin-top:2px;">Premium Beauty Studio</div>
        </div>
        <div style="height:1px;background:rgba(245,215,118,0.15);margin-bottom:1rem;"></div>
        """, unsafe_allow_html=True)

        st.markdown("**📍 ul. Złota 12, Warszawa**")
        st.markdown("📞 +48 500 123 456  \n✉️ hello@beautyflow.pl  \n🕐 Pon–Pt 9–20 · Sob 9–16")

        st.markdown("---")
        st.markdown("### 🎁 Promocje")
        for p in PROMOTIONS:
            st.markdown(f'<div class="promo-pill">{p}</div>', unsafe_allow_html=True)

        st.markdown("---")
        render_owner_panel()

        st.markdown("---")
        groq_ok = "app" in st.secrets and "groq_api_key" in st.secrets.get("app", {})
        sheets_ok = "gcp_service_account" in st.secrets
        email_ok = "email" in st.secrets
        st.markdown(
            f"{'🟢' if groq_ok else '🔴'} Groq API  \n"
            f"{'🟢' if sheets_ok else '🔴'} Google Sheets  \n"
            f"{'🟢' if email_ok else '🔴'} Email (Gmail)"
        )


def render_owner_panel():
    st.markdown("### 🔐 Panel właścicielki")
    if "owner_auth" not in st.session_state:
        st.session_state.owner_auth = False

    if not st.session_state.owner_auth:
        pw = st.text_input("Hasło:", type="password", key="opw",
                           label_visibility="collapsed", placeholder="Wpisz hasło...")
        if st.button("Zaloguj się", key="ologin"):
            try:
                correct = st.secrets["app"]["owner_password"]
            except Exception:
                correct = "admin"
            if pw == correct:
                st.session_state.owner_auth = True
                # Wczytaj terminy i rezerwacje z Sheets przy logowaniu
                slots, pending = load_slots_from_sheet()
                st.session_state.available_slots = slots
                st.session_state.pending_bookings = pending
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło")
    else:
        st.success("✓ Zalogowano")

        # ── DOSTĘPNE TERMINY ──────────────────────
        st.markdown("**📅 Wolne terminy do rezerwacji:**")
        slot = st.text_input("", key="nslot",
                             placeholder="np. 20.06.2025 godz. 14:00",
                             label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ Dodaj", key="addslot") and slot.strip():
                new_slot = {"termin": slot.strip(), "zajety": False}
                st.session_state.available_slots.append(new_slot)
                save_slot_to_sheet(slot.strip(), "wolny")  # zapis do Sheets
                st.rerun()
        with c2:
            if st.button("🗑 Wyczyść wolne", key="clrslot"):
                # Usuń tylko wolne (zachowaj zajęte)
                st.session_state.available_slots = [
                    s for s in st.session_state.available_slots if s["zajety"]
                ]
                # Zapisz stan do Sheets
                sp = get_spreadsheet()
                if sp:
                    try:
                        ws = sp.worksheet("Terminy")
                        rows = ws.get_all_records()
                        for i, r in enumerate(rows, start=2):
                            if r.get("Status") == "wolny":
                                ws.delete_rows(i)
                    except Exception:
                        pass
                st.rerun()

        for s in st.session_state.get("available_slots", []):
            ikona = "🔴" if s["zajety"] else "🟢"
            status = " *(zarezerwowany)*" if s["zajety"] else ""
            st.markdown(f"{ikona} {s['termin']}{status}")

        # ── REZERWACJE DO POTWIERDZENIA ───────────
        pending = st.session_state.get("pending_bookings", [])
        if pending:
            st.markdown("---")
            st.markdown(f"**🔔 Do potwierdzenia ({len(pending)}):**")
            for i, b in enumerate(pending):
                st.markdown(
                    f"👤 **{b.get('imie','?')}** · {b.get('zabieg','?')}  \n"
                    f"📅 {b.get('termin','?')}  \n"
                    f"📧 {b.get('email','-')} · 📞 {b.get('telefon','-')}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Potwierdź", key=f"confirm_{i}"):
                        save_slot_to_sheet(b.get("termin",""), "zajęty")
                        update_booking_status(b.get("termin",""), b.get("imie",""), "potwierdzona")
                        for s in st.session_state.available_slots:
                            if s["termin"] == b.get("termin"):
                                s["zajety"] = True
                        st.session_state.pending_bookings.pop(i)
                        # Wyślij email do klientki
                        sent = send_booking_status_email(b, confirmed=True)
                        if sent:
                            st.success(f"✅ Potwierdzono! Email wysłany do {b.get('email','-')}")
                        else:
                            st.success("✅ Potwierdzono!")
                            if b.get("email"):
                                st.warning("⚠️ Nie udało się wysłać emaila do klientki")
                        st.rerun()
                with col2:
                    if st.button("❌ Odrzuć", key=f"reject_{i}"):
                        save_slot_to_sheet(b.get("termin",""), "wolny")
                        update_booking_status(b.get("termin",""), b.get("imie",""), "odrzucona")
                        for s in st.session_state.available_slots:
                            if s["termin"] == b.get("termin"):
                                s["zajety"] = False
                        st.session_state.pending_bookings.pop(i)
                        # Wyślij email do klientki
                        sent = send_booking_status_email(b, confirmed=False)
                        if sent:
                            st.info(f"📧 Klientka ({b.get('email','-')}) poinformowana o odrzuceniu")
                        elif b.get("email"):
                            st.warning("⚠️ Nie udało się wysłać emaila do klientki")
                        st.rerun()

        if st.button("🔄 Odśwież z arkusza", key="refresh_slots"):
            slots, pending = load_slots_from_sheet()
            st.session_state.available_slots = slots
            st.session_state.pending_bookings = pending
            st.rerun()

        if st.button("Wyloguj", key="ologout"):
            st.session_state.owner_auth = False
            st.rerun()

# ─────────────────────────────────────────────
# WYBÓR ZABIEGU
# ─────────────────────────────────────────────
def render_procedure_picker():
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.25rem;color:#f5d776;margin-bottom:0.3rem;">
            Na co chcesz się umówić?
        </div>
        <div style="font-size:0.85rem;color:rgba(248,244,237,0.5);">
            Wybierz zabieg – Sofia przeprowadzi Cię przez krótką konsultację i wyśle podsumowanie na email.
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, (name, p) in enumerate(PROCEDURES.items()):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="proc-card">
                <div>
                    <span class="card-emoji">{p['emoji']}</span>
                    <span class="card-title">{name}</span>
                </div>
                <div class="card-tag">{p['tagline']}</div>
                <div class="card-meta">⏱ {p['time']} &nbsp;·&nbsp; 💰 {p['price']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Wybieram →", key=f"pick_{name}", use_container_width=True):
                st.session_state.chosen_procedure = name
                st.session_state.chat_stage = "chat"
                intro = ask_groq(
                    messages=[{"role": "user", "content": f"Chcę się dowiedzieć o {name}"}],
                    system=KNOWLEDGE_BASE + f"\nKlientka wybrała: {name}. Przywitaj się ciepło, powiedz 1-2 zdania o zabiegu i zacznij pierwsze pytanie kwalifikujące."
                )
                st.session_state.messages = [{"role": "assistant", "content": intro}]
                st.session_state.saved = False
                st.rerun()

# ─────────────────────────────────────────────
# CZAT
# ─────────────────────────────────────────────
def render_chat():
    procedure = st.session_state.get("chosen_procedure", "")
    messages  = st.session_state.get("messages", [])
    saved     = st.session_state.get("saved", False)
    p         = PROCEDURES.get(procedure, {})

    # ── Nagłówek ──────────────────────────────
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;">
        <span style="font-size:1.5rem;">{p.get('emoji','✨')}</span>
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:#f5d776;">{procedure}</div>
            <div style="font-size:0.75rem;color:rgba(248,244,237,0.45);">{p.get('tagline','')}</div>
        </div>
        <div style="margin-left:auto;font-size:0.72rem;color:rgba(248,244,237,0.35);">Sofia AI</div>
    </div>
    <div style="height:1px;background:rgba(245,215,118,0.1);margin-bottom:1rem;"></div>
    """, unsafe_allow_html=True)

    # ── Historia czatu ─────────────────────────
    for msg in messages:
        if msg.get("hidden"):   # ukryte wiadomości systemowe
            continue
        avatar = "🌸" if msg["role"] == "assistant" else "👤"
        # Jeśli Sofia zwróciła SHOW_SLOTS – pokaż komunikat zamiast kodu
        display_content = msg["content"]
        if display_content.strip() == "SHOW_SLOTS":
            display_content = "Świetnie! Oto dostępne terminy – proszę wybrać jeden:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(display_content)

    # ── Przyciski terminów ─────────────────────
    # Pokazujemy gdy Sofia powiedziała SHOW_SLOTS i termin jeszcze nie wybrany
    show_slots = (
        not saved
        and not st.session_state.get("slot_chosen")
        and any(m["content"].strip() == "SHOW_SLOTS" for m in messages if m["role"] == "assistant")
    )
    available = [s for s in st.session_state.get("available_slots", []) if not s["zajety"]]

    if show_slots:
        if available:
            st.markdown(
                '<div style="background:rgba(245,215,118,0.1);border:1px solid '
                'rgba(245,215,118,0.3);border-radius:12px;padding:14px 18px;margin:8px 0;">'
                '<span style="color:#f5d776;font-weight:500;">📅 Wybierz termin:</span></div>',
                unsafe_allow_html=True
            )
            cols = st.columns(min(len(available), 3))
            for i, s in enumerate(available):
                with cols[i % 3]:
                    if st.button(f"🟢 {s['termin']}", key=f"slot_{i}", use_container_width=True):
                        # Oznacz termin tymczasowo
                        s["zajety"] = True
                        st.session_state.slot_chosen = s["termin"]
                        # Dodaj wybór jako wiadomość użytkownika
                        messages.append({"role": "user", "content": f"Wybieram termin: {s['termin']}"})
                        # Sofia potwierdza i prosi o email
                        reply = ask_groq(
                            messages=messages,
                            system=KNOWLEDGE_BASE + (
                                f"\nKlientka wybrała termin {s['termin']}. "
                                "Potwierdź ciepło wybór. Poproś o imię i email jeśli jeszcze nie podała "
                                "(piszemy podsumowanie na skrzynkę). Poinformuj że właścicielka potwierdzi termin emailem."
                            )
                        )
                        messages.append({"role": "assistant", "content": reply})
                        st.session_state.messages = messages
                        st.rerun()
        else:
            st.info("ℹ️ Brak dostępnych terminów – właścicielka doda je wkrótce. Możemy zapisać Twoje dane i oddzwonimy.")

    # ── Przycisk zapisz + wyślij (po wyborze terminu lub po dłuższej rozmowie) ─
    can_save = (
        not saved and len(messages) >= 5
        and (st.session_state.get("slot_chosen") or len(messages) >= 8)
    )
    if can_save:
        st.markdown("")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📩 Zapisz i wyślij podsumowanie", use_container_width=True, key="save_btn"):
                with st.spinner("Sofia przygotowuje podsumowanie..."):
                    info = extract_client_info(messages)
                    if st.session_state.get("slot_chosen"):
                        info["termin"] = st.session_state.slot_chosen

                # Rezerwacja pending → Sheets
                if st.session_state.get("slot_chosen"):
                    booking = {
                        "imie":    info.get("imie", "?"),
                        "email":   info.get("email", "-"),
                        "telefon": info.get("telefon", "-"),
                        "zabieg":  procedure,
                        "termin":  st.session_state.slot_chosen,
                    }
                    if "pending_bookings" not in st.session_state:
                        st.session_state.pending_bookings = []
                    st.session_state.pending_bookings.append(booking)
                    save_pending_to_sheet(booking)
                    save_slot_to_sheet(st.session_state.slot_chosen, "zarezerwowany")

                sheet_ok      = save_to_sheet(procedure, info, messages)
                email_results = send_emails(procedure, info, messages)
                client_email  = info.get("email", "")

                if sheet_ok:
                    st.success("✅ Zapisano w Google Sheets")
                else:
                    st.warning("⚠️ Błąd zapisu do arkusza")

                if email_results.get("owner"):
                    st.success("📧 Powiadomienie wysłane do właścicielki")
                else:
                    st.warning(f"⚠️ Email do właścicielki: {email_results.get('owner_error','błąd')}")

                if client_email:
                    if email_results.get("client"):
                        st.success(f"📧 Podsumowanie wysłane na {client_email}")
                    else:
                        st.warning(f"⚠️ Email do klientki: {email_results.get('client_error','błąd')}")
                else:
                    st.info("ℹ️ Klientka nie podała emaila")

                if st.session_state.get("slot_chosen"):
                    st.info(f"🔔 Rezerwacja **{st.session_state.slot_chosen}** czeka na potwierdzenie właścicielki")

                st.session_state.saved = True
                st.rerun()

    # ── Zakończono ─────────────────────────────
    if saved:
        st.success("✅ Konsultacja zakończona i zapisana")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Nowa konsultacja", use_container_width=True, key="new_btn"):
                st.session_state.messages       = []
                st.session_state.saved          = False
                st.session_state.slot_chosen    = None
                st.session_state.chat_stage     = "pick"
                st.session_state.chosen_procedure = ""
                st.rerun()

    # ── Input klientki ─────────────────────────
    if not saved and not show_slots:
        if prompt := st.chat_input("Napisz do Sofii..."):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🌸"):
                with st.spinner("Sofia pisze..."):
                    reply = ask_groq(
                        messages=messages,
                        system=KNOWLEDGE_BASE + f"\nAktualnie omawiany zabieg: {procedure}"
                    )
                # Zamień SHOW_SLOTS na ładny tekst w UI
                display = "Świetnie! Oto dostępne terminy – proszę wybrać jeden:" if reply.strip() == "SHOW_SLOTS" else reply
                st.markdown(display)
            messages.append({"role": "assistant", "content": reply})
            st.session_state.messages = messages
            st.rerun()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()

    # Wczytaj terminy z Sheets przy pierwszym uruchomieniu
    if "slots_loaded" not in st.session_state:
        slots, pending = load_slots_from_sheet()
        st.session_state.available_slots = slots
        st.session_state.pending_bookings = pending
        st.session_state.slots_loaded = True

    if "chat_stage" not in st.session_state:
        st.session_state.chat_stage = "pick"
    if "chosen_procedure" not in st.session_state:
        st.session_state.chosen_procedure = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "saved" not in st.session_state:
        st.session_state.saved = False
    if "slot_chosen" not in st.session_state:
        st.session_state.slot_chosen = None

    render_sidebar()

    _, col, _ = st.columns([0.5, 5, 0.5])
    with col:
        render_logo()
        if st.session_state.chat_stage == "pick":
            render_procedure_picker()
        else:
            if st.button("← Zmień zabieg", key="back_btn"):
                st.session_state.chat_stage = "pick"
                st.session_state.messages = []
                st.session_state.saved = False
                st.session_state.chosen_procedure = ""
                st.rerun()
            render_chat()


if __name__ == "__main__":
    main()
