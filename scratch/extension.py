from scratch import components

__author__ = 'michele'


class Extension():
    """Contenitore dei componenti: presenda al web server le funzioni per le richieste
    e rende le risposte. Fornisce le factory per i componenti.
    """

    def __init__(self, name):
        self._name = name
        self._components = set()

    @property
    def name(self):
        return self._name

    def _register_components(self, *components):
        for component in components:
            self._components.add(component)

    def _deregister_components(self, *components):
        for component in components:
            self._components.remove(component)

    @property
    def components(self):
        return frozenset(self._components)

    def create_sensor(self, value=""):
        """Costruisce un sensore di valore iniziale value e lo registra"""
        s = components.Sensor(self, value=value)
        self._register_components(component=s)