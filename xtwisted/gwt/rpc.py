from twisted.python import reflect, failure, components, log
from twisted.internet import defer
from zope.interface import implements, Interface

from xtwisted.gwt import igwt, annotation, util, error
from xtwisted.gwt.interface import remoteInterfaceRegistry
import time


SEPARATOR = u'|'


JS_ESCAPE_CHAR = '\\'
JS_QUOTE_CHAR = '\''
escapedChars = {
    '\0' : '0', '\b' : 'b', '\n' : 'n', '\t' : 't', '\f' : 'f',
    '\r' : 'r', JS_ESCAPE_CHAR: JS_ESCAPE_CHAR, JS_QUOTE_CHAR: JS_QUOTE_CHAR, '\"': '\"'
    }

nibble_map = '0123456789abcdef'

def needUnicodeEscape(c):
    if c == '\"':
        return True
    if c == '\n':
        return True
    if c == '%':
        return True
    if ord(c) >= 127:
        return True
    return False

def unicodeEscape(c, add):
    if ord(c) < 256:
        add('x')
        add(nibble_map[(ord(c) >> 4) & 0xf])
        add(nibble_map[(ord(c) >> 0) & 0xf])
    else:
        add('u')
        add(nibble_map[(ord(c) >> 12) & 0xf])
        add(nibble_map[(ord(c) >>  8) & 0xf])
        add(nibble_map[(ord(c) >>  4) & 0xf])
        add(nibble_map[(ord(c) >>  0) & 0xf])
        
def escapeString(val):
    sb = list()
    add = sb.append
    for ch in val:
        if ch in escapedChars:
            add(JS_ESCAPE_CHAR)
            add(escapedChars[ch])
        elif needUnicodeEscape(ch):
            add(JS_ESCAPE_CHAR)
            unicodeEscape(ch, add)
        else:
            add(ch)
    return u'%c%s%c' % (JS_QUOTE_CHAR, u''.join(sb), JS_QUOTE_CHAR)


class TokenStream(list):

    def next(self):
        """Return next token.
        """
        return self.pop(0)


class Response:
    """Response.
    """
    implements(igwt.ITokenWriter)

    def __init__(self, servlet):
        self.tokenStream = list()
        self.objectDatabase = list()
        self.stringTable = list()
        self.servlet = servlet

    def serializeValue(self, value, typeInstance):
        """Serialize value.
        """
        if annotation.isPrimitiveType(typeInstance):
            self.serialize(value, typeInstance)
        else:
            self.writeObject(value, typeInstance)

    def serialize(self, instance, typeInstance):
        """Serialize instance.
        """
        serializer = annotation.getCustomFieldSerializer(typeInstance)
        serializer.serialize(instance, self)

    def writeObject(self, instance, typeInstance=None):
        """Write an instance to the token stream.
        """
        if instance is None:
            self.writeString(None)
            return 
        if typeInstance is None:
            typeInstance = igwt.IType(instance)
        #if instance in self.objectDatabase:
        #    self.writeInt(self.objectDatabase.index(instance))
        #    return
        self.objectDatabase.append(instance)
        self.writeString(annotation.getTypeSignature(typeInstance))
        self.serialize(instance, typeInstance)
        
    def writeInt(self, val):
        """Write an integer to the token stream.
        """
        self.tokenStream.append(unicode(long(val)))

    def writeLong(self, val):
        """
        Write a long value.
        """
        highBits, lowBits = long(val) >> 32, long(val) & 0xffffffffL
        TWO_PWR_16_DBL = 0x10000
        TWO_PWR_32_DBL = TWO_PWR_16_DBL * TWO_PWR_16_DBL
        high = float(highBits) * TWO_PWR_32_DBL
        low = float(lowBits)
        if low < 0.0:
            low += TWO_PWR_32_DBL
        self.writeInt(low) 
        self.writeInt(high)

    def writeDouble(self, val):
        self.tokenStream.append(unicode(float(val)))

    def addString(self, strval):
        """Add a string to the string table and return the index.
        """
        if strval is None:
            return 0
        if strval in self.stringTable:
            return self.stringTable.index(strval) + 1
        self.stringTable.append(strval)
        return len(self.stringTable)

    def writeString(self, strval):
        """Write string to token stream.
        """
        self.writeInt(self.addString(strval))

    def _writePayload(self):
        """Write payload into a string and return it.
        """
        return u','.join(reversed(self.tokenStream))

    def _writeStringTable(self):
        """Write string table into a string and return it.
        """
        return u'[%s]' % u','.join(
            [escapeString(s) for s in self.stringTable]
            )
    
    def _writeHeader(self):
        """Write header to a string and return it.
        """
        return u','.join([unicode(self.flags), unicode(self.version)])

    def toString(self):
        """Return content of response as a string.
        """
        components = [
            self._writePayload(), self._writeStringTable(), self._writeHeader()
            ]
        return u'[%s]' % u','.join(components)


class Request:
    """Request.

    @ivar objectDatabase: List of deserialized objects.  Used to lookup
        back references.

    @ivar stringTable: Table of strings, indexed by a 1-based integer.
    """
    implements(igwt.ITokenReader)

    def __init__(self, servlet):
        self.servlet = servlet
        self.stringTable = dict()
        self.objectDatabase = list()

    def prepareToRead(self, content):
        """Prepare to read.
        """
        self.tokenStream = TokenStream(content.split(SEPARATOR))

    def buildStringTable(self):
        """Build string table from the token stream.
        """
        count = self.readInt()
        for i in range(count):
            self.stringTable[i + 1] = self.readToken()

    def readToken(self):
        """Read a raw token from token stream.
        """
        return self.tokenStream.next()

    def readInt(self):
        """Read an integer from the token stream.
        """
        return int(self.readToken())

    def readDouble(self):
        """Read a double from the token stream.
        """
        return float(self.readToken())

    def readLong(self):
        """Return a long from the token stream.
        """
        low = self.readDouble()
        high = self.readDouble()
        return long(high) + long(low)

    def readString(self):
        """Return a string from the token stream.
        """
        stringIndex = self.readInt()
        if stringIndex == 0:
            return None
        return self.stringTable[stringIndex]

    def rememberObject(self, instance, id=None):
        """Remember object.
        """
        if id is None:
            self.objectDatabase.append(instance)
        else:
            self.objectDatabase[id] = instance

    def reserveObject(self):
        id = len(self.objectDatabase)
        self.objectDatabase.append(None)
        return id

    def deserializeObject(self, typeSignature):
        """Deserialize an object according to the given type signature.
        """
        id = self.reserveObject()
        typeInstance = annotation.buildAnnotation(typeSignature)
        customSerializer = annotation.getCustomFieldSerializer(typeInstance)
        instance = customSerializer.deserialize(self)
        self.rememberObject(instance, id)
        return instance

    def readObject(self):
        # read the type signature of the serialized object.  if there
        # is no signature available, it must be the null instance.
        #
        # if the token is negative, it's a backreference to an already
        # deserialized object.
        typeSignatureIndex = self.readInt()
        if typeSignatureIndex == 0:
            return None
        elif typeSignatureIndex < 0:
            # backreference to object in object database
            return self.objectDatabase[-(typeSignatureIndex + 1)]
        else:
            typeSignature = self.stringTable[typeSignatureIndex]
        return self.deserializeObject(typeSignature)

    def deserializeValue(self, typeInstance):
        """Extract value from token stream.
        """
        if annotation.isPrimitiveType(typeInstance):
            customSerializer = igwt.ICustomFieldSerializer(typeInstance)
            return customSerializer.deserialize(self)
        return self.readObject()

    def deserializeValues(self, typeList):
        """Extract values from the token stream.  

        typeList is a lost of what should be extracted.  The returned
        list should be of the same length as typeList.
        """
        return [self.deserializeValue(tn) for tn in typeList]

    def _ebInvoke(self, reason, response):
        """Report back an error.
        """
        log.err(reason)
        typeInstance = igwt.IType(reason.value, None)
        if typeInstance is None:
            reason.value = error.IncompatibleRemoteServiceException()
            typeInstance = igwt.IType(reason.value)
        response.writeObject(reason.value, typeInstance)
        return u'//EX' + response.toString()

    def _cbInvoke(self, result, response, signature):
        """Return value.
        """
        if not isinstance(signature.returnTypeSignature, annotation.Void):
            if (signature.returnTypeSignature.isPrimitive() or
                isinstance(signature.returnTypeSignature, 
                           annotation.ArrayList)):
                response.serializeValue(result, signature.returnTypeSignature)
            else:
                response.writeObject(result)
        return u'//OK' + response.toString()

    def invoke(self, provider, signature, arguments, response):
        """Invoke method ok servlet interface provider.
        """
        methodName = signature.name
        func = getattr(provider, str(methodName), None)
        if func is None:
            raise error.NoSuchMethod()
        d = defer.maybeDeferred(func, *arguments)
        d.addCallback(self._cbInvoke, response, signature)
        return d

    def _evaluate1(self, response):
        remoteInterfaceName, methodName = self.readString(), self.readString()

        try:
            remoteInterface = remoteInterfaceRegistry[remoteInterfaceName]
        except KeyError:
            raise

        provider = remoteInterface(self.servlet, None)
        if provider is None:
            raise error.NoSuchInterface()

        try:
            methodSignature = remoteInterface[methodName]
        except KeyError:
            raise error.NoSuchMethod()

        # The argument type signatures are embedded in the token stream,
        # so the server can figure out what method to invoke if there are
        # several methods with the same name.
        #
        # We do not really case since we can only have one method per name.
        # But we read them the signatures and build annotations, to
        #
        #  (1) know how to deserialize the values, and
        #  (2) check signatures
        count = self.readInt()
        argTypeNames = [self.readString() for i in range(count)]
        argTypeInstances = [annotation.buildAnnotation(t) for t in argTypeNames]
        arguments = self.deserializeValues(argTypeInstances)

        # invoke method:
        return self.invoke(
            provider, methodSignature, arguments, response
            )

    def evaluate(self, content):
        """Evalutate request.
        
        Returns a deferred that will be invoked with a Response object.
        """
        self.prepareToRead(content.decode('utf-8'))
        response = Response(self.servlet)

        response.version, response.flags = self.readInt(), self.readInt()
        self.buildStringTable()

        if response.version > 2:
            self.moduleBaseURL = self.readString()
            self.strongName = self.readString()

        return defer.maybeDeferred(
            self._evaluate1, response
            ).addErrback(self._ebInvoke, response)


class _ServiceServlet:
    """Servlet.

    @cvar remoteInterfaces: Dictionary that map from client-side interface name
        to serverside interface class.
    """

    def processRequest(self, content):
        """Process request.

        Returns a deferred that will be invoked with the result (as a
        string) that should be sent back to the client.
        """
        return Request(self).evaluate(content)
