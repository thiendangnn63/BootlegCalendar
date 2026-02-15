import json
import pathlib
import boto3
from datetime import datetime
from dateutil import tz
from google import genai
from google.genai import types
from dotenv import dotenv_values
from botocore.exceptions import ClientError


class SyllabusAnalyzer:
    def __init__(self, file, categories=None, colorId='1', user_timezone='UTC'):
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        
        api_env_paths = [os.path.join(BASE_DIR, "api.env"), '/etc/secrets/api.env']
        api_keys = []
        for path in api_env_paths:
            if os.path.exists(path):
                api_keys = list(dotenv_values(path).values())
                break
        
        if not api_keys:
            api_keys = self.get_secret()

        self.API_KEYS = api_keys
        self.MODELS = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-3-flash-preview",
            "gemini-3-pro-preview"
        ]
        self.categories = categories
        self.user_timezone = user_timezone
        self.events = self.loadFile(file, colorId)

    def get_secret(self):
        secret_name = "GEMINI_API_KEYS"
        region_name = "us-east-1"

        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            raise e

        return list(json.loads(get_secret_value_response['SecretString']).values())
    
    def loadFile(self, filepath, colorId):
        categories_str = ", ".join(self.categories) if self.categories else "All academic events"

        prompt = f"""
        Analyze the provided syllabus content.
        Do NOT output events such as: "The duration of [COURSE] is from [DATE] to [DATE]".

        Output ONLY a JSON array of Google Calendar event objects (no prose, no markdown). Each object must match this structure and use valid JSON:
        {{
            "summary": "Title of the event",
            "description": "Optional details or context",
            "location": "Venue or room" (omit this key if unknown),
            "colorId": "{colorId}",
            "start": {{
                "dateTime": "YYYY-MM-DDTHH:MM:SS" (timed) OR "date": "YYYY-MM-DD" (all-day)
            }},
            "end": {{
                "dateTime": "YYYY-MM-DDTHH:MM:SS" OR "date": "YYYY-MM-DD"
            }},
            "recurrence": [
            ],
            "reminders": {{
                "useDefault": false,
                "overrides": []
            }}
        }}

        Rules:
        1. For all-day events, set end.date to the day AFTER the event day.
        2. Infer the correct year (current or upcoming) if not explicitly present.
        3. Output ONLY the raw JSON array (no backticks, no preamble, no trailing text).
        4. Keep the "reminders" object exactly as shown for every event.
        5. Naming pattern:
            + Assignment → "ASSIGNMENT: [EVENTNAME]"
            + Exam/midterm → "EXAM: [EVENTNAME]"
            + Quiz → "QUIZ: [EVENTNAME]"
            + Project → "PROJECT DEADLINE: [EVENTNAME]"
            + Lecture/class → "LECTURE: [EVENTNAME]"
        6. Recurrence:
            + If not recurring, omit the recurrence key entirely.
            + If recurring, include one RRULE string, e.g., "RRULE:FREQ=WEEKLY;UNTIL=YYYYMMDD".
            + Find the course end date in the syllabus (last lecture, finals week, or explicit end-of-course date) and use it for UNTIL in YYYYMMDD.
            + If no end date is found, omit recurrence entirely.
        7. Ignore ALL office hours.
        8. Only include events in these categories: {categories_str}.
        """

        for i, api_key in enumerate(self.API_KEYS):
            for model in self.MODELS:
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            types.Part.from_bytes(
                                data=pathlib.Path(filepath).read_bytes(),
                                mime_type='application/pdf',
                            ),
                            prompt
                        ]
                    )

                    if response.text:
                        raw_text = response.text.replace("```json", "").replace("```", "").strip()

                        try:
                            data = json.loads(raw_text)
                        
                            if isinstance(data, list):
                                events = self.apply_timezone(data)
                                return self.filter_past_events(events)
                            elif isinstance(data, dict) and "events" in data:
                                events = self.apply_timezone(data["events"])
                                return self.filter_past_events(events)
                        
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    pass
        return []

    def filter_past_events(self, events):
        user_tz = tz.gettz(self.user_timezone) or tz.UTC
        now = datetime.now(user_tz)
        today = now.date()
        
        future_events = []
        for event in events:
            start = event.get('start', {})
            
            if 'date' in start:
                try:
                    event_date = datetime.strptime(start['date'], "%Y-%m-%d").date()
                    if event_date >= today:
                        future_events.append(event)
                except ValueError:
                    future_events.append(event)
            
            elif 'dateTime' in start:
                try:
                    dt_str = start['dateTime']
                    if dt_str.endswith('Z'):
                        dt_str = dt_str[:-1] + '+00:00'
                    
                    event_dt = datetime.fromisoformat(dt_str)
                    
                    if event_dt.tzinfo is None:
                        event_dt = event_dt.replace(tzinfo=user_tz)

                    if event_dt >= now:
                        future_events.append(event)
                except ValueError:
                    future_events.append(event)
            else:
                 future_events.append(event)
                 
        return future_events

    def apply_timezone(self, events):
        user_tz = tz.gettz(self.user_timezone) or tz.UTC
        
        for event in events:
            for key in ['start', 'end']:
                if key in event:
                    if 'date' in event[key]:
                        continue
                        
                    if 'dateTime' in event[key]:
                        time_str = event[key]['dateTime']
                        if time_str.endswith('Z') or ('+' in time_str[-6:]) or ('-' in time_str[-6:] and time_str[-6] != 'T'):
                            continue
                        
                        try:
                            dt_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
                            dt_aware = dt_obj.replace(tzinfo=user_tz)
                            event[key]['dateTime'] = dt_aware.isoformat()
                            event[key]['timeZone'] = self.user_timezone
                        except ValueError:
                            if not time_str.endswith('Z'):
                                event[key]['dateTime'] = time_str + 'Z'
        
        return events
