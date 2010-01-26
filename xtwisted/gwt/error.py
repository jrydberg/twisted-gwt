class SerializationException(Exception):
    """Serialization exception.
    """


class MissingSerializer(SerializationException):
    """Custom field serializer is missing.
    """


class BadSignature(SerializationException):
    """Bad signature.
    """


class IncompatibleRemoteServiceException(Exception):
    """Incompatible services.
    """


class MissingProtocol(Exception):
    """Missing type protocol.
    """


class NoSuchInterface(Exception):
    """No such interface.
    """


class NoSuchMethod(Exception):
    """Bad method.
    """
