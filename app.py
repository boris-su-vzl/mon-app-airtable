import streamlit as st
import requests
import bcrypt
import time

# Configuration de la page
st.set_page_config(
    page_title="Portail Membre",
    page_icon="🔒",
    layout="centered"
)

# --- Gestion des Secrets ---
try:
    AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
    AIRTABLE_BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
    AIRTABLE_TABLE_NAME = st.secrets.get("AIRTABLE_TABLE_NAME", "Utilisateurs")
except FileNotFoundError:
    st.error("Erreur de configuration : Les secrets (st.secrets) ne sont pas définis.")
    st.stop()
except KeyError as e:
    st.error(f"Erreur de configuration : Clé manquante dans st.secrets : {e}")
    st.stop()

BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

# --- Fonctions Utilitaires ---

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

def verify_password(plain_password, hashed_password_str):
    """Vérifie le mot de passe avec bcrypt."""
    try:
        # bcrypt nécessite des bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password_str.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        st.error(f"Erreur lors de la vérification du mot de passe: {e}")
        return False

def update_user_profile(record_id, nom, prenom, telephone):
    """Met à jour les informations de l'utilisateur dans Airtable."""
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

# --- Gestion de la Session ---
if 'user' not in st.session_state:
    st.session_state.user = None

def logout():
    st.session_state.user = None
    st.rerun()

# --- Interfaces UI ---

def show_login():
    st.markdown("## 🔐 Connexion Membre")
    st.write("Veuillez vous identifier pour accéder à votre profil.")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="votre@email.com")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
        submit_button = st.form_submit_button("Se connecter", use_container_width=True)

        if submit_button:
            if not email or not password:
                st.warning("Veuillez remplir tous les champs.")
            else:
                with st.spinner("Vérification en cours..."):
                    user_record = fetch_user_by_email(email)
                    
                    if user_record:
                        stored_hash = user_record['fields'].get('MotDePasse', '')
                        if verify_password(password, stored_hash):
                            st.session_state.user = user_record
                            st.success("Connexion réussie !")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Mot de passe incorrect.")
                    else:
                        st.error("Email inconnu.")

def show_profile():
    user = st.session_state.user
    fields = user['fields']
    
    # Header avec bouton déconnexion
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## Bonjour, {fields.get('Prenom', 'Membre')} 👋")
    with col2:
        if st.button("Déconnexion", type="secondary", use_container_width=True):
            logout()

    st.markdown("---")
    
    st.markdown("### 📝 Mes Informations")
    
    with st.form("profile_form"):
        col_form_1, col_form_2 = st.columns(2)
        with col_form_1:
            prenom = st.text_input("Prénom", value=fields.get("Prenom", ""))
        with col_form_2:
            nom = st.text_input("Nom", value=fields.get("Nom", ""))
            
        telephone = st.text_input("Téléphone", value=fields.get("Telephone", ""))
        
        # Email en lecture seule (désactivé)
        st.text_input("Email (Non modifiable)", value=fields.get("Email", ""), disabled=True)
        
        submit_update = st.form_submit_button("💾 Enregistrer les modifications", use_container_width=True)
        
        if submit_update:
            with st.spinner("Mise à jour en cours..."):
                updated_record = update_user_profile(user['id'], nom, prenom, telephone)
                
                if updated_record:
                    # Mise à jour de la session locale avec les nouvelles données
                    # On garde les champs existants (comme le mot de passe) et on fusionne
                    st.session_state.user = updated_record
                    
                    st.success("Profil mis à jour avec succès !")
                    time.sleep(1)
                    st.rerun()

# --- Main App Logic ---

def main():
    # Petit style CSS pour nettoyer l'interface
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.user:
        show_profile()
    else:
        show_login()

if __name__ == "__main__":
    main()
