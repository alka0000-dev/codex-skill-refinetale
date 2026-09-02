import json


class InvalidProfile(Exception):
    pass


class Profile:
    def __init__(self, user_id):
        self.user_id = user_id

    def __eq__(self, other):
        return isinstance(other, Profile) and self.user_id == other.user_id


def encode(profile):
    return json.dumps({"version": 1, "id": profile.user_id}, sort_keys=True)


def decode(raw):
    try:
        data = json.loads(raw)
        if data.get("version") != 1 or not isinstance(data.get("id"), str):
            raise InvalidProfile()
        return Profile(data["id"])
    except (TypeError, ValueError, AttributeError) as error:
        if isinstance(error, InvalidProfile):
            raise
        raise InvalidProfile() from error
