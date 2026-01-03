"""
Authentication Module for LDP Dashboard
Uses streamlit-authenticator for username/password protection
"""
import streamlit as st
import streamlit_authenticator as stauth


def check_authentication():
    """
    Check if user is authenticated.
    Uses credentials from st.secrets.

    Returns:
        Tuple: (authenticated, username)
    """
    # Load credentials from secrets
    credentials = {
        'usernames': {
            st.secrets["auth"]["username"]: {
                'name': st.secrets["auth"]["name"],
                'password': st.secrets["auth"]["password_hash"]
            }
        }
    }

    # Create authenticator
    authenticator = stauth.Authenticate(
        credentials,
        st.secrets["auth"]["cookie_name"],
        st.secrets["auth"]["cookie_key"],
        cookie_expiry_days=30
    )

    # Render login form (new API in streamlit-authenticator 0.4+)
    try:
        authenticator.login(location='main')
    except Exception as e:
        st.error(f"Errore di autenticazione: {e}")
        st.stop()

    # Check authentication status via session state
    authentication_status = st.session_state.get('authentication_status')
    username = st.session_state.get('username')
    name = st.session_state.get('name')

    if authentication_status == False:
        st.error('Username/Password è incorretto')
        st.stop()
    elif authentication_status == None:
        st.warning('Inserisci username e password')
        st.info("Contatta l'amministratore per le credenziali di accesso")
        st.stop()

    # User is authenticated
    return True, username
