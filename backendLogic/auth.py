import os
import flask
from flask import Blueprint, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

auth_bp = Blueprint('auth', __name__)

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

@auth_bp.route('/login')
def login():
    try:
        creds_path = os.path.join(os.getcwd(), 'data', 'street_creds_web.json')
        
        flow = Flow.from_client_secrets_file(
            creds_path,
            scopes=SCOPES,
            redirect_uri=url_for('auth.callback', _external=True)
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session['state'] = state
        return redirect(authorization_url)
    except FileNotFoundError:
        return "Error: data/street_creds_web.json not found. Please configure Google OAuth.", 500
    except Exception as e:
        return f"Error during login init: {str(e)}", 500

@auth_bp.route('/oauth2callback')
def callback():
    state = session.get('state')
    if not state:
        return redirect('/login')

    try:
        creds_path = os.path.join(os.getcwd(), 'data', 'street_creds_web.json')
        flow = Flow.from_client_secrets_file(
            creds_path,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('auth.callback', _external=True)
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        session['user_email'] = user_info.get('email', 'No Email Found')
        
        return redirect('/')
    except Exception as e:
        return f"Auth failed: {e}", 500

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')