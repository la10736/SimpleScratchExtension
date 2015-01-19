import logging
import threading
import urllib.parse
import weakref
from scratch.cgi import CGI

__author__ = 'michele'


class SensorFactory():
    type = "r"  # reporters

    def __init__(self, ed, name, default="", description=None):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of the sensor
        :param default: the default return value
        :param description: the description of the sensor. If None the description is equla to the name
        :return:
        """
        self._ed = weakref.ref(ed) if ed is not None else None
        self._name = name
        self._description = description if description is not None else self._name
        self._default = default

    @property
    def ed(self):
        return self._ed() if self._ed is not None else None

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def default(self):
        return self._default

    @property
    def definition(self):
        return [self.type, self.description, self.name]

    def create(self, extension, *args, **kwargs):
        return Sensor(extension, self, *args, **kwargs)


class Sensor():
    """Sensor sono gli elementi base delle estensioni: Vengono costruiti in base a una
    SensorFactory (del quale fanno da proxy per type, name, description es definition) es
    espongono i metodi get() es set() per leggere es scrivere il valore.
    Se il sensore implementa il metodo do_read() viene invocato per impostare il vaolre e
    ritornarlo.
    """

    def __init__(self, extension, info, value=None):
        self._ex = weakref.ref(extension)
        self._info = info
        self._value = value if value is not None else info.default
        self.__lock = threading.Lock()

    @property
    def extension(self):
        return self._ex()

    @property
    def info(self):
        return self._info

    @property
    def type(self):
        return self.info.type

    @property
    def name(self):
        return self.info.name

    @property
    def description(self):
        return self.info.description

    @property
    def definition(self):
        return self.info.definition

    def get(self):
        with self.__lock:
            if hasattr(self, "do_read"):
                self._value = self.do_read()
            return self._value

    def set(self, value):
        with self.__lock:
            self._value = value

    def reset(self, request=None):
        pass

    def get_cgi(self, path):
        return None


class CommandFactory():
    type = " "  # no blocking commands

    def __init__(self, ed, name, default=(), description=None, **kwargs):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of command
        :param defualt: the tuple of default values (used to describe component)
        :param description: the description of the sensor. If None the description is equla to the name
        :param kwargs: the menus entry lists
        :return:
        """
        self._ed = weakref.ref(ed) if ed is not None else None
        self._name = name
        self._description = description if description is not None else self._name
        self._default = default
        self._menu_dict = kwargs
        if not self._check_description():
            raise ValueError("Wrong description and/or values/menus")

    def _check_description(self):
        return True

    @property
    def ed(self):
        return self._ed() if self._ed else None

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def default(self):
        return self._default

    @property
    def menu_dict(self):
        return self._menu_dict.copy()

    @property
    def definition(self):
        return [self.type, self.description, self.name] + [d for d in self._default]

    def create(self, extension, *args, **kwargs):
        return Command(extension, self, *args, **kwargs)


class Command():
    """Command components perform actions and return. User application should override
    the method do_command(*args) to do the real work.
    the property value return last value (or tuple if it haa more argument) and value_dict
    the last value in a dictionary.
    """

    def __init__(self, extension, info):
        self._ex = weakref.ref(extension)
        self._info = info
        self._value = None
        self.__lock = threading.Lock()

    @property
    def extension(self):
        return self._ex()

    @property
    def info(self):
        return self._info

    @property
    def type(self):
        return self.info.type

    @property
    def name(self):
        return self.info.name

    @property
    def description(self):
        return self.info.description

    @property
    def definition(self):
        return self.info.definition

    @property
    def value(self):
        with self.__lock:
            if self._value is None:
                return None
            if len(self._value) == 1:
                return self._value[0]
            return self._value

    def command(self, *args):
        logging.info("command {} = {}".format(self.name, args))
        if hasattr(self, "do_command"):
            self.do_command(*args)
        with self.__lock:
            self._value = args

    def reset(self, request=None):
        pass

    @staticmethod
    def _get_request_data(path):
        els = path[1:].split("/")
        els = [e for e in map(lambda url: urllib.parse.unquote(url), els)]
        return els[0], els[1:]

    def _cgi(self, request):
        _name, args = self._get_request_data(request.path)
        self.command(*args)
        return ""

    def get_cgi(self, path):
        if not path.startswith("/"):
            return None
        name, _args = self._get_request_data(path)
        if name == self.name:
            return CGI(self._cgi)


class Head():
    pass