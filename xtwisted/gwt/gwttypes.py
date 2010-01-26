from zope.interface import implements, Interface, advice
from xtwisted.gwt import annotation, igwt
from twisted.python import components


class RemoteType(type):
    """Base type for remote types.

    Use this as a meta class to automaticly register types.

    Can be used together with the instanceFactoryFor class
    advisor to associate a type with an instance factory.
    """
    def __new__(meta, className, bases, attributes):
        # start out by creating the actual class.
        klass = type.__new__(meta, className, bases, attributes)
        #print "attrs", repr(attributes)
        #print "bases", bases
        #print "register", className
        names = list()
        if not '__remote_name__' in attributes:
            raise Exception("remote name not specified")
        remote_name = attributes['__remote_name__']
        superType = None
        if len(bases) != 0:
            superClassNames = list()
            for base in bases:
                if hasattr(base, '__remote_name__'):
                    superClassNames.append(base.__remote_name__)
            if len(superClassNames) > 1:
                raise Exception("only one base allowed")
            #print "super class names", superClassNames
            if superClassNames:
                superClass = annotation.getTypeClassByTypeName(
                    superClassNames[0]
                    )
                superType = superClass()
        #print "superClass", superType
        klass.superType = superType
        def getTypeName():
            return remote_name
        klass.getTypeName = staticmethod(getTypeName)
        annotation.registerTypeClass(klass)
        # pick up all remote attributes:
        for attrname, attrval in attributes.iteritems():
            if isinstance(attrval, annotation.RemoteAttribute):
                names.append(attrname)
        # fake a zope interface by providing the methods that we
        # require: names and get.
        class protocolClass:
            @staticmethod
            def names():
                return names
            @staticmethod
            def get(name):
                return getattr(protocolClass, name)
        for name in names:
            setattr(protocolClass, name, attributes[name])
        annotation.typeProtocolRegistry.register(
            klass, protocolClass
            )
        return klass


def instanceClassOf(typeClass):
    """Signal that the class suite is an instance factory for the
    specified protocol class.

    The instance class must have a constructor that accepts no arguments.
    """
    def callback(instanceClass):
        class InstanceFactory:
            def __init__(self, protocolClass):
                pass
            def buildInstance(self):
                return instanceClass()
        components.registerAdapter(InstanceFactory, typeClass, 
                                   igwt.IInstanceFactory)
        annotation.registerTypeAdapter(typeClass, instanceClass)
        return instanceClass
    advice.addClassAdvisor(callback)


class ObjectType(annotation.Type):
    """Base type for everything.
    """
    __remote_name__ = 'java.lang.Object'
    __metaclass__ = RemoteType

    def __repr__(self):
        return "<Type instance %s:%s>" % (
            self.__class__.__name__,
            self.__remote_name__
            )


intType = annotation.Integer
longType = annotation.Long
shortType = annotation.Short
voidType = annotation.Void
arrayType = annotation.Array
strType = annotation.String
HashMapType = annotation.HashMap
ArrayListType = annotation.ArrayList
DateType = annotation.Date


# Singleton for void:
void = voidType()


class ThrowableType(ObjectType):
    __remote_name__ = 'java.lang.Throwable'


class ExceptionType(ThrowableType):
    __remote_name__ = 'java.lang.Exception'


class RuntimeExceptionType(ExceptionType):
    __remote_name__ = 'java.lang.RuntimeException'
