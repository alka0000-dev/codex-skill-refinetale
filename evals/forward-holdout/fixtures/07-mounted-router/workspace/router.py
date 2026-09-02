class NotFound(Exception):
    pass


class Router:
    def __init__(self):
        self._routes = {}

    def add(self, path, handler):
        self._routes[path] = handler

    def resolve(self, path):
        try:
            return self._routes[path]
        except KeyError:
            raise NotFound(path)
