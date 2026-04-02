from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def authenticate_google():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return build('calendar', 'v3', credentials=creds)

def schedule_event(title, date, start_time, end_time, location):
    service = authenticate_google()
    event = {
        'summary': title,
        'location': location,
        'start': {'dateTime': f"{date}T{start_time}-07:00", 'timeZone': 'America/Denver'},
        'end': {'dateTime': f"{date}T{end_time}-07:00", 'timeZone': 'America/Denver'},
    }
    print(f"Creating event: {event}")
    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ Scheduled: {created_event.get('summary')} — {created_event.get('htmlLink')}"
    except HttpError as e:
        print(f"HttpError: {e.resp.status} - {e.content}")
        raise