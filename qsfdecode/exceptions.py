

class ExportException(Exception):

    def __init__(self, msg, reason):
        super().__init__(msg)
        self._reason = reason

    @property
    def reason(self):
        return self._reason


class JsonException(Exception):

    def __init__(self, msg):
        super().__init__(msg)