from zope.interface import implements, Interface, Attribute
from xtwisted.gwt import annotation, igwt, error, gwttypes
from twisted.trial import unittest


class ChangeType(gwttypes.ObjectType):
    __remote_name__ = 'test.Change'
    
    s = annotation.RemoteAttribute(gwttypes.strType(), "s")
    abc = annotation.RemoteAttribute(gwttypes.longType(), "abc")
    foo = annotation.RemoteAttribute(gwttypes.intType(), "foo")


class Change(object):
    """My simple type.
    """
    gwttypes.instanceClassOf(ChangeType)

    def __init__(self):
        pass


class RegisterTest(unittest.TestCase):
    """Test register mechanisms.
    """

    def test_lookupByRemoteName(self):
        """Verify that a type can be looked up using the remote name.
        """
        typeClass = annotation.getTypeClassByTypeName(
            'test.Change'
            )
        self.assertTrue(typeClass is not None)
 
    def test_getTypeName(self):
        """Verify that an instance of the type declaration has a getTypeName
        method.
        """
        self.assertEquals(ChangeType().getTypeName(),
                          'test.Change')

    def test_getSignature(self):
        """Verify that an instance of the type declration has a getSignature
        method.
        """
        self.assertTrue(ChangeType().getSignature(0) is not '')
    
    def test_superType(self):
        """Verify that the type has a super type.
        """
        self.assertTrue(ChangeType().superType is not None)
    
    def test_adaptToIType(self):
        """Verify that an instance can be adopted to IType.
        """
        typeInstance = igwt.IType(Change())

    def test_instanceBuilder(self):
        """Verify that an instance can be built from a type.
        """
        instance = igwt.IInstanceFactory(ChangeType()).buildInstance()
        self.assertTrue(instance is not None)
        self.assertTrue(isinstance(instance, Change))
    
    def test_correctSignature(self):
        sig = annotation.generateSignature(ChangeType())
        self.assertEquals(sig, 1572520470)

