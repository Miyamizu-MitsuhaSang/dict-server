import uuid


class KeyGenerator:

    @staticmethod
    def generate_uuid():
        return str(uuid.uuid4())