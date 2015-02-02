from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import logging
import threading
import weakref
from scratch.cgi import CGI
from scratch.components import SensorFactory, CommandFactory, HatFactory

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

    def add_hat(self, name, description=None, **kwargs):
        """Create and register a hat description"""
        return self._create_and_register(HatFactory, name=name, description=description, **kwargs)


    def get_component_info(self, name):
        return self._components[name]


class Extension():
    """The object that contains components and will be served from ExtensionService()"""

    def __init__(self):
        self._components = {}
        self._init_components()
        self._factory = None

    @property
    def factory(self):
        return self._factory

    def define_factory(self, factory):
        if self._factory is not None and not factory is self._factory:
            raise RuntimeError("Factory can be defined just once")
        self._factory = factory

    def do_init_components(self):
        """The method to override to initialize the components and return it"""
        logging.warning("You should implement that method in your concrete class")
        return []

    def _init_components(self):
        self._components = {c.name: c for c in self.do_init_components()}

    @property
    def components(self):
        return self._components.values()

    @property
    def components_name(self):
        return self._components.keys()

    def get_component(self, name):
        return self._components[name]

    def do_reset(self):
        "Method to override to and application specific reset actions"
        pass

    def reset(self):
        for c in self.components:
            c.reset()
        self.do_reset()

    def poll(self):
        values = {c.name: c.get() for c in self.components if c.type == 'r'}
        values.update({c.name: c.state for c in self.components if c.type == 'h'})
        return values

    @property
    def block_specs(self):
        return [c.definition for c in self.components]


class ExtensionService():
    """The extension service: create by a Extension object it binds the server that respond to
    Scratch query. Expose method to get the extension, start and stop the service.
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
        if name in ExtensionService._names:
            raise ValueError("Exstension named '{}' still exist".format(name))
        ExtensionService._names[name] = ed

    @staticmethod
    def _unregister_all():
        ExtensionService._names = {}

    @staticmethod
    def registered():
        return set(ExtensionService._names.keys())

    @staticmethod
    def get_registered(name):
        return ExtensionService._names[name]

    def __init__(self, extension, name, address=EXTENSION_DEFAULT_ADDRESS, port=EXTENSION_DEFAULT_PORT):
        """Create a service that serve Scracth 2 requests for an extension object.
        """
        self._extension = extension
        self._name = name
        self._address = address
        self._port = port
        self._server_thread = None
        self._http = HTTPServer((address, port), ExtensionService.HTTPHandler)
        self._http._context = weakref.ref(self)
        self._cgi_map = {"/poll": {"cgi": "_poll_cgi"},
                         "/crossdomain.xml": {"cgi": "_crossdomain_xml",
                                              "headers": {"Content-type": "text/xml"}},
                         "/reset_all": {"cgi": "reset"}}
        self._register_name(name, self)

    @property
    def extension(self):
        return self._extension

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
    def description(self):
        ret = {"extensionName": self.name,
               "extensionPort": self.port,
               "blockSpecs": self._extension.block_specs
        }
        return ret

    def _poll_cgi(self, handler):
        return self.poll_dict_render(self._extension.poll())

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

    def reset(self, request=None):
        self._extension.reset()
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
        for c in self._extension.components:
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

    def __init__(self, definition):
        self.__components_definition = definition.components
        super(ExtensionBase, self).__init__()

    def do_init_components(self):
        return [c.create(self) for c in self.__components_definition]


class ExtensionServiceBase(ExtensionService):
    """The extension service created by a ExtensionDefinition."""

    def __init__(self, definition, name, address=EXTENSION_DEFAULT_ADDRESS, port=EXTENSION_DEFAULT_PORT):
        super(ExtensionServiceBase, self).__init__(extension=ExtensionBase(definition=definition), name=name,
                                                   address=address, port=port)

