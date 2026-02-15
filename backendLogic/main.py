import os
import tempfile
import json

from flask import Flask, request, jsonify, send_from_directory, session
from google.oauth2.credentials import Credentials
from calendarIntegration import GoogleCalendarClient
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from syllabus import SyllabusAnalyzer
from flask_cors import CORS
from auth import auth_bp
from dotenv import dotenv_values

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

flask_env_paths = [os.path.join(BASE_DIR, 'flask.env'), '/etc/secrets/flask.env']
flask_config = {}
for path in flask_env_paths:
    if os.path.exists(path):
        flask_config = dotenv_values(path)
        break

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", flask_config.get('FLASK_SECRET_KEY', "dev_unsafe_key_fallback"))
app.register_blueprint(auth_bp)

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost", "http://127.0.0.1"]
        }
    })

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=["300 per day", "100 per hour"]
)

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(BASE_DIR, path)

@app.route('/api/events', methods=['GET'])
def get_events():
    if 'credentials' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    try:
        creds = Credentials(**session['credentials'])
        calendar_bot = GoogleCalendarClient(credentials=creds)
        events = calendar_bot.fetchEvents()
        return jsonify(events if events else [])
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user', methods=['GET'])
def get_user():
    if 'credentials' not in session:
        return jsonify({"loggedIn": False})
    
    if session.get('user_email') == "Authenticated User":
        session.clear()
        return jsonify({"loggedIn": False})
        
    return jsonify({
        "loggedIn": True,
        "email": session.get('user_email')
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_syllabus():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    categories = request.form.getlist('categories')
    colorId = request.form.get('colorId', '1')

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
        file.save(temp.name)
        temp_path = temp.name

    try:
        analyzer = SyllabusAnalyzer(temp_path, categories=categories, colorId=colorId)
        events = analyzer.events
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify(events)

@app.route('/api/add-events', methods=['POST'])
def add_events():
    if 'credentials' not in session:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    events = data.get('events', [])
    
    try:
        creds = Credentials(**session['credentials'])
        calendar_bot = GoogleCalendarClient(credentials=creds)
        calendar_bot.addEvents(events)
        return jsonify({"status": "success", "count": len(events)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-event', methods=['POST'])
def update_event():
    if 'credentials' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    event = request.json
    try:
        creds = Credentials(**session['credentials'])
        calendar_bot = GoogleCalendarClient(credentials=creds)
        calendar_bot.updateEvents([event])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete-events', methods=['POST'])
def delete_events():
    if 'credentials' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.json
    event_ids = data.get('eventIds', [])
    
    try:
        creds = Credentials(**session['credentials'])
        calendar_bot = GoogleCalendarClient(credentials=creds)
        count = calendar_bot.deleteEvents(event_ids)
        return jsonify({"status": "success", "deleted_count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
