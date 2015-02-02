import logging
import threading
import urllib.parse
import weakref
from scratch.cgi import CGI

__author__ = 'michele'


def extract_arg(arg, kwargs, default=None):
    v = default
    if arg in kwargs:
        v = kwargs[arg]
        del kwargs[arg]
    return v


class BlockFactory():
    type = "u"  # unknown
    block_constructor = None  # Abstract
    cb_arg = None  # Abstract

    def __init__(self, ed, name, description=None, **menudict):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of the block
        :param description: the description of the block. If None the description is equal to the name
        :return:
        """
        self._ed = weakref.ref(ed) if ed is not None else None
        self._name = name
        self._menu_dict = menudict
        self._description = description if description is not None else self._name

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
    def definition(self):
        return [self.type, self.description, self.name]

    @property
    def menu_dict(self):
        return self._menu_dict.copy()


    def create(self, extension, *args, **kwargs):
        cb = extract_arg(self.cb_arg, kwargs) if self.cb_arg is not None else None
        b = self.block_constructor(extension, self, *args, **kwargs)
        if cb is not None:
            setattr(b, self.cb_arg, cb)
            b.do_read = cb
        return b


class Block():
    """Abstract Extension components"""

    def __init__(self, extension, info, value=None):
        self._ex = weakref.ref(extension)
        self._info = info
        self._value = value if value is not None else info.default
        self._lock = threading.Lock()

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

    def reset(self, request=None):
        pass

    def get_cgi(self, path):
        return None


class Sensor(Block):
    """Sensor sono gli elementi base delle estensioni: Vengono costruiti in base a una
    SensorFactory (del quale fanno da proxy per type, name, description es definition) es
    espongono i metodi get() es set() per leggere es scrivere il valore.
    Se il sensore implementa il metodo do_read() viene invocato per impostare il vaolre e
    ritornarlo.
    """

    @staticmethod
    def create(extension, name, default=None, description=None, **kwargs):
        do_read = extract_arg("do_read", kwargs)
        factory = SensorFactory(ed=None, name=name, default=default, description=description, **kwargs)
        return factory.create(extension=extension, do_read=do_read)

    def get(self):
        with self._lock:
            if hasattr(self, "do_read"):
                self._value = self.do_read()
            return self._value

    def set(self, value):
        with self._lock:
            self._value = value


class SensorFactory(BlockFactory):
    type = "r"  # reporters
    block_constructor = Sensor
    cb_arg = "do_read"

    def __init__(self, ed, name, default="", description=None):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of the sensor
        :param default: the default return value
        :param description: the description of the sensor. If None the description is equla to the name
        :return:
        """
        super().__init__(ed=ed, name=name, description=description)
        self._default = default

    @property
    def default(self):
        return self._default


class Command(Block):
    """Command components perform actions and return. User application should override
    the method do_command(*args) to do the real work.
    the property value return last value (or tuple if it haa more argument) and value_dict
    the last value in a dictionary.
    """

    @staticmethod
    def create(extension, name, default=(), description=None, **kwargs):
        do_command = extract_arg("do_command", kwargs)
        factory = CommandFactory(ed=None, name=name, default=default, description=description, **kwargs)
        return factory.create(extension=extension, do_command=do_command)

    def __init__(self, extension, info):
        super().__init__(extension=extension, info=info)
        self._value = None

    @property
    def value(self):
        with self._lock:
            if self._value is None:
                return None
            if len(self._value) == 1:
                return self._value[0]
            return self._value

    def command(self, *args):
        logging.info("command {} = {}".format(self.name, args))
        if hasattr(self, "do_command"):
            self.do_command(*args)
        with self._lock:
            self._value = args

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


class CommandFactory(BlockFactory):
    type = " "  # no blocking commands
    block_constructor = Command
    cb_arg = "do_command"

    def __init__(self, ed, name, default=(), description=None, **kwargs):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of command
        :param defualt: the tuple of default values (used to describe component)
        :param description: the description of the sensor. If None the description is equla to the name
        :param kwargs: the menus entry lists
        :return:
        """
        super().__init__(ed=ed, name=name, description=description, **kwargs)
        self._default = default
        if not self._check_description():
            raise ValueError("Wrong description and/or values/menus")

    def _check_description(self):
        return True

    @property
    def default(self):
        return self._default

    @property
    def definition(self):
        return super().definition + [d for d in self._default]


class HatFactory(BlockFactory):
    type = "h"  # hat
