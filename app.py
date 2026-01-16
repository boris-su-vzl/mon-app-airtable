import streamlit as st
import requests
import bcrypt
import time
import google.generativeai as genai

# --- Configuration ---
st.set_page_config(
    page_title="Nautilus - Espace Membre",
    page_icon="🌊",
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
    if not GOOGLE_API_KEY: return "Un esprit vif dans les profondeurs."
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
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

# --- DESIGN CUSTOM CSS (NAUTILUS DARK MODE) ---
def inject_modern_design():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@200;400;600&display=swap');
        
        /* Fond Abysse */
        .stApp {
            background: radial-gradient(circle at 50% 20%, #003a61 0%, #001220 100%);
            background-attachment: fixed;
            color: #e0f2fe;
        }

        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif;
        }

        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Conteneurs Translucides */
        div[data-testid="stForm"], .welcome-card {
            background-color: rgba(0, 30, 60, 0.4);
            border: 1px solid rgba(0, 217, 255, 0.2);
            border-radius: 24px;
            padding: 40px;
            backdrop-filter: blur(15px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }

        /* Titres Lumineux */
        .welcome-title {
            font-size: 34px;
            font-weight: 200;
            letter-spacing: 6px;
            text-transform: uppercase;
            color: #00d9ff;
            text-shadow: 0 0 15px rgba(0, 217, 255, 0.4);
            margin-bottom: 20px;
        }

        /* Boutons Style Contour */
        div.stButton > button {
            border-radius: 50px;
            font-weight: 400;
            letter-spacing: 2px;
            text-transform: uppercase;
            font-size: 0.8rem;
            border: 1px solid #00d9ff !important;
            background-color: transparent !important;
            color: #00d9ff !important;
            padding: 0.5rem 2rem;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            background-color: rgba(0, 217, 255, 0.1) !important;
            box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
            transform: translateY(-2px);
        }

        /* Champs de saisie */
        .stTextInput input {
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(0, 217, 255, 0.2) !important;
            border-radius: 12px !important;
            color: white !important;
        }

        /* Labels des formulaires */
        label {
            color: rgba(0, 217, 255, 0.8) !important;
            font-weight: 200 !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }

        /* Boîte IA */
        .ai-box {
            background-color: rgba(0, 217, 255, 0.05);
            border-left: 3px solid #00d9ff;
            padding: 20px;
            border-radius: 10px;
            font-style: italic;
            color: #94e2ff;
            margin-top: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

# --- Interfaces ---

def show_login():
    st.markdown("<div style='text-align: center; margin-bottom: 10px;'><p style='color: #00d9ff; letter-spacing: 8px; font-weight: 200;'>STRIDE-UP</p></div>", unsafe_allow_html=True)
    st.markdown("<h1 class='welcome-title'>NAUTILUS</h1>", unsafe_allow_html=True)
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("S'immerger", use_container_width=True):
            u = fetch_user_by_email(e)
            if u and verify_password(p, u['fields'].get('MotDePasse', '')):
                st.session_state.user = u
                st.rerun()
            else: st.error("Coordonnées d'accès invalides")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Créer un nouveau profil"):
        st.session_state.auth_mode = 'register'
        st.rerun()

def show_welcome():
    fields = st.session_state.user['fields']
    
    c1, c2 = st.columns([8, 1])
    with c2:
        if st.button("⚙️", help="Système", key="gear"):
            st.session_state.page = 'settings'
            st.rerun()

    st.markdown(f"""
        <div class="welcome-card">
            <p style='color: #00d9ff; font-weight: 400; letter-spacing: 3px; margin-bottom: 0;'>TABLEAU DE BORD</p>
            <h1 class='welcome-title' style='text-align: left; margin-top: 10px;'>Bonjour, {fields.get('Prenom')}</h1>
            <p style='color: #94a3b8;'>Systèmes opérationnels. Bienvenue à bord.</p>
            <div class='ai-box'>
                <span style='color: #00d9ff; font-weight: 600;'>ANALYSE IA :</span><br>
                "{get_name_compliment(fields.get('Prenom'))}"
            </div>
        </div>
    """, unsafe_allow_html=True)

def show_profile_settings():
    u = st.session_state.user
    f = u['fields']
    
    c1, c2 = st.columns([8, 1])
    with c1: st.markdown("<h1 class='welcome-title' style='text-align: left;'>PARAMÈTRES</h1>", unsafe_allow_html=True)
    with c2: 
        if st.button("🏠", key="home_back"):
            st.session_state.page = 'home'
            st.rerun()

    with st.form("profile"):
        col1, col2 = st.columns(2)
        prenom = col1.text_input("Prénom", value=f.get("Prenom", ""))
        nom = col2.text_input("Nom", value=f.get("Nom", ""))
        tel = st.text_input("Contact Téléphonique", value=f.get("Telephone", ""))
        
        if st.form_submit_button("Mettre à jour les données", use_container_width=True):
            up = update_user_profile(u['id'], nom, prenom, tel)
            if up:
                st.session_state.user['fields'].update(up['fields'])
                st.toast("Base de données mise à jour", icon="🛰️")
                time.sleep(1)
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Terminer la session", use_container_width=True): logout()

# --- Main Logic ---
def main():
    inject_modern_design()
    if not st.session_state.user:
        _, center, _ = st.columns([1, 6, 1])
        with center:
            if st.session_state.auth_mode == 'login': show_login()
            else: 
                st.info("Module d'inscription en cours de déploiement...")
                if st.button("Retour à la connexion"):
                    st.session_state.auth_mode = 'login'
                    st.rerun()
    else:
        if st.session_state.page == 'home': show_welcome()
        else: show_profile_settings()

if __name__ == "__main__":
    main()
