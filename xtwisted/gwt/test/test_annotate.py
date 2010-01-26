from zope.interface import implements, Interface, Attribute
from xtwisted.gwt import annotation, igwt, error
from twisted.trial import unittest
from twisted.python.components import Adapter, registerAdapter


class IChange(Interface):
    s = annotation.RemoteAttribute(annotation.String(), "s")
    abc = annotation.RemoteAttribute(annotation.Long(), "abc")
    foo = annotation.RemoteAttribute(annotation.Integer(), "foo")

class Change:
    """A simple type.
    """
    implements(IChange)


class ChangeType(annotation.Object):
    superType = annotation.Object()

    def getTypeName(self):
        """Return type name.
        """
        return 'test.Change'

annotation.registerTypeProtocol(ChangeType, IChange)

# register the type so that adaptation to IType works
annotation.registerTypeAdapter(ChangeType, Change)


class IFuture(IChange):
    baz =  annotation.RemoteAttribute(annotation.Short(), "baz")
    xy = annotation.RemoteAttribute(annotation.Integer(), "xy")


class FutureType(annotation.Object):
    superType = ChangeType()

    def getTypeName(self):
        """Return type name.
        """
        return 'test.Future'


annotation.registerTypeProtocol(FutureType, IFuture)


class SignatureTest(unittest.TestCase):
    """Tests for generation of type signatures.
    """

    def test_javaLangString(self):
        """Verify that the signature for java.lang.String is generated
        correctly.
        """
        sig = annotation.generateSignature(annotation.String())
        self.assertEquals(sig, 2004016611)

    def test_javaUtilHashMap(self):
        """Verify that the signature for java.util.HashMap is generated
        correctly.
        """
        sig = annotation.generateSignature(annotation.HashMap())
        self.assertEquals(sig, 962170901)

    def test_hashMapArray(self):
        """Verify that the signature for an array of java.util.HashMap is
        generated correctly.
        """
        sig = annotation.generateSignature(annotation.Array(annotation.HashMap()))
        self.assertEquals(sig, 3177835830)
        
    def test_intArray(self):
        """Verify that the signature for an array of integers
        is generated correctly.
        """
        sig = annotation.generateSignature(annotation.Array(annotation.Integer()))
        self.assertEquals(sig, 2970817851)
    
    def test_genericCustomFieldSerializer(self):
        """Verify that the generic serializer generates correct
        signatures
        """
        sig = annotation.generateSignature(ChangeType())
        self.assertEquals(sig, 1572520470)

    def test_inheritedGenericCustomFieldSerializer(self):
        """Verify that the generic serializer supports inherited types.
        """
        sig = annotation.generateSignature(FutureType())
        self.assertEquals(sig, 2439950297)

    def test_IncompatibleRemoteServiceException(self):
        typeInstance = igwt.IType(error.IncompatibleRemoteServiceException())
        sig = annotation.generateSignature(typeInstance)
        self.assertEquals(sig, 3936916533)


class AdaptationTest(unittest.TestCase):
    
    def test_IType(self):
        """Verify that types that are registered with registerType
        can be adapted.
        """
        t = igwt.IType(Change())
        self.assertTrue(isinstance(t, ChangeType))


class BuilderTest(unittest.TestCase):

    def setUp(self):
        self.builder = annotation.AnnotationBuilder()
    
    def test_buildInteger(self):
        """Test that an integer can be built from a type signature.
        """
        typeInstance = self.builder.buildAnnotation('I')
        self.assertTrue(isinstance(typeInstance, annotation.Integer))

    def test_buildHashMap(self):
        """Test that a HashMap can be built.
        """
        typeInstance = self.builder.buildAnnotation('java.util.HashMap')
        self.assertTrue(isinstance(typeInstance, annotation.HashMap))

    def test_buildArrayOfInteger(self):
        """Test that an array of integers can be built.
        """
        typeInstance = self.builder.buildAnnotation('[I')
        self.assertTrue(isinstance(typeInstance, annotation.Array))
        compoundType = typeInstance.compoundType
        self.assertTrue(isinstance(compoundType, annotation.Integer))

    def test_buildArrayOfString(self):
        """Test that an array of strings can be built.
        """
        typeInstance = self.builder.buildAnnotation('[Ljava.lang.String;/2600011424')
        self.assertTrue(isinstance(typeInstance, annotation.Array))
        compoundType = typeInstance.compoundType
        self.assertTrue(isinstance(compoundType, annotation.String))

    def test_badSignature(self):
        """Test that the signature is verified.
        """
        self.assertRaises(
            error.BadSignature,
            self.builder.buildAnnotation, 'java.util.HashMap/123'
            )

