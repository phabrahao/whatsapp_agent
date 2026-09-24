from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from dotenv import load_dotenv
import langchain
from typing import List, Dict, Any
import base64
import json
from datetime import datetime, timedelta
import pytz
from calendar_test import create_calendar_event as create_gcal_event
from typing import Optional

langchain.debug = True

import os
api_key = os.getenv('OPENAI_API_KEY')
load_dotenv(override=True)
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
CALENDAR_ID = os.getenv('CALENDAR_ID')

def create_calendar_event(
    summary: str,
    start_datetime: str,
    end_datetime: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    timezone: str = "America/New_York"
) -> str:

    """Create event in google calendar

    Args:
        summary: Event title/name
        start_datetime: Start date and time in ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD for all-day events
        end_datetime: End date and time in ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD for all-day events (optional, defaults to 1 hour after start)
        location: Event location (optional)
        description: Event description (optional)
        timezone: Timezone for the event (default: America/New_York)
    
    Returns:
        String confirmation of event creation
    """
    try:
        # Parse the datetime
        tz = pytz.timezone(timezone)
        
        # Check if it's an all-day event (date only format)
        if 'T' not in start_datetime and len(start_datetime) == 10:
            # All-day event
            start_date = datetime.strptime(start_datetime, '%Y-%m-%d').date()
            if end_datetime and 'T' not in end_datetime and len(end_datetime) == 10:
                end_date = datetime.strptime(end_datetime, '%Y-%m-%d').date()
                # Check if this is actually a multi-day event
                if end_date > start_date:
                    # Multi-day event: Google Calendar uses exclusive end dates,
                    # so add 1 day to include the actual end date
                    end_date = end_date + timedelta(days=1)
                else:
                    # Same day or invalid range, treat as single day
                    end_date = start_date + timedelta(days=1)
            else:
                # No end date provided, single day event
                end_date = start_date + timedelta(days=1)
            
            event_config = {
                'summary': summary,
                'start': {
                    'date': start_date.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'date': end_date.isoformat(),
                    'timeZone': timezone,
                },
            }
        else:
            # Timed event
            if 'T' not in start_datetime:
                # If only date provided, assume it's at 9 AM
                start_datetime += 'T09:00:00'
            
            start_time = datetime.fromisoformat(start_datetime)
            if start_time.tzinfo is None:
                start_time = tz.localize(start_time)
            
            if end_datetime:
                if 'T' not in end_datetime and len(end_datetime) == 10:
                    end_datetime += 'T10:00:00'  # Default to 10 AM if only date provided
                end_time = datetime.fromisoformat(end_datetime)
                if end_time.tzinfo is None:
                    end_time = tz.localize(end_time)
            else:
                # Default to 1 hour duration
                end_time = start_time + timedelta(hours=1)
            
            event_config = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
            }
        
        # Add optional fields
        if location:
            event_config['location'] = location
        if description:
            event_config['description'] = description
            
        # Add default settings
        event_config.update({
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                    {'method': 'popup', 'minutes': 10},       # 10 minutes before
                ],
            },
            'visibility': 'default',
            'status': 'confirmed',
        })
        
        print(f"DEBUG: Event config being sent to Google Calendar:")
        print(json.dumps(event_config, indent=2, default=str))

        result = create_gcal_event(SERVICE_ACCOUNT_FILE, CALENDAR_ID, event_config)
        
        return f"Successfully created calendar event: '{summary}' on {start_datetime}"
        
    except Exception as e:
        return f"Error creating calendar event: {str(e)}"

def describe_image_with_llm(image_data: bytes) -> str:
    """Use OpenAI GPT-4V to describe image"""
    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
    current_year = datetime.now().year
    # Convert bytes to base64
    image_b64 = base64.b64encode(image_data).decode()
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": """Describe this image. If it is a invitation 
             extract the following information in JSON format:
        
        {
            "event_title": "The main title or name of the event",
            "date": "Event date (format as YYYY-MM-DD if possible, otherwise as written) If the format is just XX/ZZ, XX MUST BE DD AND ZZ MUST BE MM, NOT THE OTHER WAY AROUND",
            "time": "Event time (if specified)",
            "location": {
                "venue": "Name of the venue/place",
                "address": "Full address if available",
                "city": "City",
                "state": "State/Province",
                "country": "Country (if specified)"
            },
            "description": "Event description or additional details",
            "host": "Who is hosting/organizing the event",
            "dress_code": "Dress code if mentioned",
            "rsvp": {
                "required": true/false,
                "contact": "RSVP contact information",
                "deadline": "RSVP deadline if specified"
            },
            "additional_info": "Any other relevant information (parking, gifts, special instructions, etc.)"
        }
        
        If any information is not available in the image, use null for that field.
        Only extract information that is clearly visible in the invitation. """ + f"If not in the invite, the current year is {current_year}"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
            }
        ]
    )
    
    response = llm.invoke([message])
    return response.content

def process_multimodal_data(input_data: List[Dict[str, Any]]) -> str:
    """Process multimodal data in order and return combined prompt"""
    prompt_parts = []
    for item in input_data:
        if item["type"] == "text":
            content = item.get("content", "")
            if content:
                prompt_parts.append(str(content))
            
        elif item["type"] == "image":
            caption = item.get("caption", "")
            image_data = item["image"]
            description = describe_image_with_llm(image_data)
            
            if caption:
                prompt_parts.append(str(caption))
            if description:
                prompt_parts.append(str(description))
    
    return "\n".join(prompt_parts)

tools = [create_calendar_event]

def run_agent(prompt_input, tools=tools, thread_id=None, checkpointer=None):
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
    llm_with_tools = llm.bind_tools(tools)
    print('agent run')
    
    # Process multimodal input if it's a list of dicts
    if isinstance(prompt_input, list):
        print('isinstance run')
        processed_prompt = process_multimodal_data(prompt_input)
    else:
        processed_prompt = prompt_input

    # System message with instructions for calendar event creation
    sys_msg = SystemMessage(content="""You are a helpful assistant that can create Google Calendar events.

When users ask you to create calendar events, extract the relevant information and use the create_calendar_event function.

For the create_calendar_event function:
- summary: The event title/name
- start_datetime: Use ISO format YYYY-MM-DDTHH:MM:SS for timed events, or YYYY-MM-DD for all-day events
- end_datetime: Optional, use ISO format or leave empty for 1-hour default duration
- location: Full address or venue name if provided
- description: Any additional details about the event
- timezone: Use appropriate timezone (default is America/New_York)

If the user provides an invitation image, extract the event details from the image description and create the calendar event.

Give concise, helpful responses.
""")
    
    def assistant(state: MessagesState):
        input_messages = [sys_msg] + state["messages"]
        for msg in input_messages:
            print(f"{msg.__class__.__name__}: {msg.content}")
        
        response = llm_with_tools.invoke(input_messages)
        return {"messages": [response]}
        
    builder = StateGraph(MessagesState)

    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    react_graph = builder.compile(checkpointer=checkpointer)

    messages = [HumanMessage(content=processed_prompt)]

    messages = react_graph.invoke({"messages": messages}, {"configurable": {"thread_id": thread_id}})
    print(messages)
    return messages['messages'][-1].to_json().get('kwargs').get('content')
