import threading
from collections import defaultdict
from agent import run_agent

class MessageBuffer:
    def __init__(self, instance, checkpointer):
        self.buffer_time = 5.0
        self.buffers = defaultdict(list)
        self.timers = {}
        self.lock = threading.Lock()
        self.evolution_api = instance
        self.checkpointer = checkpointer
        print("MessageBuffer initialized")  

    def add_message(self, user_id, message):
        print(f"Adding message for {user_id}: {message}")  
        with self.lock:
            try:
                self.buffers[user_id].append(message)
                print(f"Current buffer for {user_id}: {self.buffers[user_id]}")  
                
                if user_id in self.timers:
                    print(f"Cancelling existing timer for {user_id}")  
                    self.timers[user_id].cancel()
                
                self.timers[user_id] = threading.Timer(
                    self.buffer_time,
                    self._process_buffer_with_logging,  
                    args=[user_id]
                )
                self.timers[user_id].daemon = True
                self.timers[user_id].start()
                print(f"Started new timer for {user_id}")  
                
            except Exception as e:
                print(f"ERROR in add_message: {str(e)}")  

    def _process_buffer_with_logging(self, user_id):
        print(f"Timer expired for {user_id}, processing buffer...")  
        try:
            self.process_buffer(user_id)
        except Exception as e:
            print(f"ERROR in timer callback: {str(e)}")  

    def process_buffer(self, user_id):
        with self.lock:
            print(f"Processing buffer for {user_id}")  
            messages = self.buffers.get(user_id, [])
            if messages:
                print(f"Found {len(messages)} messages to process") 
                try:
                    self.send_to_processing(user_id, messages)
                except Exception as e:
                    print(f"ERROR in send_to_processing: {str(e)}")  
                    self._cleanup_user(user_id)

    def _cleanup_user(self, user_id):
        if user_id in self.buffers:
            del self.buffers[user_id]
        if user_id in self.timers:
            del self.timers[user_id]
        print(f"Cleaned up resources for {user_id}") 

    def send_to_processing(self, user_id, messages):
        print(f"Processing {len(messages)} messages for {user_id}")
                
        # Process with LangGraph
        response = run_agent(
            messages, 
            thread_id=user_id,
            checkpointer=self.checkpointer
        )
        
        self.evolution_api.send_message(user_id, response)
        print("Messages processed and sent successfully")



