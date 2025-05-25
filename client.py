class Client:
    def __init__(self, id: str, data_version: int):
        self.id = id
        self.data_version = data_version
        self.messages: list[dict] = []
