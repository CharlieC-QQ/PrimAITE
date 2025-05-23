# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
"""PrimAITE-specific exceptions."""


class PrimaiteError(Exception):
    """The root PrimAITE Error."""

    pass


class NetworkError(PrimaiteError):
    """Raised when an error occurs at the network level."""

    pass
