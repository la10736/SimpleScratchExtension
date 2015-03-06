import copy
import inspect
import logging
import threading
import urllib.parse
import weakref
import re
import collections

from scratch.cgi import CGI


__author__ = 'michele'


def extract_arg(arg, kwargs, default=None):
    v = default
    if arg in kwargs:
        v = kwargs[arg]
        del kwargs[arg]
    return v


def to_bool(val):
    return str(val).lower() == "true"


_description_parser = re.compile("%(s|n|b|m\.[^\s.]+|d\.[^\s.]+)")


class _Checker:
    def __init__(self, menu, def_mapper=None):
        self._menu = menu
        if def_mapper is not None:
            self._def_mapper = def_mapper

    def _def_mapper(self, v):
        raise KeyError("Menu doesn't contain key {}".format(v))


class _CheckerMapper(_Checker):
    def __call__(self, v):
        try:
            return self._menu[v]
        except KeyError:
            return self._def_mapper(v)

    @property
    def elements(self):
        return set(self._menu.keys())


class _CheckerContainer(_Checker):
    def __call__(self, v):
        if v in self._menu:
            return v
        else:
            return self._def_mapper(v)

    @property
    def elements(self):
        return set(self._menu.copy())


def _create_menu_checker(menu):
    if isinstance(menu, collections.Mapping):
        checker = _CheckerMapper(menu)
    elif isinstance(menu, collections.Container):
        checker = _CheckerContainer(menu)
    else:
        raise TypeError("Menu must be a Mapping or Container")
    return checker

def _create_editable_menu_checker(menu):
    try:
        def_mapper = menu.get(None, str)
    except AttributeError:
        def_mapper = str

    if isinstance(menu, collections.Mapping):
        checker = _CheckerMapper(menu, def_mapper)
    elif isinstance(menu, collections.Container):
        checker = _CheckerContainer(menu, def_mapper)
    else:
        raise TypeError("Menu must be a Mapping or Container")


    return checker


def _desc_mapper(e, **kwargs):
    if e == "s":
        return str
    if e == "n":
        return float
    if e == "b":
        return to_bool
    if e.startswith("m.") or e.startswith("d."):
        mname = e[2:]
        checker_factory = _create_menu_checker if e[0] == 'm' else _create_editable_menu_checker
        try:
            menu = kwargs[mname]
            if not isinstance(menu, (collections.Mapping, collections.Container)):
                raise TypeError("Menu must be a Mapping or Container")
            return checker_factory(menu)
        except KeyError:
            raise TypeError(
                "Description contains {} menu: need a keyword args {}=<Your menu>".format(mname, mname))


def parse_description(description, **kwargs):
    ret = []

    elements = _description_parser.findall(description)
    return tuple([_desc_mapper(e, **kwargs) for e in elements])


class BlockFactory():
    type = "u"  # unknown
    block_constructor = None  # Abstract
    cb_arg = None  # Abstract

    def __init__(self, ed, name, description=None, **menus):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of the block
        :param description: the description of the block. If None the description is equal to the name
        :return:
        """
        self._ed = weakref.ref(ed) if ed is not None else None
        self._name = name
        self._menu_dict = copy.deepcopy(menus)
        self._description = description if description is not None else self._name
        self._signature = parse_description(self.description, **self._menu_dict)

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
        return b

    @property
    def signature(self):
        return self._signature

    @property
    def menus(self):
        ret = {}
        for k,c in self.menu_dict.items():
            if isinstance(c, collections.Mapping):
                ret[k] = list(c.keys())
            else:
                ret[k] = c
            ret[k].sort()
        return ret


class Block():
    def __init__(self, extension, info, value=None):
        self._ex = weakref.ref(extension)
        self._info = info
        self._value = value
        self._lock = threading.RLock()
        self._busy = set()

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
    def signature(self):
        return self.info.signature

    @property
    def busy(self):
        with self._lock:
            return self._busy.copy()

    def _busy_add(self, busy):
        with self._lock:
            self._busy.add(busy)

    def _busy_remove(self, busy):
        with self._lock:
            self._busy.discard(busy)

    def _busy_clean(self):
        with self._lock:
            self._busy = set()

    def do_reset(self):
        """Designed to override. Pay attention here you are in lock context: you just do your reset busness
         and don't touch block object."""
        pass

    def reset(self):
        with self._lock:
            self.do_reset()

    def get_cgi(self, path):
        return None

    @staticmethod
    def _get_request_data(path):
        els = path[1:].split("/")
        els = [e for e in map(lambda url: urllib.parse.unquote(url), els)]
        return els[0], els[1:]

    def _check_command_argument(self, *args):
        """ Base implementation: no cheks

        :return: None if wrong elese the arguments tuple
        """
        return args

    def poll(self):
        return {}


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

    def __init__(self, extension, info, value=None):
        v = self._get_default_value(value, info)
        super().__init__(extension, info, value=v)

    def _get_default_value(self, value=None, info=None):
        if info is None:
            info = self._info
        v = value if value is not None else info.default
        try:
            v = copy.deepcopy(v)
        except AttributeError:
            pass
        if len(info.signature) and not isinstance(v, collections.Mapping):
            v = {None: v}
        return v

    def reset(self):
        with self._lock:
            self._value = self._get_default_value()
            self.do_reset()

    @property
    def value(self):
        """Last value"""
        with self._lock:
            return self._value

    def _set_value(self, value):
        with self._lock:
            self._value = value

    def get(self):
        v = self.do_read() if hasattr(self, "do_read") else None
        with self._lock:
            if v is not None:
                self._set_value(v)
            return self._value

    def set(self, value):
        self._set_value(value)

    def poll(self):
        return {(): self.get()}


class SensorFactory(BlockFactory):
    type = "r"  # reporters
    block_constructor = Sensor
    cb_arg = "do_read"

    def __init__(self, ed, name, default="", description=None, **menus):
        """
        :param ed: The ExtensionDefinition (container)
        :param name: the name of the sensor
        :param default: the default return value
        :param description: the description of the sensor. If None the description is equla to the name
        :param menu: menues
        :return:
        """
        super().__init__(ed=ed, name=name, description=description, **menus)
        self._default = default

    @property
    def default(self):
        return self._default


class BooleanBlock(Sensor):
    @staticmethod
    def create(extension, name, default=None, description=None, **kwargs):
        do_read = extract_arg("do_read", kwargs)
        factory = BooleanFactory(ed=None, name=name, default=default, description=description, **kwargs)
        return factory.create(extension=extension, do_read=do_read)

    def get(self):
        return "true" if super().get() else "false"

    def set(self, value=True):
        super().set(bool(value))

    def clear(self):
        """Clear the value"""
        self.set(False)


class BooleanFactory(SensorFactory):
    type = "b"  # reporters
    block_constructor = BooleanBlock


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

    def _cgi(self, request):
        _name, args = self._get_request_data(request.path)
        args = self._check_command_argument(*args)
        self.command(*args)
        return ""

    def get_cgi(self, path):
        if not path.startswith("/"):
            return None
        name, args = self._get_request_data(path)
        args = self._check_command_argument(*args)
        if args is None:
            return None
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


class Hat(Block):
    """Hat blocks return True to raise a event. User application should call flag() to
    raise event or override do_flag() method that return True when want to raise event.
    """

    @staticmethod
    def create(extension, name, description=None, **kwargs):
        do_flag = extract_arg("do_flag", kwargs)
        factory = HatFactory(ed=None, name=name, description=description, **kwargs)
        return factory.create(extension=extension, do_flag=do_flag)

    def __init__(self, extension, info):
        super().__init__(extension=extension, info=info, value=False)

    @property
    def state(self):
        try:
            return bool(getattr(self, "do_flag")())
        except AttributeError:
            pass
        with self._lock:
            r = self._value
            self._value = False
            return r

    def flag(self):
        with self._lock:
            self._value = True

    def reset(self):
        with self._lock:
            self._value = False
            self.do_reset()


class HatFactory(BlockFactory):
    type = "h"  # hat
    block_constructor = Hat
    cb_arg = "do_flag"


class WaiterCommand(Command):
    @staticmethod
    def create(extension, name, default=(), description=None, **kwargs):
        do_command = extract_arg("do_command", kwargs)
        factory = WaiterCommandFactory(ed=None, name=name, default=default, description=description, **kwargs)
        return factory.create(extension=extension, do_command=do_command)

    def execute_busy_command(self, busy, *args):
        try:
            self.do_command(*args)
        finally:
            self._busy_remove(busy)

    def command(self, busy, *args):
        logging.info("waiter command {} = {}".format(self.name, args))
        if hasattr(self, "do_command"):
            t = threading.Thread(name="Command {} [{}] execution".format(self.name, busy),
                                 target=self.execute_busy_command,
                                 args=(busy,) + args)
            t.setDaemon(True)
            self._busy.add(busy)
            t.start()
        with self._lock:
            self._value = args

    def reset(self):
        with self._lock:
            self._busy_clean()
            self.do_reset()

    def _check_command_argument(self, *args):
        """ Base implementation : should be at least one integer

        :return: None if wrong else the arguments tuple
        """
        if not len(args):
            return None
        try:
            args = [a for a in args]
            args[0] = int(args[0])
        except ValueError:
            return None
        return args


class WaiterCommandFactory(CommandFactory):
    type = "w"  # blocking commands
    block_constructor = WaiterCommand


class Requester(Sensor):
    @staticmethod
    def create(extension, name, default=None, description=None, **kwargs):
        do_read = extract_arg("do_read", kwargs)
        factory = RequesterFactory(ed=None, name=name, default=default, description=description, **kwargs)
        return factory.create(extension=extension, do_read=do_read)

    def __init__(self, extension, info, value=None):
        super().__init__(extension, info, value)
        self._condition = threading.Condition(self._lock)
        self._ready = False
        self._results = []
        self._pending_async_results = set()

    def _set_value(self, value):
        with self._condition:
            super()._set_value(value)
            if not hasattr(self, "do_read"):
                while self._pending_async_results:
                    busy = self._pending_async_results.pop()
                    self._new_result(busy, value, None)
                self._flush_pending_async_results()
            self._ready = True
            self._condition.notify_all()

    def _new_result(self, busy, v="invalid", exception=None):
        with self._lock:
            self._results.append((busy, v, exception))
            self._pending_async_results.discard(busy)

    def _flush_results(self):
        with self._lock:
            self._results = []

    def _flush_pending_async_results(self):
        with self._lock:
            self._pending_async_results = set()

    @property
    def results(self):
        with self._lock:
            return self._results[:]

    def get_results(self):
        with self._lock:
            ret = self._results
            self._flush_results()
            return ret

    def execute_busy_read(self, busy, *args):
        v = "invalid"
        ex = None
        try:
            v = self.get(*args)
        except Exception as e:
            ex = e
            raise e
        finally:
            self._new_result(busy, v, ex)

    def get_async(self, busy):
        logging.info("requester {}".format(self.name))
        self._pending_async_results.add(busy)
        if hasattr(self, "do_read"):
            t = threading.Thread(name="Requester {} [{}] execution".format(self.name, busy),
                                 target=self.execute_busy_read,
                                 args=(busy,))
            t.setDaemon(True)
            self._busy.add(busy)
            t.start()

    def busy_get(self):
        logging.info("busy_get {}".format(self.name))
        if hasattr(self, "do_read"):
            return self.do_read()
        with self._condition:
            self._ready = False
            self._condition.wait_for(lambda: self._ready)
            return self._value

    def reset(self):
        with self._lock:
            self._ready = True
            self._condition.notify_all()
            self._busy_clean()
            self._flush_results()
            self._flush_pending_async_results()
            self.do_reset()

    def _check_command_argument(self, *args):
        """ Base implementation for requester without arguments if no args return () [execute inline],
        if an argument check if it is integer and use it as busy.

        :return: None if wrong else the arguments tuple
        """
        if len(args) > 1:
            return None
        if not len(args):
            return ()
        try:
            return (int(args[0]),)
        except ValueError:
            return None
        return None

    def _sync_cgi(self, request):
        _name, args = self._get_request_data(request.path)
        args = self._check_command_argument(*args)
        return str(self.busy_get(*args))

    def _async_cgi(self, request):
        _name, args = self._get_request_data(request.path)
        args = self._check_command_argument(*args)
        self.get_async(*args)
        return ""

    def get_cgi(self, path):
        if not path.startswith("/"):
            return None
        name, args = self._get_request_data(path)
        if name != self.name:
            return None
        args = self._check_command_argument(*args)
        if args is None:
            return None
        if not len(args):
            return CGI(self._sync_cgi)
        return CGI(self._async_cgi)

    def poll(self):
        return {}
        # return {self.name: self.value}


class RequesterFactory(SensorFactory):
    type = "R"  # blocking reporter
    block_constructor = Requester


class Reporter(Sensor):

    @staticmethod
    def create(extension, name, default=None, description=None, **kwargs):
        do_read = extract_arg("do_read", kwargs)
        factory = ReporterFactory(ed=None, name=name, default=default, description=description, **kwargs)
        if do_read:
            if len(inspect.getargspec(do_read)[0]) != len(factory.signature):
                raise TypeError("do_read should match the signature {}".format(factory.signature))
        return factory.create(extension=extension, do_read=do_read)


    def _resolve_values(self, *args):
        if not self.signature:
            return self._value
        d = self._value
        default = ""
        for a in args:
            default = d.get(None, default)
            try:
                d = d[a]
            except KeyError:
                return default
        return d

    def _values_dict(self, flat=False):
            signature = self.signature
            l = len(signature)
            if not l:
                return self._value
            values = {}
            stack = [([], self._value, values)]
            for s in signature:
                l -= 1
                new_stack=[]
                try:
                    other = s.elements
                except AttributeError:
                    other = set()
                while stack:
                    args,src,dst = stack.pop()
                    elements = {e for e in other.copy().union(src.keys()) if e is not None}
                    for e in elements:
                        new_args = args.copy()+[e]
                        if l:
                            d = {}
                            if not flat:
                               dst[e] = d
                            new_stack += [(new_args, src.get(e,{}), d)]
                        else:
                            v = self._resolve_values(*new_args)
                            if not flat:
                                dst[e] = v
                            else:
                                values[tuple(new_args)] = v
                stack = new_stack
            return values

    @property
    def value(self):
        """Last value"""
        with self._lock:
            return self._values_dict(flat=False)

    def _set_value(self, value, *args):
        with self._lock:
            if not args:
                self._value = value
            else:
                d = self._value
                for a in args[:-1]:
                    if not a in d:
                        d[a] = {}
                    d = d[a]
                d[args[-1]] = value

    def _convert_args(self, *args):
        try:
            return map(lambda x, y: x(y), self.signature, args)
        except (ValueError, KeyError):
            raise TypeError("Arguments don't fit signature {}".format(self.signature))

    def get(self, *args):
        if len(args) != len(self.signature):
            raise TypeError("get must have {} arguments".format(len(self.signature)))
        args = tuple(self._convert_args(*args))
        v = self.do_read(*args) if hasattr(self, "do_read") else None
        with self._lock:
            if v is not None:
                self._set_value(v, *args)
            return self._resolve_values(*args)

    def set(self, value, *args):
        if len(args) != len(self.signature):
            raise TypeError("set must have {} arguments".format(len(self.signature)))
        args = self._convert_args(*args)
        self._set_value(value, *args)

    def poll(self):
        if not self.signature:
            return {(): self.get()}
        """Otherwise we cannot know hot to call get() we must use last computed value"""
        with self._lock:
            return self._values_dict(flat=True)

    def _sync_cgi(self, request):
        _name, args = self._get_request_data(request.path)
        return str(self.get(*self._convert_args(*args)))

    def get_cgi(self, path):
        if not path.startswith("/"):
            return None
        name, args = self._get_request_data(path)
        if name != self.name:
            return None
        if len(args) != len(self.signature):
            return None
        try:
            args = tuple(self._convert_args(*args))
        except (ValueError, KeyError):
            return None
        return CGI(self._sync_cgi)


class ReporterFactory(SensorFactory):
    block_constructor = Reporter
