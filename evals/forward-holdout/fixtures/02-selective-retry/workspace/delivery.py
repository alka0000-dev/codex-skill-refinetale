class TemporaryFailure(Exception):
    pass


class PermanentFailure(Exception):
    pass


def deliver(sender, message):
    return sender.send(message)
