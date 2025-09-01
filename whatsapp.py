import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import json
from datetime import datetime
from buffer import MessageBuffer
from evolution import EvolutionApi
from langgraph.checkpoint.memory import MemorySaver
from decrypt import decrypt_image
load_dotenv()
api_key = os.getenv('EVOLUTION_API_KEY')
checkpointer = MemorySaver()
app = Flask(__name__)
instance_name = 'walter'
evolution_api = EvolutionApi(instance_name, api_key)
message_buffer = MessageBuffer(evolution_api, checkpointer)
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data is None:
      return jsonify({"error": "Invalid JSON"}), 400  # Bad Request
    try:

        # Print timestamp and raw data for debugging
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Webhook received:")


        print(f"🔍 RAW DATA: {json.dumps(data, indent=2)}")

        # Check if it's a message event
        if data.get('event') == 'messages.upsert':
            message_data = data.get('data', {})
            # Get sender info
            sender = message_data.get('pushName', 'Unknown')
            phone = message_data.get('key', {}).get('remoteJid', 'Unknown')
            
            # Get message content
            message_type = message_data.get('messageType', 'unknown')
            
            if message_type == 'conversation':
                content = message_data.get('message', {}).get('conversation', '')
                if not message_data.get('key', {}).get('fromMe', True):
                    content = ({"type": "text", "content": content})
                    message_buffer.add_message(phone, content)
            elif message_type == 'imageMessage':
                url = message_data.get('message', {}).get('imageMessage', '').get('url', '')
                media_key = message_data.get('message', {}).get('imageMessage', '').get('mediaKey', '')
                caption = message_data.get('message', {}).get('imageMessage', '').get('caption', '')
                if not message_data.get('key', {}).get('fromMe', True):
                    decrypted = decrypt_image(url, media_key)
                    content = ({"type": "image", "image": decrypted, "caption": caption})
                    message_buffer.add_message(phone, content)
            elif message_type == 'extendedTextMessage':
                content = message_data.get('message', {}).get('extendedTextMessage', {}).get('text', '')
            else:
                content = f"[{message_type}]"
            timestamp = message_data.get('messageTimestamp', 'Unknown')
            # Display the message
            print(f"📱 New Message from: {sender}")
            print(f"📞 Phone: {phone}")
            print(f"💬 Content: {content}")
            print(f"🔤 Type: {message_type}")
            print(f"🕒 Timestamp: {timestamp}")
        else:
            # Handle other events
            event_type = data.get('event', 'unknown')
            print(f"🔔 Event: {event_type}")
            print(f"📄 Data: {json.dumps(data, indent=2)}")
        
        print("-" * 50)
        
        # Return success response
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"❌ Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    print("🚀 Starting Evolution API Webhook Server...")
    print("📡 Listening for webhooks on http://localhost:5000/webhook")
    print("🏥 Health check available at http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=True)