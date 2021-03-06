class BadRequestError(Exception):
    status_code = 400
    name = "Bad Request"

    def __init__(self, message=None):
        Exception.__init__(self)
        self.message = message or "Feedsearch cannot handle the provided request."

    def to_dict(self):
        return {"error": self.name, "message": self.message}


class NotFoundError(Exception):
    status_code = 404
    name = "Not Found"

    def __init__(self, message=None):
        Exception.__init__(self)
        self.message = message or "Feedsearch cannot find the requested URL."

    def to_dict(self):
        return {"error": self.name, "message": self.message}
