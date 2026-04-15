import uuid


class ThreadManager:
    def __init__(self):
        self.threads = {}

    def create_thread(self, user_id: str):
        thread_id = str(uuid.uuid4())

        self.threads[thread_id] = {
            "user_id": user_id,
            "messages": []
        }

        return thread_id

    def add_message(self, thread_id: str, role: str, content: str):
        if thread_id not in self.threads:
            return

        self.threads[thread_id]["messages"].append({
            "role": role,
            "content": content
        })

    def get_thread(self, thread_id: str):
        return self.threads.get(thread_id, {"messages": []})