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

    # Render login form
    name, authentication_status, username = authenticator.login('Login', 'main')

    if authentication_status == False:
        st.error('Username/Password è incorretto')
        st.stop()
    elif authentication_status == None:
        st.warning('Inserisci username e password')
        st.info("Contatta l'amministratore per le credenziali di accesso")
        st.stop()

    # User is authenticated
    return True, username
