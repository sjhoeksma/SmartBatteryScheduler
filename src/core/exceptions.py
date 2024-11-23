"""Exceptions for EcactusEcos"""


class EcactusEcosException(Exception):
    """Base exception of the EcactusEcos client"""

    pass


class EcactusEcosUnauthenticatedException(EcactusEcosException):
    """An attempt is made to perform a request which requires authentication while the client is not authenticated."""

    pass


class EcactusEcosConnectionException(EcactusEcosException):
    """An error occured in the connection with the API."""

    pass


class EcactusEcosDataException(EcactusEcosException):
    """An error occured receiving data with the API."""

    pass
