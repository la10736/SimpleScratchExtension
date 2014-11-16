import weakref

__author__ = 'michele'


class Sensor():
    """Sensor sono gli elementi base delle estensioni: internamente espongono la funzione di set()
    e come estensione quella di get() completamente sincrona. quando vengono costruite devono
    avere comunque un valore e rendono sempre un valore coerente.
    Una volta agganciate a una estensione se quella estensione diventa visibile risponde alle richieste
    con il valore di get
    """

    type = "r" # Sono dei reporter

    def __init__(self, extension, name, value="", description=None):
        self._ex = weakref.ref(extension)
        self._name = name
        self._description = description if description is not None else self._name
        self._value = value

    @property
    def extension(self):
        return self._ex()

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    def get(self):
        return self._value

    @property
    def definition(self):
        return [self.type, self.description, self.name]