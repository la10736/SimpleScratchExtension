from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import logging
import threading
import weakref
from scratch import components
from scratch.cgi import CGI
from scratch.components import SensorFactory, CommandFactory

__author__ = 'michele'

EXTENSION_DEFAULT_ADDRESS = "0.0.0.0"
EXTENSION_DEFAULT_PORT = 0


class ExtensionDefinition():
    """Contiene la descrizione di una estensione con i descrittore. Di fatto è una
    classe astratta: la sua implementazione es' la factory per costruire le estensioni
    """
    _names = {}

    @staticmethod
    def _register_name(name, ed):
        if name in ExtensionDefinition._names:
            raise ValueError("ExtensionDefinition named '{}' still exist".format(name))
        ExtensionDefinition._names[name] = ed

    @staticmethod
    def _unregister_all():
        ExtensionDefinition._names = {}

    @staticmethod
    def registered():
        return set(ExtensionDefinition._names.keys())

    @staticmethod
    def get_registered(name):
        return ExtensionDefinition._names[name]

    def __init__(self, name, description=None):
        """
        Exstensions descriptor.
        :param name: the descriptor' s  name (unique)
        :param description: The text description. If None will be equal to name
        """
        self._name = name
        self._description = description if description is not None else name
        self._components = {}
        self._register_name(name, self)


    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def components(self):
        return self._components.values()

    def get_component(self, name):
        return self._components[name]

    def _check_components(self, *components):
        for c in components:
            try:
                _ = c.name
            except AttributeError:
                raise TypeError("I componenti devono avere almeno un nome")

    def _check_if_already_in(self, *components):
        for c in components:
            if c.name in self._components and not c is self._components[c.name]:
                raise ValueError("Il componente dal nome {} esiste gia'".format(c.name))

    def _register_components(self, *components):
        self._check_components(*components)
        self._check_if_already_in(*components)
        self._components.update({c.name: c for c in components})

    def _deregister_components(self, *components):
        for component in components:
            del self._components[component.name]

    def _create_and_register(self, kclass, *args, **kwargs):
        c = kclass(self, *args, **kwargs)
        self._register_components(c)
        return c

    def add_sensor(self, name, value="", description=None):
        """Create and register a sensor description"""
        return self._create_and_register(SensorFactory, name=name, default=value, description=description)

    def add_command(self, name, default=(), description=None, **kwargs):
        """Create and register a command description"""
        return self._create_and_register(CommandFactory, name=name, default=default, description=description,
                                         **kwargs)

    def get_component_info(self, name):
        return self._components[name]


class ExtensionGroup():
    """A set of extension that work in team."""

    def __init__(self, factory, name, *extensions):
        """ Create a group of extension.

        :param factory: The factory that create the extensions
        :param name: The name of the Group
        :param extensions: the extensions in the group (cannot be changed) must be at least one
        """
        self.__factory = factory
        self.__name = name
        if not len(extensions):
            raise ValueError("A group must contain at least one extension")
        for e in extensions:
            e.define_group(self)
        self.__extensions = weakref.WeakSet(extensions)

    @property
    def extensions(self):
        return self.__extensions.copy()

    @property
    def name(self):
        return self.__name

    @property
    def factory(self):
        return self.__factory

    def start(self):
        for e in self.__extensions:
            e.start()

    def stop(self):
        for e in self.__extensions:
            e.stop()

    @property
    def running(self):
        return all([e.running for e in self.__extensions])


class ExtensionFactory():
    """The factory object are "immutable" because do not expose any method to change how create extension object.
    Moreover a factory contain a dictionary of his created exstension.
    """
    __anonymous = "anonymous"
    __registered = {}

    @staticmethod
    def __register(obj):
        if obj.__name is None:
            return
        if obj.__name in ExtensionFactory.__registered:
            raise ValueError("Factory named {} already exist".format(obj.__name))
        ExtensionFactory.__registered[obj.__name] = obj

    @staticmethod
    def deregister_all():
        ExtensionFactory.__registered = {}

    @staticmethod
    def registered(name=None):
        if name is None:
            return frozenset(ExtensionFactory.__registered.keys())
        return ExtensionFactory.__registered.get(name, None)

    @staticmethod
    def deregister(name):
        del ExtensionFactory.__registered[name]

    def __init__(self, name=None):
        """
        Can be anonymous or registered. None named factory are anonymous,
        :param name: the name of the factory. None are the anonymous element (not registered and volatile)
        """
        self.__name = name
        self.__register(self)
        self.__extensions = weakref.WeakSet()
        self.__groups = {}
        self.__next_index_name = 1

    @property
    def name(self):
        return self.__name if self.__name is not None else self.__anonymous

    def port_generator(self, port):
        try:
            for i in iter(port):
                yield i
            return
        except TypeError:
            pass
        while True:
            yield port
            port += 1

    def do_create(self, group_name, *args, **kwargs):
        """ Create a group of extension from the factory. The concrete factory must
         implement that method.

        :param group_name: The extensions base_name
        :param args: positional args passed to Extension Constructor
        :param kwargs: Nominal args passed to Extension Constructor
        :return: a list of extensions
        """
        raise NotImplementedError("You must implement it in your sub classes")

    def __register_extensions(self, *extensions):
        for e in extensions:
            e.define_factory(self)
            self.__extensions.add(e)

    @property
    def groups(self):
        return self.__groups.keys()

    def group(self, key):
        return self.__groups[key]

    def _search_next_index_group_name(self):
        while str(self.__next_index_name) in self.__groups:
            self.__next_index_name += 1

    def create(self, group_name=None, *args, **kwargs):
        if group_name is not None and group_name in self.__groups:
            raise ValueError("Group name already present")
        gen = False
        if group_name is None:
            self._search_next_index_group_name()
            group_name = str(self.__next_index_name)
            gen = True
        ret = extensions = self.do_create(group_name, *args, **kwargs)
        self.__register_extensions(*extensions)
        if len(extensions) > 1:
            ret = self.__groups[group_name] = ExtensionGroup(self, group_name, *extensions)
            if gen:
                self.__next_index_name += 1
        return ret

    @property
    def extensions(self):
        return self.__extensions.copy()


class Extension():
    """The extension: create by a ExtensionDefinition it binds the server that respond to
    scratch query. Expose method to get the components.
    """

    class HTTPHandler(BaseHTTPRequestHandler):
        @property
        def context(self):
            return self.server._context()

        def _get_cgi(self):
            return self.context._get_cgi(self.path)

        def _set_headers_from_cgi(self, cgi):
            if cgi.headers:
                for k, v in cgi.headers.items():
                    self.send_header(k, v)
            else:
                self.send_header("Content-type", "text/html")

        def do_HEAD(self):
            cgi = self._get_cgi()
            if not cgi:
                self.send_response(404)
            else:
                self.send_response(200)
                self._set_headers_from_cgi(cgi=cgi)
            self.end_headers()

        def do_GET(self):
            data = ''
            cgi = self._get_cgi()
            if not cgi:
                self.send_response(404)
            else:
                try:
                    data = cgi(self)
                except Exception as e:
                    logging.exception(e)
                    self.send_response(500)
                else:
                    self.send_response(200)
                    self._set_headers_from_cgi(cgi=cgi)

            self.end_headers()
            self.wfile.write(bytes(data, "utf-8"))

    _names = {}

    @staticmethod
    def _register_name(name, ed):
        if name in Extension._names:
            raise ValueError("Exstension named '{}' still exist".format(name))
        Extension._names[name] = ed

    @staticmethod
    def _unregister_all():
        Extension._names = {}

    @staticmethod
    def registered():
        return set(Extension._names.keys())

    @staticmethod
    def get_registered(name):
        return Extension._names[name]

    def __init__(self, name, address=EXTENSION_DEFAULT_ADDRESS, port=EXTENSION_DEFAULT_PORT):
        self._name = name
        self._address = address
        self._port = port
        self._components = {}
        self._init_components()
        self._server_thread = None
        self._http = HTTPServer((address, port), Extension.HTTPHandler)
        self._http._context = weakref.ref(self)
        self._cgi_map = {"/poll": {"cgi": "_poll_cgi"},
                         "/crossdomain.xml": {"cgi": "_crossdomain_xml",
                                              "headers": {"Content-type": "text/xml"}},
                         "/reset_all": {"cgi": "reset"}}
        self._register_name(name, self)
        self._factory = None
        self._group = None

    def do_init_components(self):
        """The method to override to initialize the components and return it"""
        logging.warning("You should implement that method in your concrete class")
        return []

    def _init_components(self):
        self._components = {c.name: c for c in self.do_init_components()}

    def start(self):
        if self._server_thread is None:
            self._server_thread = threading.Thread(name="%s HTTP Server" % self.name, target=self._http.serve_forever)
            self._server_thread.daemon = True
            self._server_thread.start()

    def stop(self):
        if self._server_thread is None:
            return
        self._http.shutdown()
        self._server_thread.join()
        self._server_thread = None

    @property
    def running(self):
        return self._server_thread is not None

    @property
    def name(self):
        return self._name

    @property
    def address(self):
        return self._http.server_name

    @property
    def port(self):
        return self._http.server_port

    @property
    def components(self):
        return self._components.values()

    @property
    def components_name(self):
        return self._components.keys()

    def get_component(self, name):
        return self._components[name]

    @property
    def description(self):
        ret = {"extensionName": self.name,
               "extensionPort": self.port,
               "blockSpecs": [c.definition for c in self.components]
        }
        return ret

    @property
    def factory(self):
        return self._factory

    def define_factory(self, factory):
        if self._factory is not None and not factory is self._factory:
            raise RuntimeError("Factory can be defined just once")
        self._factory = factory

    @property
    def group(self):
        return self._group

    def define_group(self, group):
        if self._group is not None and not group is self._group:
            raise RuntimeError("Group can be defined just once")
        self._group = group

    def poll(self):
        return {c.name: c.get() for c in self.components if c.type == 'r'}

    def _poll_cgi(self, handler):
        return self.poll_dict_render(self.poll())

    @staticmethod
    def poll_dict_render(vals):
        sio = io.StringIO()
        for v, k in vals.items():
            sio.write('%s %s\n' % (v, str(k)))
        return sio.getvalue()

    def _crossdomain_xml(self, request):
        return """<cross-domain-policy>
<allow-access-from domain="*" to-ports="{}"/>
</cross-domain-policy>""".format(self.port)

    def do_reset(self, request=None):
        "Method to override to and application specific reset actions"
        pass

    def reset(self, request=None):
        for c in self.components:
            c.reset(request)
        self.do_reset(request)
        return ""

    def _resolve_local_cgi(self, path):
        try:
            el = self._cgi_map[path]
        except KeyError:
            return None
        else:
            cgi = getattr(self, el["cgi"], None)
            headers = el.get("headers", {})
            return CGI(cgi, headers)

    def _resolve_components_cgi(self, path):
        for c in self.components:
            cgi = c.get_cgi(path)
            if cgi is not None:
                return cgi

    def _get_cgi(self, path):
        cgi = self._resolve_components_cgi(path)
        if cgi is not None:
            return cgi
        return self._resolve_local_cgi(path)

class ExtensionBase(Extension):
    """The extension created by a ExtensionDefinition."""

    def __init__(self, definition, name, address=EXTENSION_DEFAULT_ADDRESS, port=EXTENSION_DEFAULT_PORT):
        self.__components_definition = definition.components
        super(ExtensionBase, self).__init__(name=name, address=address, port=port)

    def do_init_components(self):
        return [c.create(self) for c in self.__components_definition]
