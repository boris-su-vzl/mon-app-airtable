import streamlit as st
import requests
import bcrypt
import time
import google.generativeai as genai

# --- Configuration de la page ---
st.set_page_config(
    page_title="Portail Membre",
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
    st.error(f"🚨 Erreur de configuration : {e}")
    st.stop()

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# --- Services IA (Gemini) ---
def get_name_compliment(prenom):
    if not GOOGLE_API_KEY: return "Clé API manquante."
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(
            f"Tu es un expert en étymologie jovial. Donne un avis court (une seule phrase), élégant et flatteur sur le prénom '{prenom}'. Pas de guillemets."
        )
        return response.text.strip()
    except Exception as e:
        return f"Note : {e}"

# --- Services Airtable ---
def fetch_user_by_email(email):
    formula = f"{{Email}} = '{email}'"
    params = {"filterByFormula": formula}
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        data = response.json()
        return data["records"][0] if "records" in data and data["records"] else None
    except: return None

def create_user(email, password, nom, prenom, telephone):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    data = {"fields": {"Email": email, "MotDePasse": hashed, "Nom": nom, "Prenom": prenom, "Telephone": telephone}}
    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=data)
        return response.json()
    except: return None

def update_user_profile(record_id, nom, prenom, telephone):
    url = f"{BASE_URL}/{record_id}"
    data = {"fields": {"Nom": nom, "Prenom": prenom, "Telephone": telephone}}
    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        return response.json()
    except: return None

def verify_password(plain_password, hashed_password_str):
    try: return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password_str.encode('utf-8'))
    except: return False

def send_slack_notification(message):
    if not SLACK_WEBHOOK_URL: return
    try: requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    except: pass

# --- Gestion de l'État ---
if 'user' not in st.session_state: st.session_state.user = None
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def logout():
    st.session_state.user = None
    st.session_state.auth_mode = 'login'
    st.rerun()

# --- Design & CSS ---
def inject_custom_css():
    st.markdown("""
        <style>
        .stApp { background-color: #f8fafc; }
        div[data-testid="stForm"] { background-color: white; padding: 2rem; border-radius: 1rem; border: 1px solid #e2e8f0; }
        h1, h2, h3 { color: #1e293b; font-family: 'Segoe UI', sans-serif; }
        .welcome-card { background: white; padding: 3rem; border-radius: 1.5rem; text-align: center; border: 1px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
        </style>
    """, unsafe_allow_html=True)

# --- Interfaces ---

def show_login():
    st.markdown("<h2 style='text-align: center;'>🔐 Connexion</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter", type="primary", use_container_width=True):
            user_record = fetch_user_by_email(email)
            if user_record and verify_password(password, user_record['fields'].get('MotDePasse', '')):
                st.session_state.user = user_record
                st.rerun()
            else: st.error("Identifiants incorrects.")
    if st.button("Créer un compte"): 
        st.session_state.auth_mode = 'register'
        st.rerun()

def show_register():
    st.markdown("<h2 style='text-align: center;'>✨ Inscription</h2>", unsafe_allow_html=True)
    with st.form("reg_form"):
        p, n = st.columns(2)
        prenom = p.text_input("Prénom")
        nom = n.text_input("Nom")
        email = st.text_input("Email")
        tel = st.text_input("Téléphone")
        pw = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("S'inscrire", type="primary"):
            new_u = create_user(email, pw, nom, prenom, tel)
            if new_u:
                st.session_state.user = new_u
                st.rerun()
    if st.button("Déjà un compte ?"): 
        st.session_state.auth_mode = 'login'
        st.rerun()

# --- NOUVELLE PAGE : ACCUEIL ---
def show_welcome():
    fields = st.session_state.user['fields']
    st.markdown(f"""
        <div class="welcome-card">
            <h1 style='font-size: 3rem; margin-bottom: 0;'>👋 Bonjour, {fields.get('Prenom')} !</h1>
            <p style='color: #64748b; font-size: 1.2rem;'>Ravi de vous revoir dans votre espace membre.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Un petit message d'accueil de l'IA dès l'arrivée
    with st.expander("✨ Un petit mot pour vous", expanded=True):
        st.write(get_name_compliment(fields.get('Prenom')))

# --- PAGE PROFIL (MODIFIÉE) ---
def show_profile_settings():
    user = st.session_state.user
    fields = user['fields']
    
    st.markdown("## ⚙️ Paramètres du profil")
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        prenom = col1.text_input("Prénom", value=fields.get("Prenom", ""))
        nom = col2.text_input("Nom", value=fields.get("Nom", ""))
        telephone = st.text_input("Téléphone", value=fields.get("Telephone", ""))
        st.text_input("Email", value=fields.get("Email", ""), disabled=True)
        
        if st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True):
            with st.spinner("Mise à jour..."):
                updated = update_user_profile(user['id'], nom, prenom, telephone)
                if updated:
                    st.session_state.user['fields'].update(updated['fields'])
                    ai_comment = get_name_compliment(prenom)
                    send_slack_notification(f"🔔 Mise à jour : {prenom} {nom}\n🤖 IA : {ai_comment}")
                    st.success("Profil mis à jour !")
                    time.sleep(1)
                    st.rerun()

# --- Main App Logic ---
def main():
    inject_custom_css()
    
    if not st.session_state.user:
        col_l, col_center, col_r = st.columns([1, 2, 1])
        with col_center:
            if st.session_state.auth_mode == 'login': show_login()
            else: show_register()
    else:
        # NAVIGATION SIDEBAR (Roue crantée incluse)
        with st.sidebar:
            st.markdown(f"### Menu")
            # Utilisation de boutons pour naviguer
            page = st.radio("Aller vers :", ["🏠 Accueil", "⚙️ Mon Profil"], label_visibility="collapsed")
            st.markdown("---")
            if st.button("🚪 Déconnexion", use_container_width=True):
                logout()

        if page == "🏠 Accueil":
            show_welcome()
        else:
            show_profile_settings()

if __name__ == "__main__":
    main()
