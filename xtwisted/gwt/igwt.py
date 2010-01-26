from zope.interface import implements, Interface, Attribute


class IType(Interface):
    """Base class for types.
    """
    superType = Attribute("superType", "super type of type")

    def isPrimitive():
        """Return true if type is primtive.
        """
        # XXX: this can be deduced from the type name.

    def getTypeName():
        """Return type name.
        """

    def getSignature(crc):
        """Return signature for the type, using the initial crc.
        """


class ICustomFieldSerializer(IType):
    """Custom field serializer.
    
    @cvar className: The fully quallified java name of the 
        custom field serializer.
    """

    def serialize(value, writer):
        """Serialize value to writer.
        """

    def deserialize(reader):
        """Deserialize value.
        """


class IInstanceFactory(Interface):
    """Builder of instances.
    """
    
    def buildInstance():
        """Build an instance.
        """


class ISerializable(Interface):
    """Interface that describes that an object can be serialized, and the
    protocol for its serialization.
    """
    fieldTypes = Attribute("fieldTypes", "field annotations")


class IDeserializer(Interface):
    """Providers gives the possibility to deserialize a transport
    token stream into a value.
    """

    def deserialize(reader):
        """Deserialize value from reader.
        """


class ISerializer(Interface):
    """"Providers gives the possibility to serialize a value into
    a list of tokens.
    """
    typeSignature = Attribute("Signature of serialized type")
    

    def serialize(value, writer):
        """Serialize value to writer.
        """


class ITokenReader(Interface):
    """XXX
    """
    
    def readToken():
        """Read a raw token from the transport token stream.
        """

    def readInt():
        """Read an integer from the transport token stream.
        """

    def readString():
        """Read a string from the transport token stream.
        """

    def readObject():
        """Read any type of object specified by the type name.
        """


class ITokenWriter(Interface):
    """XXX
    """

    def writeInt(c):
        """Write an integer to the transport token stream.
        """

    def writeString(c):
        """Write a string to the transport token stream.
        """


