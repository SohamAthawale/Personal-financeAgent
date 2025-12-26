class AgentMemory:
    def __init__(self):
        self.events = []

    def log(self, action, context):
        self.events.append({
            "action": action,
            "context": context
        })
