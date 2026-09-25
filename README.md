# WhatsApp Calendar Agent

A WhatsApp bot that turns messages and photos of invitations into Google Calendar events. Send it "Dentist on October 14, 2026 at 3pm" or a picture of a wedding invitation, and it creates the event and replies with a confirmation.

It connects to WhatsApp through [Evolution API](https://github.com/EvolutionAPI/evolution-api). A [LangGraph](https://github.com/langchain-ai/langgraph) agent running on OpenAI or Groq models works out what you asked for, and a Google service account writes the event to your calendar.

> **Status:** personal prototype. Read [Limitations](#limitations) before exposing it to anyone else.

## How it works

1. Evolution API receives a WhatsApp message and POSTs it to the Flask webhook in `whatsapp.py`.
2. Text messages are passed on as they are. Image messages are downloaded from WhatsApp's CDN and decrypted locally with the message's `mediaKey` (`decrypt.py`).
3. `MessageBuffer` (`buffer.py`) collects each sender's messages and waits 5 seconds after the last one. That way a photo followed by "this is on Saturday" is handled as one request.
4. The agent (`agent.py`) sends each image to a vision model. If the image is an invitation, the model extracts the title, date, time, venue, host, dress code and RSVP details as JSON.
5. The combined text goes to a LangGraph ReAct agent that has one tool, `create_calendar_event`. Conversation history is kept per phone number, so follow-up messages have context.
6. The tool builds the Google Calendar event (timed, all-day or multi-day) and inserts it through `calendar_test.py`.
7. The agent's reply is sent back to the sender through Evolution API (`evolution.py`).

## Project structure

| File | Purpose |
|---|---|
| `whatsapp.py` | Entry point. Flask app that receives Evolution API webhooks on `/webhook` and exposes `/health`. |
| `buffer.py` | Per-sender message buffer with a 5-second debounce. Calls the agent and sends the reply. |
| `agent.py` | LangGraph agent on OpenAI: `gpt-4o-mini` for chat, `gpt-4o` for images. Defines the calendar tool. |
| `agent_groq.py` | The same agent on Groq: `llama-3.3-70b-versatile` for chat, `llama-4-scout-17b-16e-instruct` for images. Only used if you switch to it (see below). |
| `evolution.py` | Minimal Evolution API client that sends text messages. |
| `decrypt.py` | Downloads and decrypts WhatsApp image media (AES-256-CBC with HKDF-derived keys). |
| `calendar_test.py` | Google Calendar helper that inserts an event with a service account. Can also be run on its own to create a sample event. |
| `invitation_ocr.py` | Standalone CLI that extracts invitation details from an image file. Not used by the bot. |
| `buffer.ipynb` | Development notebook. Not needed to run the bot. |

## Requirements

- Python 3.10+
- A running [Evolution API](https://doc.evolution-api.com/) instance at `http://localhost:8080`, with a WhatsApp number connected
- A Google Cloud project with the Google Calendar API enabled and a service account key (JSON)
- An OpenAI API key, or a Groq API key if you use `agent_groq.py`

## Setup

### 1. Install dependencies

There is no `requirements.txt` yet, so install the packages directly:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install flask python-dotenv requests pytz pycryptodome pillow openai \
    langchain langchain-core langchain-openai langchain-groq langgraph \
    google-auth google-api-python-client
```

### 2. Set up Google Calendar

1. In the Google Cloud Console, enable the **Google Calendar API** and create a **service account**. Download its JSON key into the project folder. `*.env` and the key file are git-ignored; if your key has a different filename, add it to `.gitignore`.
2. In Google Calendar, open the calendar the bot should write to and go to **Settings and sharing → Share with specific people**. Add the service account's email address with the **Make changes to events** permission.
3. Copy the **Calendar ID** from the **Integrate calendar** section.

### 3. Set environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...                      # only needed for agent_groq.py
EVOLUTION_API_KEY=your-evolution-api-key
INSTANCE_NAME=your-evolution-instance
SERVICE_ACCOUNT_FILE=your-service-account.json
CALENDAR_ID=xxxxxxxx@group.calendar.google.com
EVOLUTION_API_URL=http://localhost:8080   # not read yet: the URL is hard-coded in evolution.py
```

### 4. Point the Evolution API webhook at the bot

In the Evolution API manager, or through its webhook endpoint, set your instance's webhook URL to the Flask server and enable the `MESSAGES_UPSERT` event:

```
http://<host>:5000/webhook
```

If Evolution API runs in Docker Desktop and the bot runs on the host machine, use `host.docker.internal` as `<host>`.

## Running

```bash
python whatsapp.py
```

The server listens on port 5000. To check that it's running:

```bash
curl http://localhost:5000/health
# {"status": "healthy"}
```

Then message the connected WhatsApp number, for example:

- "Dentist on October 14, 2026 at 3pm at 200 Main St"
- a photo of an invitation, with or without a caption

### Using Groq instead of OpenAI

`buffer.py` imports the OpenAI agent. To use Groq, change the import:

```python
from agent_groq import run_agent
```

### Standalone scripts

```bash
python invitation_ocr.py path/to/invitation.jpg   # prints the extracted invitation as JSON
python calendar_test.py                           # creates a sample event
```

`main()` in `calendar_test.py` has the service account file and calendar ID hard-coded. Edit them before you run it.

## Calendar event defaults

- A timed event with no end time lasts 1 hour.
- A date with no time becomes an all-day event. Multi-day ranges include the last day.
- The timezone defaults to `America/New_York` unless the model passes a different one. The default is set in the signature of `create_calendar_event` in `agent.py`.
- Every event gets an email reminder 24 hours before and a pop-up reminder 10 minutes before.

## Limitations

- **No access control.** Anyone who messages the connected number can create events on your calendar, and that includes messages in groups the number belongs to. The webhook has no authentication, and Flask runs with `debug=True` on `0.0.0.0`. Don't expose port 5000 to the internet.
- **Memory lives in the process.** Conversation history uses LangGraph's `MemorySaver` and is lost when the server restarts.
- **Plain text and images only.** Messages that arrive as `extendedTextMessage` are logged but not answered. That covers quoted replies, messages with link previews and many messages sent from WhatsApp Web. Audio, video and documents are ignored too.
- **Create only.** The agent can't list, edit or delete events.
- **One calendar.** Every user writes to the calendar set in `CALENDAR_ID`.
