import streamlit as st
import requests
import bcrypt
import time
import google.generativeai as genai

# --- Configuration ---
st.set_page_config(
    page_title="Espace Membre",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Gestion des Secrets ---
try:
    AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
    AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    AIRTABLE_TABLE_NAME = st.secrets.get("AIRTABLE_TABLE_NAME", "Utilisateurs")
    SLACK_WEBHOOK_URL = st.secrets.get("SLACK_WEBHOOK_URL")
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
except Exception as e:
    st.error(f"Configuration manquante : {e}")
    st.stop()

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

# --- Services IA & Airtable ---
def get_name_compliment(prenom):
    if not GOOGLE_API_KEY: return "Un prénom magnifique."
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(f"Donne un avis court, flatteur et moderne sur le prénom '{prenom}'. Une phrase.")
        return response.text.strip()
    except: return "Une personnalité rayonnante !"

def fetch_user_by_email(email):
    params = {"filterByFormula": f"{{Email}} = '{email}'"}
    r = requests.get(BASE_URL, headers=HEADERS, params=params).json()
    return r["records"][0] if "records" in r and r["records"] else None

def update_user_profile(record_id, nom, prenom, telephone):
    url = f"{BASE_URL}/{record_id}"
    data = {"fields": {"Nom": nom, "Prenom": prenom, "Telephone": telephone}}
    return requests.patch(url, headers=HEADERS, json=data).json()

def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

# --- État de la Session ---
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def logout():
    st.session_state.user = None
    st.session_state.page = 'home'
    st.rerun()

# --- DESIGN CUSTOM CSS (FLAT & MODERN) ---
def inject_modern_design():
    st.markdown("""
        <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1e293b;
        }

        .stApp {
            background-color: #fcfcfd;
        }

        /* Masquer le menu Streamlit */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}

        /* Cartes Flat */
        div[data-testid="stForm"], .welcome-card {
            background-color: #ffffff;
            border: 1px solid #f1f5f9;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }

        /* Boutons Modernes */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
            border: none;
            transition: all 0.2s ease;
        }
        
        div.stButton > button[kind="primary"] {
            background-color: #4f46e5;
            color: white;
        }
        
        div.stButton > button[kind="primary"]:hover {
            background-color: #4338ca;
            transform: translateY(-1px);
        }

        /* Inputs Flat */
        .stTextInput input {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }

        /* Message d'accueil */
        .welcome-title {
            font-size: 32px;
            font-weight: 600;
            letter-spacing: -0.5px;
            color: #0f172a;
        }
        
        .ai-box {
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            border-radius: 8px;
            font-style: italic;
        }
        </style>
    """, unsafe_allow_html=True)

# --- Interfaces ---

def show_login():
    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'><h1 class='welcome-title'>Connexion</h1></div>", unsafe_allow_html=True)
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
            u = fetch_user_by_email(e)
            if u and verify_password(p, u['fields'].get('MotDePasse', '')):
                st.session_state.user = u
                st.rerun()
            else: st.error("Identifiants incorrects")
    if st.button("Pas encore de compte ? S'inscrire"):
        st.session_state.auth_mode = 'register'
        st.rerun()

def show_welcome():
    fields = st.session_state.user['fields']
    
    # Navigation minimaliste
    c1, c2 = st.columns([8, 1])
    with c2:
        if st.button("⚙️", help="Paramètres", key="gear"):
            st.session_state.page = 'settings'
            st.rerun()

    st.markdown(f"""
        <div class="welcome-card">
            <p style='color: #6366f1; font-weight: 600; margin-bottom: 0;'>TABLEAU DE BORD</p>
            <h1 class='welcome-title'>Bonjour, {fields.get('Prenom')}</h1>
            <p style='color: #64748b;'>Heureux de vous revoir parmi nous.</p>
            <div class='ai-box'>
                ✨ {get_name_compliment(fields.get('Prenom'))}
            </div>
        </div>
    """, unsafe_allow_html=True)

def show_profile_settings():
    u = st.session_state.user
    f = u['fields']
    
    c1, c2 = st.columns([8, 1])
    with c1: st.markdown("<h1 class='welcome-title'>Paramètres</h1>", unsafe_allow_html=True)
    with c2: 
        if st.button("🏠", key="home_back"):
            st.session_state.page = 'home'
            st.rerun()

    with st.form("profile"):
        col1, col2 = st.columns(2)
        prenom = col1.text_input("Prénom", value=f.get("Prenom", ""))
        nom = col2.text_input("Nom", value=f.get("Nom", ""))
        tel = st.text_input("Téléphone", value=f.get("Telephone", ""))
        
        if st.form_submit_button("Enregistrer", type="primary", use_container_width=True):
            up = update_user_profile(u['id'], nom, prenom, tel)
            if up:
                st.session_state.user['fields'].update(up['fields'])
                st.toast("Profil mis à jour", icon="✅")
                time.sleep(1)
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Se déconnecter", use_container_width=True): logout()

# --- Main Logic ---
def main():
    inject_modern_design()
    if not st.session_state.user:
        _, center, _ = st.columns([1, 4, 1])
        with center:
            if st.session_state.auth_mode == 'login': show_login()
            else: st.info("Page d'inscription simplifiée...") # À compléter selon besoin
    else:
        if st.session_state.page == 'home': show_welcome()
        else: show_profile_settings()

if __name__ == "__main__":
    main()
