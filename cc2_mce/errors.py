class MCEError(Exception):
    exit_code = 4


class InputError(MCEError):
    pass


class BaselineError(MCEError):
    exit_code = 3


class ToolError(MCEError):
    exit_code = 5
