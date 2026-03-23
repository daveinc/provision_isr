"""Exceptions for Provision ISR API client."""

class ProvisionError(Exception):
    """Base exception for Provision ISR API errors."""


class ProvisionConnectionError(ProvisionError):
    """Connection to device failed."""


class AuthenticationError(ProvisionError):
    """Authentication failed."""


class InvalidRequestError(ProvisionError):
    """Invalid request URL or parameters (Error Code 1)."""


class InvalidXMLFormatError(ProvisionError):
    """Invalid XML format (Error Code 2)."""


class InvalidXMLContentError(ProvisionError):
    """Invalid XML content or out‑of‑range parameters (Error Code 3)."""


class PermissionDeniedError(ProvisionError):
    """Permission denied (Error Code 4)."""
