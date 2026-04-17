# ============================================================
# BeautyFlow AI – Asystent Kosmetyczny oparty na Grok (xAI)
# Stack: Streamlit + Grok API (openai-compatible) + gspread
# Deploy: Streamlit Cloud
# ============================================================
#
# STREAMLIT SECRETS (App Settings → Secrets):
#
# [app]
# grok_api_key      = "xai-TWÓJ_KLUCZ_GROK"
# google_sheet_id   = "ID_ARKUSZA_Z_URL"
# owner_password    = "TwojeBezpieczneHaslo"
#
# [gcp_service_account]
# type              = "service_account"
# project_id        = "beautyflow-ai"
# private_key_id    = "..."
# private_key       = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
# client_email      = "beautyflow@beautyflow-ai.iam.gserviceaccount.com"
# client_id         = "..."
# auth_uri          = "https://accounts.google.com/o/oauth2/auth"
# token_uri         = "https://oauth2.googleapis.com/token"
# ============================================================

import streamlit as st
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ─────────────────────────────────────────────
# KONFIGURACJA STRONY
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BeautyFlow AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# BAZA WIEDZY SALONU
# Grok dostaje tę bazę jako system prompt w każdym zapytaniu
# ─────────────────────────────────────────────
KNOWLEDGE_BASE = """
Jesteś Sofią – elegancką, ciepłą asystentką salonu kosmetycznego BeautyFlow w Warszawie.
Rozmawiasz WYŁĄCZNIE po polsku. Jesteś profesjonalna ale serdeczna.
Nie wymyślasz informacji spoza bazy poniżej. Jeśli pytanie wykracza poza bazę, odsyłasz do telefonu.
Zadajesz pytania kwalifikujące naturalnie – po 1-2 na raz, nie wszystkich naraz jak formularz.

=== ZABIEGI ===

1. MEZOTERAPIA IGŁOWA
   Czas: 60 min | Cena: od 350 zł | Seria: 3-6 zabiegów co 2-3 tygodnie
   Efekty: nawilżenie, redukcja zmarszczek, rozjaśnienie, poprawa owalu twarzy
   Przeciwwskazania: ciąża, karmienie, aktywna opryszczka, retinoidy lub leki rozrzedzające krew,
     choroby autoimmunologiczne, aktywne stany zapalne skóry
   Przygotowanie: unikać alkoholu 24h przed, bez kwasów 3 dni przed
   Pytania kwalifikujące: czy stosuje retinoidy/leki rozrzedzające krew, aktywne stany zapalne,
     typ skóry (nawilżenie), poprzednie doświadczenia z mezoterapią

2. LAMINACJA RZĘS
   Czas: 90 min | Cena: od 180 zł | Efekt trwa: 6-8 tygodni
   Efekty: naturalne podkręcenie, optyczne pogrubienie i wydłużenie rzęs
   Przeciwwskazania: alergia na kleje kosmetyczne, aktywne infekcje oczu, chemioterapia,
     rzęsy krótsze niż 4mm
   Przygotowanie: bez tuszu do rzęs i odżywek 24h przed
   Pytania kwalifikujące: wcześniejsze reakcje alergiczne, leki okulistyczne, naturalna długość rzęs,
     soczewki kontaktowe

3. POWIĘKSZANIE UST KWASEM HIALURONOWYM
   Czas: 45 min | Cena: od 600 zł (0.5ml), od 900 zł (1ml) | Trwałość: 9-12 miesięcy
   Efekty: większa objętość, lepszy kontur, nawilżenie, symetria
   Przeciwwskazania: ciąża, karmienie, skłonność do keloidów, choroby tkanki łącznej (toczeń, twardzina),
     aktywna opryszczka wargowa, ibuprofen/aspiryna 3 dni przed
   Przygotowanie: bez makijażu ust, unikać leków rozrzedzających krew 3 dni przed
   Pytania kwalifikujące: poprzednie wypełnienia (kiedy), skłonność do bliznowacenia,
     choroby autoimmunologiczne, oczekiwany efekt (subtelny / wyraźny / głównie kontur)

4. PEELING KAWITACYJNY
   Czas: 45 min | Cena: 150 zł
   Efekty: głęboko oczyszczona skóra, zwężone pory, wyrównana cera
   Polecany dla: cery tłustej, mieszanej, z zanieczyszczeniami; jako przygotowanie do innych zabiegów
   Przeciwwskazania: rozrusznik serca, metalowe implanty w twarzy, aktywne stany zapalne, ciąża

=== PROMOCJE ===
- Pakiet 3x Mezoterapia: 900 zł (oszczędzasz 150 zł)
- Laminacja rzęs + Peeling kawitacyjny: 300 zł
- Nowe klientki: 10% zniżki na pierwszą wizytę

=== KONTAKT I GODZINY ===
Adres: ul. Złota 12, Warszawa (Centrum, blisko metra Świętokrzyska)
Tel: +48 500 123 456
Email: hello@beautyflow.pl
Godziny: Poniedziałek–Piątek 9:00–20:00, Sobota 9:00–16:00

=== INSTRUKCJA PROWADZENIA ROZMOWY ===
1. Jeśli nie znasz imienia klientki, zapytaj na początku.
2. Zapytaj co ją interesuje lub z czym możesz pomóc.
3. Przy konkretnym zabiegu – zadawaj pytania kwalifikujące stopniowo (1-2 naraz).
4. Jeśli pojawia się przeciwwskazanie – delikatnie to zaznacz i zasugeruj konsultację ze specjalistką.
5. Gdy klientka jest gotowa do umówienia – poinformuj że możesz przekazać jej dane do specjalistki
   i że zostanie ona oddzwoniona w celu ustalenia terminu.
6. Bądź ciepła, naturalna, nie używaj formalnego żargonu medycznego.
"""

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
        st.error(f"Błąd Grok API: {e}")
        return None


def ask_grok(history: list) -> str:
    """Wysyła historię rozmowy do Grok i zwraca odpowiedź Sofii."""
    client = get_grok_client()
    if not client:
        return "Przepraszam, wystąpił problem z połączeniem. Proszę zadzwonić na +48 500 123 456."
    try:
        response = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "system", "content": KNOWLEDGE_BASE}] + history,
            max_tokens=600,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Przepraszam, wystąpił błąd: {e}. Proszę spróbować ponownie."


def extract_booking_info(messages: list) -> tuple:
    """Wyciąga imię i zabieg z historii rozmowy przez Groka."""
    client = get_grok_client()
    if not client:
        return "nieznane", "nieustalony"
    try:
        history_text = "\n".join(
            [f"{m['role'].upper()}: {m['content'][:100]}" for m in messages[-8:]]
        )
        resp = client.chat.completions.create(
            model="grok-3-latest",
            messages=[{"role": "user", "content": (
                f"Z tej rozmowy wyciągnij imię klientki i zabieg który ją interesuje.\n"
                f"Odpowiedz TYLKO w formacie: IMIĘ: xxx | ZABIEG: xxx\n\n{history_text}"
            )}],
            max_tokens=50,
            temperature=0,
        )
        text = resp.choices[0].message.content
        imie = text.split("IMIĘ:")[1].split("|")[0].strip() if "IMIĘ:" in text else "nieznane"
        zabieg = text.split("ZABIEG:")[1].strip() if "ZABIEG:" in text else "nieustalony"
        return imie, zabieg
    except Exception:
        return "nieznane", "nieustalony"

# ─────────────────────────────────────────────
# GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_gsheet_client():
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
        st.warning(f"Google Sheets niedostępne: {e}")
        return None


def save_to_sheet(client_name: str, procedure: str, messages: list) -> bool:
    """Zapisuje konsultację do arkusza Google Sheets."""
    try:
        gc = get_gsheet_client()
        if not gc:
            return False

        spreadsheet = gc.open_by_key(st.secrets["app"]["google_sheet_id"])

        try:
            ws = spreadsheet.worksheet("Konsultacje AI")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet("Konsultacje AI", rows=1000, cols=8)
            ws.append_row([
                "Timestamp", "Imię klientki", "Zabieg",
                "Liczba wiadomości", "Fragment rozmowy"
            ])

        # Zbierz fragment rozmowy (ostatnie 4 wymiany)
        fragment = " || ".join([
            f"{m['role']}: {m['content'][:120]}"
            for m in messages[-8:]
        ])

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            client_name,
            procedure,
            len(messages),
            fragment[:800],
        ])
        return True
    except Exception as e:
        st.error(f"Błąd zapisu do Sheets: {e}")
        return False

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300&family=Jost:wght@300;400;500&display=swap');
    html,body,[data-testid="stAppViewContainer"]{background:#0d0b09!important;color:#e8dcc8!important;font-family:'Jost',sans-serif!important}
    [data-testid="stSidebar"]{background:#13100c!important;border-right:1px solid #c9a84c22!important}
    [data-testid="stSidebar"] *{color:#e8dcc8!important}
    h1,h2,h3{font-family:'Cormorant Garamond',serif!important;color:#c9a84c!important;letter-spacing:.05em}
    [data-testid="stChatMessage"]{background:#1a1610!important;border:1px solid #c9a84c22!important;border-radius:12px!important;margin-bottom:.4rem!important}
    [data-testid="stChatInputTextArea"]{background:#1a1610!important;color:#e8dcc8!important;border:1px solid #c9a84c44!important;border-radius:8px!important;font-family:'Jost',sans-serif!important}
    .stButton>button{background:linear-gradient(135deg,#c9a84c,#a07830)!important;color:#0d0b09!important;border:none!important;border-radius:6px!important;font-family:'Jost',sans-serif!important;font-weight:500!important;letter-spacing:.08em!important;text-transform:uppercase!important;font-size:.75rem!important}
    .stButton>button:hover{opacity:.85!important}
    .stTextInput>div>div>input{background:#1a1610!important;color:#e8dcc8!important;border:1px solid #c9a84c44!important;border-radius:6px!important}
    hr{border-color:#c9a84c22!important}
    #MainMenu,header,footer{visibility:hidden}
    ::-webkit-scrollbar{width:4px}
    ::-webkit-scrollbar-thumb{background:#c9a84c44;border-radius:2px}
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOGO
# ─────────────────────────────────────────────
def render_logo():
    st.markdown("""
    <div style="display:flex;align-items:center;gap:16px;padding:1.5rem 0 .5rem">
      <svg width="52" height="52" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="26" cy="26" r="24" stroke="#c9a84c" stroke-width="1.2" fill="none"/>
        <path d="M26 8 C34 14 38 20 26 26 C14 20 18 14 26 8Z" fill="#c9a84c" opacity=".9"/>
        <path d="M26 44 C18 38 14 32 26 26 C38 32 34 38 26 44Z" fill="#c9a84c" opacity=".6"/>
        <path d="M8 26 C14 18 20 14 26 26 C20 34 14 38 8 26Z" fill="#c9a84c" opacity=".35"/>
        <path d="M44 26 C38 34 32 38 26 26 C32 18 38 14 44 26Z" fill="#c9a84c" opacity=".2"/>
        <circle cx="26" cy="26" r="3" fill="#c9a84c"/>
      </svg>
      <div>
        <div style="font-family:'Cormorant Garamond',serif;font-size:2rem;font-weight:300;color:#c9a84c;letter-spacing:.12em;line-height:1.1">BEAUTYFLOW</div>
        <div style="font-family:'Jost',sans-serif;font-size:.62rem;letter-spacing:.35em;color:#e8dcc877;text-transform:uppercase;margin-top:2px">AI Konsultant · Sofia · Premium Beauty</div>
      </div>
    </div>
    <hr style="margin:.5rem 0 1.2rem">
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 .5rem">
          <div style="font-family:'Cormorant Garamond',serif;font-size:1.4rem;color:#c9a84c;letter-spacing:.1em">BEAUTYFLOW</div>
          <div style="font-size:.6rem;color:#e8dcc855;letter-spacing:.3em;text-transform:uppercase">Premium Beauty Studio</div>
        </div><hr>
        """, unsafe_allow_html=True)

        st.markdown("### 📍 Kontakt")
        st.markdown("**ul. Złota 12, Warszawa**  \n📞 +48 500 123 456  \n✉️ hello@beautyflow.pl  \n🕐 Pon–Pt 9–20 | Sob 9–16")

        st.markdown("---")
        st.markdown("### 💫 Dostępność")
        busy = st.session_state.get("busy_slots", [])
        for s in busy:
            st.markdown(f"🔴 {s}")
        if not busy:
            st.markdown("*Brak zablokowanych terminów*")

        st.markdown("---")
        render_owner_panel()

        st.markdown("---")
        st.markdown("### 🔌 Status")
        try:
            st.secrets["app"]["grok_api_key"]
            st.markdown("🟢 Grok API")
        except Exception:
            st.markdown("🔴 Grok API – brak klucza")
        try:
            st.secrets["gcp_service_account"]
            st.markdown("🟢 Google Sheets")
        except Exception:
            st.markdown("🔴 Google Sheets – brak kluczy")


def render_owner_panel():
    st.markdown("### 🔐 Panel właścicielki")
    if "owner_auth" not in st.session_state:
        st.session_state.owner_auth = False

    if not st.session_state.owner_auth:
        pw = st.text_input("Hasło:", type="password", key="owner_pw")
        if st.button("Zaloguj", key="owner_login"):
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
        st.success("Zalogowano ✓")
        if "busy_slots" not in st.session_state:
            st.session_state.busy_slots = []
        slot = st.text_input("Zablokuj termin:", placeholder="2025-06-20 14:00", key="new_slot")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ Dodaj", key="add_slot") and slot.strip():
                st.session_state.busy_slots.append(slot.strip())
                st.rerun()
        with c2:
            if st.button("🗑️ Wyczyść", key="clr"):
                st.session_state.busy_slots = []
                st.rerun()
        if st.button("Wyloguj", key="logout"):
            st.session_state.owner_auth = False
            st.rerun()

# ─────────────────────────────────────────────
# CZAT Z GROK AI
# ─────────────────────────────────────────────
def run_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "saved" not in st.session_state:
        st.session_state.saved = False

    # Powitanie od Sofii
    if not st.session_state.messages:
        greeting = (
            "Dzień dobry! 🌸 Jestem Sofia, Twoja asystentka w salonie BeautyFlow.\n\n"
            "Chętnie opowiem o naszych zabiegach, cenach i pomogę dobrać coś dla Twojej skóry. "
            "Jak mam się do Pani zwracać?"
        )
        st.session_state.messages.append({"role": "assistant", "content": greeting})

    # Wyświetl historię
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="✨" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # Przycisk zapisu (po co najmniej 3 wymianach)
    if len(st.session_state.messages) >= 6 and not st.session_state.saved:
        st.markdown("")
        col1, col2, col3 = st.columns([2, 2, 2])
        with col2:
            if st.button("💾 Zapisz konsultację do arkusza", use_container_width=True):
                with st.spinner("Analizuję rozmowę i zapisuję..."):
                    imie, zabieg = extract_booking_info(st.session_state.messages)
                    ok = save_to_sheet(imie, zabieg, st.session_state.messages)
                if ok:
                    st.success(f"✅ Zapisano! Klientka: **{imie}** | Zabieg: **{zabieg}**")
                    st.session_state.saved = True
                    st.rerun()
                else:
                    st.error("Błąd zapisu – sprawdź konfigurację Google Sheets w Secrets")

    if st.session_state.saved:
        st.info("✅ Konsultacja zapisana w Google Sheets")
        if st.button("🔄 Nowa konsultacja", use_container_width=False):
            st.session_state.messages = []
            st.session_state.saved = False
            st.rerun()

    # Input klientki
    if prompt := st.chat_input("Napisz do Sofii..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("Sofia pisze..."):
                reply = ask_grok(st.session_state.messages)
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    inject_css()
    render_sidebar()
    _, col, _ = st.columns([1, 4, 1])
    with col:
        render_logo()
        st.markdown(
            '<p style="color:#e8dcc877;font-size:.88rem;margin-bottom:1.5rem">'
            'Porozmawiaj z Sofią – naszą AI konsultantką. Odpowie na pytania o zabiegi, '
            'ceny i pomoże dobrać odpowiednią opcję dla Twojej skóry.</p>',
            unsafe_allow_html=True
        )
        run_chat()


if __name__ == "__main__":
    main()
