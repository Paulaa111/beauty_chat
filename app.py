# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny
# Stack: Streamlit + Grok (xAI) + Google Sheets
# ============================================================
#
# STREAMLIT SECRETS – wklej to w App Settings → Secrets:
#
# [app]
# grok_api_key    = "xai-TWÓJ_KLUCZ"          ← z console.x.ai
# owner_password  = "TwojeHaslo123"
#
# [sheets]
# sheet_id        = "ID_TWOJEGO_ARKUSZA"       ← z URL arkusza Google
#
# [gcp_service_account]
# type            = "service_account"
# project_id      = "beautyflow-ai"
# private_key_id  = "abc123..."
# private_key     = "-----BEGIN RSA PRIVATE KEY-----\nMII...\n-----END RSA PRIVATE KEY-----\n"
# client_email    = "beautyflow@beautyflow-ai.iam.gserviceaccount.com"
# client_id       = "123456789"
# auth_uri        = "https://accounts.google.com/o/oauth2/auth"
# token_uri       = "https://oauth2.googleapis.com/token"
#
# ──────────────────────────────────────────────────────────
# GOOGLE SHEETS – jak ustawić arkusz i powiadomienia email:
#
# 1. Utwórz nowy arkusz: nazwij go "BeautyFlow Konsultacje"
# 2. Skopiuj ID z URL: docs.google.com/spreadsheets/d/[TO_JEST_ID]/edit
# 3. Udostępnij arkusz dla client_email z uprawnieniami Edytora
# 4. POWIADOMIENIA EMAIL: w arkuszu → Narzędzia → Powiadomienia
#    → "Gdy wprowadzane są zmiany" → "Od razu" → Twój email
#    Dzięki temu Google automatycznie wyśle Ci email przy każdej nowej konsultacji!
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BeautyFlow AI",
    page_icon="✦",
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
        "emoji": "👁",
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

WAŻNE zasady prowadzenia rozmowy:
- Klientka wybrała już zabieg z listy – wiesz o co chodzi, więc nie pytaj ponownie jaki zabieg ją interesuje.
- Zadajesz pytania kwalifikujące STOPNIOWO – maksymalnie 1–2 naraz, naturalnie, jak w rozmowie.
- Jeśli pojawia się przeciwwskazanie – delikatnie to sygnalizujesz i sugerujesz konsultację ze specjalistką.
- Odpowiadasz na wszystkie pytania klientki korzystając z bazy poniżej.
- Gdy klientka jest gotowa do rezerwacji – informujesz, że specjalistka oddzwoni w celu ustalenia terminu.
- Bądź naturalna, ciepła, nie nudna.

=== BAZA ZABIEGÓW ===
{chr(10).join([
    f'''
ZABIEG: {name}
Tagline: {p["tagline"]}
Czas: {p["time"]} | Cena: {p["price"]}
Seria: {p["series"]}
Efekty: {p["effects"]}
Przeciwwskazania: {p["contraindications"]}
Przygotowanie: {p["prep"]}
Pytania kwalifikujące (zadawaj stopniowo): {" / ".join(p["questions"])}
'''
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
# CSS – GRANAT / MAŚLANY ŻÓŁTY / BIEL
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
        --white2: #ede8df;
        --muted:  rgba(248,244,237,0.55);
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--navy) !important;
        color: var(--white) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--navy2) !important;
        border-right: 1px solid rgba(245,215,118,0.15) !important;
    }
    [data-testid="stSidebar"] * { color: var(--white) !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(245,215,118,0.15) !important; }

    /* Headings */
    h1,h2,h3 {
        font-family: 'DM Serif Display', serif !important;
        color: var(--butter) !important;
        letter-spacing: 0.01em;
    }

    /* Chat bubbles */
    [data-testid="stChatMessage"] {
        background: var(--navy2) !important;
        border: 1px solid rgba(245,215,118,0.12) !important;
        border-radius: 16px !important;
        margin-bottom: 0.5rem !important;
        animation: fadeUp 0.3s ease forwards;
    }
    @keyframes fadeUp {
        from { opacity:0; transform: translateY(8px); }
        to   { opacity:1; transform: translateY(0); }
    }

    /* Chat input */
    [data-testid="stChatInputTextArea"] {
        background: var(--navy2) !important;
        color: var(--white) !important;
        border: 1px solid rgba(245,215,118,0.3) !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    [data-testid="stChatInputTextArea"]:focus {
        border-color: var(--butter) !important;
        box-shadow: 0 0 0 2px rgba(245,215,118,0.15) !important;
    }

    /* Buttons */
    .stButton > button {
        background: var(--butter) !important;
        color: var(--navy) !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        letter-spacing: 0.03em !important;
        font-size: 0.82rem !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: var(--butter2) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(245,215,118,0.25) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* Text inputs */
    .stTextInput > div > div > input {
        background: var(--navy2) !important;
        color: var(--white) !important;
        border: 1px solid rgba(245,215,118,0.25) !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--butter) !important;
    }

    /* Alerts / info */
    .stAlert {
        background: var(--navy2) !important;
        border: 1px solid rgba(245,215,118,0.2) !important;
        border-radius: 10px !important;
        color: var(--white) !important;
    }

    /* Procedure cards */
    .proc-card {
        background: var(--navy2);
        border: 1px solid rgba(245,215,118,0.15);
        border-radius: 16px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.6rem;
        cursor: pointer;
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

    /* Promo pill */
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

    /* Animated dots */
    @keyframes bounce {
        0%,80%,100% { transform:translateY(0); }
        40%          { transform:translateY(-4px); }
    }
    .dot { display:inline-block; width:6px; height:6px; border-radius:50%;
           background:var(--butter); margin:0 2px;
           animation: bounce 1.0s infinite; }
    .dot:nth-child(2){ animation-delay:.15s; }
    .dot:nth-child(3){ animation-delay:.3s; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--navy); }
    ::-webkit-scrollbar-thumb { background: rgba(245,215,118,0.3); border-radius: 2px; }

    /* Hide Streamlit chrome */
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
# GROK API
# ─────────────────────────────────────────────
@st.cache_resource
def get_grok_client():
    try:
        return OpenAI(
            api_key=st.secrets["app"]["grok_api_key"],
            base_url="https://api.x.ai/v1",
        )
    except Exception as e:
        st.error(f"❌ Brak klucza Grok API w Secrets: {e}")
        return None


def ask_grok(messages: list, system: str = None) -> str:
    client = get_grok_client()
    if not client:
        return "Przepraszam, wystąpił problem techniczny. Proszę zadzwonić: +48 500 123 456."
    try:
        sys_msg = system or KNOWLEDGE_BASE
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "system", "content": sys_msg}] + messages,
            max_tokens=600,
            temperature=0.72,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Przepraszam, błąd połączenia: {e}"


def extract_client_info(messages: list) -> dict:
    """Grok wyciąga strukturyzowane dane z rozmowy do zapisania w arkuszu."""
    client = get_grok_client()
    if not client:
        return {}
    try:
        history = "\n".join([f"{m['role'].upper()}: {m['content'][:150]}" for m in messages[-10:]])
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": (
                f"Z tej rozmowy wyciągnij dane klientki.\n"
                f"Odpowiedz TYLKO w tym formacie (bez nic więcej):\n"
                f"IMIĘ: xxx\n"
                f"TELEFON: xxx lub brak\n"
                f"UWAGI: krótkie podsumowanie max 2 zdania\n\n"
                f"Rozmowa:\n{history}"
            )}],
            max_tokens=100,
            temperature=0,
        )
        text = resp.choices[0].message.content
        result = {}
        for line in text.strip().split("\n"):
            if "IMIĘ:" in line:
                result["imie"] = line.split("IMIĘ:")[1].strip()
            elif "TELEFON:" in line:
                result["telefon"] = line.split("TELEFON:")[1].strip()
            elif "UWAGI:" in line:
                result["uwagi"] = line.split("UWAGI:")[1].strip()
        return result
    except Exception:
        return {}

# ─────────────────────────────────────────────
# GOOGLE SHEETS
# Arkusz: nazwij go "BeautyFlow Konsultacje"
# Powiadomienia: Narzędzia → Powiadomienia → "Od razu" → Twój email
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
    except Exception as e:
        return None


def save_consultation(procedure: str, messages: list, client_info: dict) -> bool:
    """
    Zapisuje konsultację do arkusza Google Sheets.
    POWIADOMIENIE EMAIL: skonfiguruj w arkuszu → Narzędzia → Powiadomienia
    """
    try:
        gc = get_sheets_client()
        if not gc:
            return False

        sheet_id = st.secrets["sheets"]["sheet_id"]
        spreadsheet = gc.open_by_key(sheet_id)

        # Znajdź lub stwórz arkusz "Konsultacje"
        try:
            ws = spreadsheet.worksheet("Konsultacje")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet("Konsultacje", rows=2000, cols=8)
            ws.append_row([
                "📅 Data i godzina",
                "👤 Imię klientki",
                "📞 Telefon",
                "💆 Wybrany zabieg",
                "💬 Liczba wiadomości",
                "📝 Uwagi AI",
                "📄 Fragment rozmowy",
            ])
            # Nagłówki pogrubione
            ws.format("A1:G1", {"textFormat": {"bold": True}})

        # Zbierz fragment rozmowy
        fragment = " ↳ ".join([
            f"[{m['role']}] {m['content'][:100]}"
            for m in messages[-6:]
        ])

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            client_info.get("imie", "nieznane"),
            client_info.get("telefon", "–"),
            procedure,
            len(messages),
            client_info.get("uwagi", "–"),
            fragment[:1000],
        ])
        return True
    except Exception as e:
        st.error(f"Błąd zapisu Sheets: {e}")
        return False

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

        # Status API
        st.markdown("---")
        grok_ok = "app" in st.secrets and "grok_api_key" in st.secrets["app"]
        sheets_ok = "gcp_service_account" in st.secrets and "sheets" in st.secrets
        st.markdown(
            f"{'🟢' if grok_ok else '🔴'} Grok API  \n"
            f"{'🟢' if sheets_ok else '🔴'} Google Sheets"
        )


def render_owner_panel():
    st.markdown("### 🔐 Panel właścicielki")
    if "owner_auth" not in st.session_state:
        st.session_state.owner_auth = False

    if not st.session_state.owner_auth:
        pw = st.text_input("Hasło:", type="password", key="opw", label_visibility="collapsed",
                           placeholder="Wpisz hasło...")
        if st.button("Zaloguj się", key="ologin"):
            try:
                correct = st.secrets["app"]["owner_password"]
            except Exception:
                correct = "admin"
            if pw == correct:
                st.session_state.owner_auth = True
                st.rerun()
            else:
                st.error("Nieprawidłowe hasło")
    else:
        st.success("✓ Zalogowano")
        if "busy_slots" not in st.session_state:
            st.session_state.busy_slots = []

        slot = st.text_input("Zablokuj termin:", key="nslot",
                             placeholder="np. 20.06 godz. 14:00",
                             label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ Dodaj", key="addslot") and slot.strip():
                st.session_state.busy_slots.append(slot.strip())
                st.rerun()
        with c2:
            if st.button("🗑 Wyczyść", key="clrslot"):
                st.session_state.busy_slots = []
                st.rerun()

        if st.session_state.busy_slots:
            st.markdown("**Zajęte terminy:**")
            for s in st.session_state.busy_slots:
                st.markdown(f"🔴 {s}")

        if st.button("Wyloguj", key="ologout"):
            st.session_state.owner_auth = False
            st.rerun()

# ─────────────────────────────────────────────
# EKRAN WYBORU ZABIEGU
# ─────────────────────────────────────────────
def render_procedure_picker():
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.25rem;color:#f5d776;margin-bottom:0.3rem;">
            Na co chcesz się umówić?
        </div>
        <div style="font-size:0.85rem;color:rgba(248,244,237,0.5);">
            Wybierz zabieg – Sofia przeprowadzi Cię przez krótką konsultację kwalifikującą.
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    items = list(PROCEDURES.items())
    for i, (name, p) in enumerate(items):
        with cols[i % 2]:
            # Karta HTML – klikalna przez button poniżej
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
            if st.button(f"Wybieram →", key=f"pick_{name}", use_container_width=True):
                st.session_state.chosen_procedure = name
                st.session_state.chat_stage = "chat"
                # Pierwsza wiadomość Sofii od razu nawiązuje do wybranego zabiegu
                intro = ask_grok(
                    messages=[{"role": "user", "content": f"Chcę się dowiedzieć o {name}"}],
                    system=KNOWLEDGE_BASE + f"\nKlientka wybrała: {name}. Przywitaj się, powiedz krótko o zabiegu i zacznij pytania kwalifikujące – 1-2 pierwsze pytania."
                )
                st.session_state.messages = [
                    {"role": "assistant", "content": intro}
                ]
                st.rerun()

# ─────────────────────────────────────────────
# CZAT
# ─────────────────────────────────────────────
def render_chat():
    procedure = st.session_state.get("chosen_procedure", "")
    messages = st.session_state.get("messages", [])
    saved = st.session_state.get("saved", False)

    # Nagłówek czatu
    p = PROCEDURES.get(procedure, {})
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;">
        <span style="font-size:1.5rem;">{p.get('emoji','✨')}</span>
        <div>
            <div style="font-family:'DM Serif Display',serif;font-size:1.1rem;color:#f5d776;">{procedure}</div>
            <div style="font-size:0.75rem;color:rgba(248,244,237,0.45);">{p.get('tagline','')}</div>
        </div>
        <div style="margin-left:auto;font-size:0.72rem;color:rgba(248,244,237,0.35);">
            Konsultantka: Sofia AI
        </div>
    </div>
    <div style="height:1px;background:rgba(245,215,118,0.1);margin-bottom:1rem;"></div>
    """, unsafe_allow_html=True)

    # Historia wiadomości
    for msg in messages:
        avatar = "✦" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Przycisk zapis + powrót (po 5+ wiadomościach)
    if len(messages) >= 5 and not saved:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("💾 Zapisz konsultację do arkusza", use_container_width=True, key="save_btn"):
                with st.spinner("Sofia analizuje rozmowę..."):
                    info = extract_client_info(messages)
                    ok = save_consultation(procedure, messages, info)
                if ok:
                    st.success(f"✅ Zapisano! Klientka: **{info.get('imie','?')}** · Zabieg: **{procedure}**")
                    st.caption("📧 Powiadomienie email wysłane automatycznie przez Google Sheets")
                    st.session_state.saved = True
                    st.rerun()
                else:
                    st.warning("⚠️ Błąd zapisu – sprawdź konfigurację Google Sheets w Secrets")

    if saved:
        st.success("✅ Konsultacja zapisana w arkuszu Google Sheets")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("← Nowa konsultacja", use_container_width=True, key="new_btn"):
                st.session_state.messages = []
                st.session_state.saved = False
                st.session_state.chat_stage = "pick"
                st.session_state.chosen_procedure = ""
                st.rerun()

    # Input klientki
    if not saved:
        if prompt := st.chat_input(f"Napisz do Sofii o {procedure.lower()}..."):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="✦"):
                with st.spinner(""):
                    st.markdown('<span class="dot"></span><span class="dot"></span><span class="dot"></span>', unsafe_allow_html=True)
                    reply = ask_grok(
                        messages=messages,
                        system=KNOWLEDGE_BASE + f"\nAktualnie omawiany zabieg: {procedure}"
                    )
                st.markdown(reply)

            messages.append({"role": "assistant", "content": reply})
            st.session_state.messages = messages
            st.rerun()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()
    render_sidebar()

    # Stan globalny
    if "chat_stage" not in st.session_state:
        st.session_state.chat_stage = "pick"
    if "chosen_procedure" not in st.session_state:
        st.session_state.chosen_procedure = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "saved" not in st.session_state:
        st.session_state.saved = False

    _, col, _ = st.columns([0.5, 5, 0.5])
    with col:
        render_logo()

        if st.session_state.chat_stage == "pick":
            render_procedure_picker()
        else:
            # Przycisk powrotu
            if st.button("← Zmień zabieg", key="back_btn"):
                st.session_state.chat_stage = "pick"
                st.session_state.messages = []
                st.session_state.saved = False
                st.session_state.chosen_procedure = ""
                st.rerun()
            render_chat()


if __name__ == "__main__":
    main()
