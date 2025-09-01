from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

def create_calendar_event(service_account_file, calendar_id, event_details):
    # Define the scope for Google Calendar API
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    try:
        # Authenticate using service account
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, 
            scopes=SCOPES
        )
        
        # Build the Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Create the event
        event_result = service.events().insert(
            calendarId=calendar_id,
            body=event_details
        ).execute()
        
        print(f"Event created successfully!")
        print(f"Event ID: {event_result.get('id')}")
        print(f"Event Link: {event_result.get('htmlLink')}")
        
        return event_result
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def create_sample_event():
    """
    Create a sample event with common properties.
    You can modify this function to create different types of events.
    """
    
    # Set timezone (adjust to your timezone)
    timezone = pytz.timezone('America/Sao_Paulo')  # Change this to your timezone
    
    # Calculate start and end times
    start_time = datetime.now(timezone) + timedelta(days=1, hours=2)  # Tomorrow, 2 hours from now
    end_time = start_time + timedelta(hours=1)  # 1 hour duration
    
    event = {
        'summary': 'Sample Meeting',
        'location': '123 Main St, Anytown, USA',
        'description': 'This is a sample event created via Python API',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': str(timezone),
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': str(timezone),
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                {'method': 'popup', 'minutes': 10},       # 10 minutes before
            ],
        },
        'visibility': 'default',  # 'default', 'public', 'private'
        'status': 'confirmed',    # 'tentative', 'confirmed', 'cancelled'
    }
    
    return event

def create_all_day_event():
    """
    Create an all-day event example.
    """
    
    # For all-day events, use date instead of dateTime
    tomorrow = datetime.now().date() + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)
    
    event = {
        'summary': 'All Day Event',
        'description': 'This is an all-day event',
        'start': {
            'date': tomorrow.isoformat(),
        },
        'end': {
            'date': day_after.isoformat(),
        },
        'reminders': {
            'useDefault': True,
        },
    }
    
    return event

def main():
  
    # Configuration - UPDATE THESE VALUES
    SERVICE_ACCOUNT_FILE = 'sonic-mile-455722-f9-83fc65ad543a.json'
    CALENDAR_ID = '951fdc5c8b9c0269a62f932baac88d603e9bf073b317d763f05a7347549b7228@group.calendar.google.com'
        
    print("Creating a sample timed event...")
    
    # Create a regular timed event
    sample_event = create_sample_event()
    result = create_calendar_event(SERVICE_ACCOUNT_FILE, CALENDAR_ID, sample_event)
    
    if result:
        print("✅ Timed event created successfully!")
    
    print("\nCreating an all-day event...")
    
    # Create an all-day event
    #all_day_event = create_all_day_event()
    #result2 = create_calendar_event(SERVICE_ACCOUNT_FILE, CALENDAR_ID, all_day_event)
    
    #if result2:
    #    print("✅ All-day event created successfully!")


# Additional utility functions

def create_recurring_event():
    """
    Example of creating a recurring event.
    """
    timezone = pytz.timezone('America/New_York')
    start_time = datetime.now(timezone) + timedelta(days=1, hours=10)  # Tomorrow at 10 AM
    end_time = start_time + timedelta(hours=1)
    
    event = {
        'summary': 'Weekly Team Meeting',
        'description': 'Recurring weekly team meeting',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': str(timezone),
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': str(timezone),
        },
        'recurrence': [
            'RRULE:FREQ=WEEKLY;COUNT=10'  # Weekly for 10 occurrences
        ],
        'reminders': {
            'useDefault': True,
        },
    }
    
    return event

def list_calendars(service_account_file):
    """
    List all calendars accessible by the service account.
    Useful for finding calendar IDs.
    """
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, 
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        
        # List calendars
        calendar_list = service.calendarList().list().execute()
        
        print("Available calendars:")
        for calendar in calendar_list['items']:
            print(f"  - {calendar['summary']}: {calendar['id']}")
            
    except Exception as e:
        print(f"Error listing calendars: {e}")

if __name__ == "__main__":
    # Uncomment the line below to list available calendars first
    # list_calendars('path/to/your/service-account-key.json')
    
    main()