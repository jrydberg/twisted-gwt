import types, inspect
from zope.interface import interface, providedBy, implements, Attribute


class RemoteInterfaceClass(interface.InterfaceClass):
    """This metaclass lets RemoteInterfaces be a lot like Interfaces. The
    methods are parsed differently (PB needs more information from them than
    z.i extracts, and the methods can be specified with a RemoteMethodSchema
    directly).

    RemoteInterfaces can accept the following additional attribute::

     __remote_name__: can be set to a string to specify the globally-unique
                      name for this interface. This should be a URL in a
                      namespace you administer. If not set, defaults to the
                      short classname.

    RIFoo.names() returns the list of remote method names.
    """

    def __init__(self, iname, bases=(), attrs=None, __module__=None):
        if attrs is None:
            interface.InterfaceClass.__init__(self, iname, bases, attrs, __module__)
            return

        # parse (and remove) the attributes that make this a RemoteInterface
        # and let the normal InterfaceClass do its thing
        rname, remote_attrs = self._parseRemoteInterface(iname, attrs)
        interface.InterfaceClass.__init__(self, iname, bases, attrs,
                                          __module__)

        # XXX: from foolscap:
        # now add all the remote methods that InterfaceClass would have
        # complained about. This is really gross, and it really makes me
        # question why we're bothing to inherit from z.i.Interface at all. I
        # will probably stop doing that soon, and just have our own
        # meta-class, but I want to make sure you can still do
        # 'implements(RIFoo)' from within a class definition.

        a = getattr(self, "_InterfaceClass__attrs") # the ickiest part
        a.update(remote_attrs)
        self.__remote_name__ = rname

        registerRemoteInterface(self, rname)

    def _parseRemoteInterface(self, iname, attrs):
        remote_attrs = {}
        remote_name = attrs.get("__remote_name__", iname)

        # and see if there is a __remote_name__ . We delete it because
        # InterfaceClass doesn't like arbitrary attributes
        if attrs.has_key("__remote_name__"):
            del attrs["__remote_name__"]

        names = [name for name in attrs.keys()
                 if ((type(attrs[name]) == types.FunctionType and
                      not name.startswith("_")))]

        for name in names:
            remote_attrs[name] = RemoteMethod(name, self, attrs[name])
            del attrs[name]

        return remote_name, remote_attrs


RemoteInterface = RemoteInterfaceClass("RemoteInterface",
                                       __module__="zope.interface")


class RemoteMethod:
    """Method that can be invoked from the client-side.
    """
    
    def __init__(self, name, interface, func):
        self.name = name
        self.interface = interface
        self.func = func
        argcount = self.func.func_code.co_argcount
        self.returnTypeSignature = func(*([None] * argcount))


class DuplicateRemoteInterfaceError(Exception):
    pass


class RemoteInterfaceRegistry:
    """Registry of the mapping between remote name and the interface.
    """

    def __init__(self):
        self.registry = {}

    def register(self, interfaceClass, rname):
        if rname in self.registry:
            DuplicateRemoteInterfaceError(
                "%s already in registry", rname
                )
        self.registry[rname] = interfaceClass
    
    def __getitem__(self, rname):
        """Return remote interface by name.
        """
        return self.registry[rname]


remoteInterfaceRegistry = RemoteInterfaceRegistry()
registerRemoteInterface = remoteInterfaceRegistry.register
