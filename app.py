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
    # La clé API Google est optionnelle pour ne pas bloquer l'app si elle manque,
    # mais l'IA ne fonctionnera pas sans elle.
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")
except FileNotFoundError:
    st.error("🚨 Erreur de configuration : Les secrets (st.secrets) ne sont pas définis.")
    st.stop()
except KeyError as e:
    st.error(f"🚨 Erreur de configuration : Clé manquante dans st.secrets : {e}")
    st.stop()

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# --- Services IA (Gemini) ---

def get_name_compliment(prenom):
    if not GOOGLE_API_KEY:
        return "Clé API manquante."
    
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # On teste avec le nom technique exact et stable
        # Si 'gemini-1.5-flash' échoue, on essaie 'models/gemini-1.5-flash'
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        response = model.generate_content(
            f"Donne un avis très court et flatteur sur le prénom '{prenom}'. Une seule phrase."
        )
        return response.text.strip()
    except Exception as e:
        # Si l'erreur 404 persiste, on va essayer le modèle 'gemini-pro' 
        # qui est le nom universel de repli
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(f"Dit du bien du prénom {prenom}")
            return response.text.strip()
        except:
            return f"Erreur technique persistante : {e}"
    
        

# --- Services Airtable & Sécurité ---

def fetch_user_by_email(email):
    """Récupère un utilisateur Airtable par son email."""
    formula = f"{{Email}} = '{email}'"
    params = {"filterByFormula": formula}
    
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "records" in data and len(data["records"]) > 0:
            return data["records"][0]
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à Airtable : {e}")
        return None

def create_user(email, password, nom, prenom, telephone):
    """Crée un nouvel utilisateur dans Airtable."""
    # Hachage du mot de passe
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_str = hashed.decode('utf-8')

    data = {
        "fields": {
            "Email": email,
            "MotDePasse": hashed_str,
            "Nom": nom,
            "Prenom": prenom,
            "Telephone": telephone
        }
    }

    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la création du compte : {e}")
        return None

def update_user_profile(record_id, nom, prenom, telephone):
    """Met à jour les informations de l'utilisateur."""
    url = f"{BASE_URL}/{record_id}"
    data = {
        "fields": {
            "Nom": nom,
            "Prenom": prenom,
            "Telephone": telephone
        }
    }
    
    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la mise à jour : {e}")
        return None

def verify_password(plain_password, hashed_password_str):
    """Vérifie le mot de passe avec bcrypt."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password_str.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def send_slack_notification(message):
    """Envoie une notification à Slack via Webhook."""
    if not SLACK_WEBHOOK_URL:
        return

    try:
        payload = {"text": message}
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification Slack: {e}")

# --- Gestion de l'État (Session) ---

if 'user' not in st.session_state:
    st.session_state.user = None
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login' ou 'register'

def switch_to_register():
    st.session_state.auth_mode = 'register'
    st.rerun()

def switch_to_login():
    st.session_state.auth_mode = 'login'
    st.rerun()

def logout():
    st.session_state.user = None
    st.session_state.auth_mode = 'login'
    st.rerun()

# --- Design & CSS ---

def inject_custom_css():
    st.markdown("""
        <style>
        /* Fond général plus doux */
        .stApp {
            background-color: #f8fafc;
        }
        
        /* Carte centrale pour les formulaires */
        div[data-testid="stForm"] {
            background-color: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid #e2e8f0;
        }

        /* Titres */
        h1, h2, h3 {
            color: #1e293b;
            font-family: 'Segoe UI', sans-serif;
        }

        /* Boutons personnalisés */
        div.stButton > button[kind="primary"] {
            background-color: #4f46e5;
            border-color: #4f46e5;
            color: white;
            border-radius: 0.5rem;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            transition: all 0.2s;
        }
        div.stButton > button[kind="primary"]:hover {
            background-color: #4338ca;
            border-color: #4338ca;
            box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3);
        }
        
        div.stButton > button[kind="secondary"] {
            background-color: white;
            color: #475569;
            border: 1px solid #cbd5e1;
            border-radius: 0.5rem;
        }
        div.stButton > button[kind="secondary"]:hover {
            background-color: #f1f5f9;
            color: #1e293b;
            border-color: #94a3b8;
        }

        /* Inputs */
        .stTextInput > div > div > input {
            border-radius: 0.5rem;
            border-color: #cbd5e1;
        }
        .stTextInput > div > div > input:focus {
            border-color: #4f46e5;
            box-shadow: 0 0 0 1px #4f46e5;
        }
        </style>
    """, unsafe_allow_html=True)

# --- Interfaces UI ---

def show_login():
    st.markdown("<h2 style='text-align: center;'>🔐 Connexion</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Heureux de vous revoir !</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="votre@email.com")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
        
        submit_button = st.form_submit_button("Se connecter", type="primary", use_container_width=True)

        if submit_button:
            if not email or not password:
                st.warning("⚠️ Veuillez remplir tous les champs.")
            else:
                with st.spinner("Connexion..."):
                    user_record = fetch_user_by_email(email)
                    
                    if user_record:
                        stored_hash = user_record['fields'].get('MotDePasse', '')
                        if verify_password(password, stored_hash):
                            st.session_state.user = user_record
                            st.toast("✅ Connexion réussie !", icon="🎉")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Mot de passe incorrect.")
                    else:
                        st.error("Aucun compte trouvé avec cet email.")

    st.markdown("---")
    col1, col2 = st.columns([2, 2])
    with col1:
        st.markdown("<div style='padding-top: 10px; color: #64748b;'>Pas encore de compte ?</div>", unsafe_allow_html=True)
    with col2:
        if st.button("Créer un compte", type="secondary", use_container_width=True):
            switch_to_register()

def show_register():
    st.markdown("<h2 style='text-align: center;'>✨ Inscription</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 2rem;'>Rejoignez notre communauté</p>", unsafe_allow_html=True)

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            prenom = st.text_input("Prénom")
        with col2:
            nom = st.text_input("Nom")
        
        email = st.text_input("Email", placeholder="votre@email.com")
        telephone = st.text_input("Téléphone", placeholder="06 12 34 56 78")
        
        col_pass1, col_pass2 = st.columns(2)
        with col_pass1:
            password = st.text_input("Mot de passe", type="password")
        with col_pass2:
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")

        submit_register = st.form_submit_button("S'inscrire", type="primary", use_container_width=True)

        if submit_register:
            if not all([email, password, confirm_password, nom, prenom]):
                st.warning("⚠️ Veuillez remplir tous les champs obligatoires.")
            elif password != confirm_password:
                st.error("❌ Les mots de passe ne correspondent pas.")
            else:
                with st.spinner("Création du compte..."):
                    # Vérifier si l'email existe déjà
                    existing_user = fetch_user_by_email(email)
                    if existing_user:
                        st.error("Cet email est déjà utilisé.")
                    else:
                        new_user = create_user(email, password, nom, prenom, telephone)
                        if new_user:
                            st.success("Compte créé avec succès ! Vous êtes connecté.")
                            st.session_state.user = new_user
                            time.sleep(1.5)
                            st.rerun()

    st.markdown("---")
    col1, col2 = st.columns([2, 2])
    with col1:
        st.markdown("<div style='padding-top: 10px; color: #64748b;'>Déjà un compte ?</div>", unsafe_allow_html=True)
    with col2:
        if st.button("Se connecter", type="secondary", use_container_width=True):
            switch_to_login()

def show_profile():
    user = st.session_state.user
    fields = user['fields']
    
    # Navbar like header
    col_logo, col_logout = st.columns([4, 1])
    with col_logo:
        st.markdown(f"### 👋 Bonjour, {fields.get('Prenom', 'Membre')}")
    with col_logout:
        if st.button("Déconnexion", type="secondary", use_container_width=True):
            logout()

    st.markdown("---")
    
    # Layout profil centré
    col_space_l, col_main, col_space_r = st.columns([1, 6, 1])
    
    with col_main:
        st.info("💡 Vous pouvez modifier vos informations ci-dessous.")
        
        with st.form("profile_form"):
            st.markdown("#### 👤 Mes Informations")
            
            col_form_1, col_form_2 = st.columns(2)
            with col_form_1:
                prenom = st.text_input("Prénom", value=fields.get("Prenom", ""))
            with col_form_2:
                nom = st.text_input("Nom", value=fields.get("Nom", ""))
                
            telephone = st.text_input("Téléphone", value=fields.get("Telephone", ""))
            
            st.markdown("#### 🔒 Identifiants")
            st.text_input("Email", value=fields.get("Email", ""), disabled=True, help="L'email ne peut pas être modifié.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit_update = st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True)
            
            if submit_update:
                with st.spinner("Mise à jour..."):
                    updated_record = update_user_profile(user['id'], nom, prenom, telephone)
                    
                    if updated_record:
                        # Mise à jour locale sécurisée
                        merged_user = st.session_state.user.copy()
                        merged_user['fields'].update(updated_record['fields'])
                        st.session_state.user = merged_user
                        
                        # --- Notification Slack avec IA ---
                        try:
                            ai_comment = get_name_compliment(prenom)
                            slack_message = f"🔔 Mise à jour : {prenom} {nom} vient de modifier ses informations.\n\n🤖 *L'avis de l'IA :* {ai_comment}"
                        except Exception:
                            # Fallback si l'IA échoue
                            slack_message = f"🔔 Mise à jour : {prenom} {nom} vient de modifier ses informations."
                            
                        send_slack_notification(slack_message)

                        st.toast("Profil mis à jour !", icon="✅")
                        time.sleep(1)
                        st.rerun()

# --- Main App Logic ---

def main():
    inject_custom_css()
    
    # Conteneur principal centré pour Login/Register
    if not st.session_state.user:
        # Utiliser des colonnes pour centrer horizontalement sur grand écran
        col_l, col_center, col_r = st.columns([1, 2, 1])
        with col_center:
            if st.session_state.auth_mode == 'login':
                show_login()
            else:
                show_register()
    else:
        # Affichage du profil (prend toute la largeur configurée)
        show_profile()

if __name__ == "__main__":
    main()
