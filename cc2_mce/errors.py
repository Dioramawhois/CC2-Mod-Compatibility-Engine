from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cc2_mce.diagnostics import Diagnostic


class MCEError(Exception):
    exit_code = 4


class InputError(MCEError):
    pass


class DiagnosticError(InputError):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.cause)
        self.diagnostic = diagnostic


class BaselineError(MCEError):
    exit_code = 3


class ToolError(MCEError):
    exit_code = 5
