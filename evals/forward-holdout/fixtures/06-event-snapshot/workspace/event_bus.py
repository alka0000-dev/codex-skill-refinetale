class EventBus:
    def __init__(self):
        self._handlers = {}

    def on(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)
        return handler

    def emit(self, event, payload):
        results = []
        for handler in self._handlers.get(event, []):
            results.append(handler(payload))
        return results
