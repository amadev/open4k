class OpenStackControllerException(Exception):
    """A generic OpenStack Controller exception to be inherited from"""


class TaskException(OpenStackControllerException):
    """A generic handler error exception"""


class OsDplValidationFailed(OpenStackControllerException):
    def __init__(self, message=None, code=400):
        super().__init__()
        self.message = message
        self.code = code
