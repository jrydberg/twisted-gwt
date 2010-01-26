def unsigned(x):
    if x < 0:
        return long(x) + 2*0x80000000L
    return x


class SerializedInstanceReference:
    """Interface for describing a serialized instance reference reference.
    """
    SEPARATOR = '/'

    def __init__(self, typeSignature):
        if self.SEPARATOR in typeSignature:
            self.typeName, self.signature = typeSignature.split(self.SEPARATOR)
        else:
            self.typeName, self.signature = typeSignature, None


class Registry:
    """Generic registry.
    """

    def __init__(self):
        self.values = {}

    def register(self, key, value):
        self.values[key] = value

    def __getitem__(self, key):
        """Return item from registry.
        """
        return self.values.get(key, None)

    def __contains__(self, key):
        """Return true if the registry contains a value with the specified
        key.
        """
        return (key in self.values)

    
