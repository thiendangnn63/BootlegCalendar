import os
import json
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

def get_flow(**kwargs):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    creds_path = os.path.join(BASE_DIR, 'data', 'street_creds_web.json')
    
    if os.path.exists(creds_path):
        return Flow.from_client_secrets_file(
            creds_path,
            scopes=SCOPES,
            **kwargs
        )
    
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        try:
            config = json.loads(creds_json)
            return Flow.from_client_config(
                config,
                scopes=SCOPES,
                **kwargs
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
            
    raise FileNotFoundError("Google credentials not found. Upload 'data/street_creds_web.json' or set 'GOOGLE_CREDENTIALS_JSON' env var.")

@auth_bp.route('/login')
def login():
    try:
        flow = get_flow(redirect_uri=url_for('auth.callback', _external=True))
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session['state'] = state
        return redirect(authorization_url)
    except FileNotFoundError as e:
        return f"Configuration Error: {str(e)}", 500
    except Exception as e:
        return f"Error during login init: {str(e)}", 500

@auth_bp.route('/oauth2callback')
def callback():
    state = session.get('state')
    if not state:
        return redirect('/login')

    try:
        flow = get_flow(
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