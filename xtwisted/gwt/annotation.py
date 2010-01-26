from zope.interface import implements, Interface, Attribute
from binascii import crc32

from twisted.python.components import registerAdapter
from twisted.python import reflect

from xtwisted.gwt import igwt, error
from xtwisted.gwt.util import SerializedInstanceReference, unsigned, Registry

import calendar
import time


TYPES_EXCLUDED_FROM_SIGNATURES = (
    'Z', 'B', 'C', 'D', 'F', 'I', 'J', 'S',
    'java.lang.String',
    'java.lang.Throwable',	# XXX: is this correct?
    'java.lang.Exception',
    'java.lang.Object',		# XXX: is this correct?
)

JRE_SERIALIZER_PACKAGE = "com.google.gwt.user.client.rpc.core."


class Type(object):
    """Base class for all types.
    """
    implements(igwt.IType)

    superType = None

    def isPrimitive(self):
        return False

    def getSignature(self, crc):
        """Return signature.
        """
        crc = crc32(self.getTypeName(), crc)

        if self.getTypeName() in TYPES_EXCLUDED_FROM_SIGNATURES:
            return crc

        customSerializer = getCustomFieldSerializer(self)
        crc = customSerializer.getSignature(crc)

        if self.superType is not None:
            crc = self.superType.getSignature(crc)

        return crc


def registerTypeAdapter(typeClass, instanceClass):
    """Associate a value class with an type.

    This enables us to lookup the type for a value by simply adopting
    it to IType.  This is mostly used for exceptions.
    """
    def adapter(original):
        return typeClass()
    registerAdapter(adapter, instanceClass, igwt.IType)


class Object(Type):

    def getTypeName(self):
        return 'java.lang.Object'



class _PrimitiveType(Type):
    """Base class for primitive types.
    """

    def getName(self):
        """Return name of type.
        """
        return self.typeName

    def getTypeName(self):
        """Return type signature.
        """
        return self.primitiveTypeName

    def getSignature(self, crc):
        # primitive types do not have a crc signature
        return crc32(self.getTypeName(), crc)

    def isPrimitive(self):
        """Return true if the type is primitive.
        """
        return True


class Integer(_PrimitiveType):
    typeName = 'int'
    primitiveTypeName = 'I'


class Long(_PrimitiveType):
    typeName = 'long'
    primitiveTypeName = 'J'


class Short(_PrimitiveType):
    typeName = 'short'
    primitiveTypeName = 'S'


class Boolean(_PrimitiveType):
    typeName = 'boolean'
    primitiveTypeName = 'Z'


class Void(Type):
    
    def getTypeName(self):
        return 'java.lang.Void'


class String(Type):
    """String serializer.
    """
    typeName = 'String'

    #def isPrimitive(self):
    #    return True

    def getName(self):
        return 'String'
    
    def getTypeName(self):
        """Return type name.
        """
        return 'java.lang.String'

    def getSignature(self, crc):
        """Return signature for type.
        """
        return crc32(self.getTypeName(), crc)


registerTypeAdapter(String, str)
registerTypeAdapter(String, unicode)



class RemoteType(Type):
    """A remote type.
    """
    
    def getTypeName(self):
        """Return name of the remote type.
        """
        return self.remoteName


def generateSignature(typeInstance):
    """Generate signature for type instance and return it as an integer.
    """
    return unsigned(typeInstance.getSignature(0))


typeSignatureCache = {}

def getTypeSignature(typeInstance):
    """Return type signature for given type instance.
    """
    typeClass = typeInstance.__class__
    if typeClass in typeSignatureCache:
        return typeSignatureCache[typeClass]
    typeSignatureCache[typeClass] = '%s/%s' % (
        typeInstance.getTypeName(),
        generateSignature(typeInstance)
        )
    return typeSignatureCache[typeClass]


def isPrimitiveType(typeInstance):
    """Return true if the specified type is considered to be a primitive
    type.
    """
    return (
        isinstance(typeInstance, String) or
        isinstance(typeInstance, Integer) or
        isinstance(typeInstance, Long) or
        isinstance(typeInstance, Short) or
        isinstance(typeInstance, Boolean)
        )


class Array(Type):
    """An array that may hold a list of elements of the same type.
    """

    def __init__(self, compoundType):
        self.compoundType = compoundType

    def getTypeName(self):
        """Return type name.
        """
        def isPrimitiveTypeName(typeName):
            return len(typeName.split('.')) == 1
        compoundTypeName = self.compoundType.getTypeName()
        if isPrimitiveTypeName(compoundTypeName):
            return '[%s' % compoundTypeName
        else:
            return '[L%s;' % compoundTypeName

    def getSignature(self, crc):
        """Calculate signature.
        """
        crc = crc32(self.getTypeName(), crc)
        # add the compound type too:
        crc = self.compoundType.getSignature(crc)
        return crc


class CustomFieldSerializer:
    """Base functionality for the custom field serializers.
    """
    superType = Object()

    def __init__(self, instanceType):
        self.instanceType = instanceType

    def getTypeName(self):
        """Return type name.
        """
        return self.className

    def getSignature(self, crc):
        """Get signature for custom field serializer.
        """
        # assumption: custom field serializers have no fields.
        crc = crc32(self.getTypeName(), crc)
        if self.superType is not None:
            crc = self.superType.getSignature(crc)
        return crc


typeRegistry = {}

def registerTypeClass(typeClass):
    """Register a type so that it can be looked up by its name.
    """
    typeRegistry[typeClass().getTypeName()] = typeClass


def registerCustomFieldSerializer(serializerClass, typeClass):
    """Register a custom field serializer for a specific type.
    """
    registerAdapter(
        serializerClass, typeClass, igwt.ICustomFieldSerializer
        )
    registerTypeClass(typeClass)


def getTypeClassByTypeName(typeName):
    """Lookup a type class based on its type name.
    """
    return typeRegistry.get(typeName, None)


class IEmpty(Interface):
    """An empty type protocol.
    """


class RemoteAttribute(Attribute):
    """Attribute with type annotation.
    """

    def __init__(self, typeInstance, doc=''):
        super(RemoteAttribute, self).__init__(doc)
        self.typeInstance = typeInstance


class TypeProtocolRegistry(Registry):
    """Registry over serialization protocol for different
    types.

    The key is a type class, and the value is the protocol.
    """

typeProtocolRegistry = TypeProtocolRegistry()


def registerTypeProtocol(typeClass, protocol):
    """Associate the specified type protocol with the given type.
    """
    typeProtocolRegistry.register(typeClass, protocol)
    # assume that the user also wants to register the type:
    registerTypeClass(typeClass)


class GenericFieldSerializer(CustomFieldSerializer):
    """The generic field serialzier is responsible for serializing objects
    using their type protocol.
    """

    def getTypeName(self):
        return self.instanceType.getTypeName()

    def gatherSerializableFields(self, instanceType, all=False):
        """Gather fields that can be serialzied by the instance type.
        """
        #instanceType = igwt.IType(instance)
        def _gather(t, d):
            protocol = typeProtocolRegistry[t.__class__]
            if protocol is None:
                return
            for fieldName in protocol.names():
                d[fieldName] = protocol.get(fieldName).typeInstance
            if all and t.superType is not None:
                _gather(t.superType, d)
        if not hasattr(instanceType, '__generic_fields__'):
            fields = dict()
            _gather(instanceType, fields)
            instanceType.__generic_fields__ = fields
        return instanceType.__generic_fields__

    def getSignature(self, crc):
        protocol = typeProtocolRegistry[self.instanceType.__class__]
        if protocol is None:
            raise error.MissingProtocol(self.instanceType.__class__)
        fields = self.gatherSerializableFields(self.instanceType)
        for fieldName in sorted(fields.keys()):
            typeInstance = fields[fieldName]
            crc = crc32(fieldName, crc)
            crc = crc32(typeInstance.getTypeName(), crc)
        return crc

    def serialize(self, instance, writer):
        protocol = typeProtocolRegistry[self.instanceType.__class__]
        if protocol is None:
            raise error.MissingProtocol(self.instanceType.__class__)
        instanceType = self.instanceType
        while instanceType is not None:
            fields = self.gatherSerializableFields(instanceType)
            #print "fields for ", instanceType,"is", fields
            for fieldName in sorted(fields.keys()):
                value = getattr(instance, fieldName)
                # FIXME: check against fields typeInstance
                #print "try to get type for", fieldName, value
                typeInstance = igwt.IType(value, fields[fieldName])
                #print "  got", typeInstance, "suggested was", fields[fieldName]
                writer.serializeValue(value, typeInstance)
            instanceType = instanceType.superType
        # done
#         fields = self.gatherSerializableFields(self.instanceType, True)
#         for fieldName in sorted(fields.keys()):
#             value = getattr(instance, fieldName)
#             # FIXME: check against fields typeInstance
#             print "try to get type for", fieldName, value
#             typeInstance = igwt.IType(value, fields[fieldName])
#             print "  got", typeInstance, "suggested was", fields[fieldName]
#             writer.serializeValue(value, typeInstance)
        # done

    def deserialize(self, reader):
        protocol = typeProtocolRegistry[self.instanceType.__class__]
        if protocol is None:
            raise error.MissingProtocol(self.instanceType.__class__)
        factory = igwt.IInstanceFactory(self.instanceType)
        instance = factory.buildInstance()
        instanceType = self.instanceType
        while instanceType is not None:
            fields = self.gatherSerializableFields(instanceType)
            for fieldName in sorted(fields.keys()):
                typeInstance = fields[fieldName]
                value = reader.deserializeValue(typeInstance)
                setattr(instance, fieldName, value)
            instanceType = instanceType.superType
        return instance


def getCustomFieldSerializer(typeInstance):
    """Return a custom field serializer for the given type.
    """
    customSerializer = igwt.ICustomFieldSerializer(typeInstance, None)
    if customSerializer is None:
        customSerializer = GenericFieldSerializer(typeInstance)
    return customSerializer


class ArrayCustomFieldSerializer(CustomFieldSerializer):
    """Custom field serializer for arrays.
    """
    implements(igwt.ICustomFieldSerializer)

    def __init__(self, arrayType):
        self.arrayType = arrayType
        self.compoundType = arrayType.compoundType

    def getSignature(self, crc):
        assert False, "is this code ever executed?"
        crc = crc32(self.compoundType.getTypeName(), crc)
        customSerializer = igwt.ICustomFieldSerializer(self.compoundType, None)
        if customSerializer is not None:
            crc = customSerializer.getSignature(crc)
        return crc

    def getTypeName(self):
        """Return class name of custom field serializer.
        """
        assert False
        if self.compoundType.isPrimitive():
            qualifiedTypeName = ('java.lang.' 
                                 + self.compoundType.typeName)
        else:
            qualifiedTypeName = 'java.lang.Object'
        qualifiedTypeName += '_Array_CustomFieldSerializer'
        return JRE_SERIALIZER_PACKAGE + qualifiedTypeName

    def deserialize(self, reader):
        """Deserialize into an list of elements.
        """
        count = reader.readInt()
        value = list()
        for c in range(count):
            value.append(reader.deserializeValue(self.compoundType))
        return value

    def serialize(self, value, writer):
        """Serialize into tokens.
        """
        writer.writeInt(len(value))
        for subvalue in value:
            writer.serializeValue(subvalue, self.compoundType)


# the array custom field serializer is not registered with the builder.
registerAdapter(
    ArrayCustomFieldSerializer, Array, igwt.ICustomFieldSerializer
    )


class HashMap(Object):

    def getTypeName(self):
        return 'java.util.HashMap'


class HashMapCustomFieldSerializer(CustomFieldSerializer):
    implements(igwt.ICustomFieldSerializer)

    className = (
        JRE_SERIALIZER_PACKAGE + 'java.util.HashMap_CustomFieldSerializer'
        )

    def deserialize(self, reader):
        """Deserialize into an list of elements.
        """
        count = reader.readInt()
        value = dict()
        #print "count is", count
        for c in range(count):
            key = reader.readObject()
            #print "got key", key
            value[key] = reader.readObject()
            #print "got value", value[key]
        return value

    def serialize(self, value, writer):
        """Serialize into tokens.
        """
        writer.writeInt(len(value))
        #print "hashmap custsom: ", len(value)
        for key, subvalue in value.iteritems():
            #print "hashmap: write key", key
            writer.writeObject(key)
            #print "hashmap: write value", subvalue
            writer.writeObject(subvalue)
        # done

registerCustomFieldSerializer(HashMapCustomFieldSerializer, HashMap)


class ArrayList(Object):
    
    def __init__(self, compoundType=None):
        self.compoundType = compoundType

    def getTypeName(self):
        return 'java.util.ArrayList'


class ArrayListCustomFieldSerializer(CustomFieldSerializer):
    """Custom field serializer for java.util.ArrayList.
    """
    implements(igwt.ICustomFieldSerializer)

    className = (
        JRE_SERIALIZER_PACKAGE + 'java.util.ArrayList_CustomFieldSerializer'
        )

    def __init__(self, arrayType):
        self.arrayType = arrayType
        self.compoundType = arrayType.compoundType

    def deserialize(self, reader):
        """Deserialize into an list of elements.
        """
        count = reader.readInt()
        value = list()
        for c in range(count):
            value.append(reader.readObject())
        return value

    def serialize(self, value, writer):
        """Serialize into tokens.
        """
        writer.writeInt(len(value))
        for subvalue in value:
            writer.writeObject(subvalue)

registerCustomFieldSerializer(ArrayListCustomFieldSerializer, ArrayList)


class Date(Object):

    def getTypeName(self):
        return 'java.util.Date'


import datetime, time
        

class DateCustomFieldSerializer(CustomFieldSerializer):
    """Custom field serializer for java.util.Date.
    """
    implements(igwt.ICustomFieldSerializer)

    className = (
        JRE_SERIALIZER_PACKAGE + 'java.util.Date_CustomFieldSerializer'
        )

    def __init__(self, dateType):
        self.dateType = dateType

    def deserialize(self, reader):
        """Deserialize into a datetime object.
        """
        milliseconds = reader.readLong()
        return datetime.datetime.utcfromtimestamp(milliseconds/1000)

    def serialize(self, value, writer):
        """Serialize into tokens.
        """
        t = calendar.timegm(value.utctimetuple()) * 1000
        writer.writeLong(t)

registerCustomFieldSerializer(DateCustomFieldSerializer, Date)


class _PrimitiveCustomFieldSerialzier(CustomFieldSerializer):

    def getSignature(self, crc):
        """Return type signature for field serializer.
        """
        # primitive types do not have signatures, nor does custom
        # field serializers for primitive types.
        return crc32(self.className, crc)


class BooleanCustomFieldSerializer(_PrimitiveCustomFieldSerialzier):
    className = 'Z'
    
    def deserialize(self, reader):
        return reader.readInt() and True or False

    def serialize(self, value, writer):
        writer.writeInt({True:1, False:0}[value])

registerCustomFieldSerializer(BooleanCustomFieldSerializer, Boolean)


class IntegerCustomFieldSerializer(_PrimitiveCustomFieldSerialzier):
    className = 'I'
    
    def deserialize(self, reader):
        return reader.readInt()

    def serialize(self, value, writer):
        writer.writeInt(value)

registerCustomFieldSerializer(IntegerCustomFieldSerializer, Integer)


class StringCustomFieldSerializer(_PrimitiveCustomFieldSerialzier):
    className = 'java.lang.String'
    
    def deserialize(self, reader):
        return reader.readString()

    def serialize(self, value, writer):
        writer.writeString(value)

registerCustomFieldSerializer(StringCustomFieldSerializer, String)


class AnnotationBuilder:
    """Annotation builder.
    """
    
    def __init__(self):
        self.annotationCache = {}

    def buildAnnotation(self, typeSignature):
        """Build an annotation from a type signature.
        """
        if typeSignature in self.annotationCache:
            return self.annotationCache[typeSignature]
        # we have to treat arrays in a special way.
        if typeSignature[0] == '[':
            if typeSignature[1] == 'L':
                ref = SerializedInstanceReference(typeSignature[2:])
                compoundType = self.buildAnnotation(ref.typeName[:-1])
            else:
                ref = SerializedInstanceReference(typeSignature[1:])
                compoundType = self.buildAnnotation(ref.typeName)
            typeInstance = Array(compoundType)
        else:
            ref = SerializedInstanceReference(typeSignature)
            typeClass = getTypeClassByTypeName(ref.typeName)
            if typeClass is None:
                raise error.MissingSerializer(ref.typeName)
            typeInstance = typeClass()

        if ref.typeName not in TYPES_EXCLUDED_FROM_SIGNATURES:
            if ref.signature is not None:
                # FIXME: should we cache the signature?
                signature = generateSignature(typeInstance)
                if long(ref.signature) != signature:
                    raise error.BadSignature(
                        long(ref.signature), signature
                        )
        
        self.annotationCache[typeSignature] = typeInstance
        return typeInstance


annotationBuilder = AnnotationBuilder()
buildAnnotation = annotationBuilder.buildAnnotation



class ThrowableType(Type):
    superType = Object()

    def getTypeName(self):
        return 'java.lang.Throwable'


class ExceptionType(Object):
    superType = ThrowableType()

    def getTypeName(self):
        return 'java.lang.Exception'


registerTypeProtocol(ExceptionType, IEmpty)


class RuntimeExceptionType(Object):
    superType = ExceptionType()

    def getTypeName(self):
        return 'java.lang.RuntimeException'


registerTypeProtocol(RuntimeExceptionType, IEmpty)


def registerRuntimeException(instanceClass, className, protocol=None):
    """Register the instance class as a runtime exception.
    """
    class Type(Object):
        superType = RuntimeExceptionType()
        def getTypeName(self):
            return className
    if protocol is None:
        protocol = IEmpty
    registerTypeProtocol(Type, protocol)
    registerTypeAdapter(Type, instanceClass)


registerRuntimeException(
    error.IncompatibleRemoteServiceException, 
    'com.google.gwt.user.client.rpc.IncompatibleRemoteServiceException'
)

# register some other errors:

class INoSuchInterfaceException(Interface):
    interfaceName = RemoteAttribute(String(), 
                                    "name of missing interface")

registerRuntimeException(
    error.NoSuchInterface,
    'org.twisted.gwt.client.rpc.NoSuchInterfaceException',
    INoSuchInterfaceException
)


class INoSuchMethodException(Interface):
    methodName = RemoteAttribute(String(),
                                 "name of missing method")
    
registerRuntimeException(
    error.NoSuchMethod,
    'org.twisted.gwt.client.rpc.NoSuchMethodException',
    INoSuchMethodException
)

