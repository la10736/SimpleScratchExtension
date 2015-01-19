import json
import logging
from scratch.components import CommandFactory, SensorFactory
from scratch.extension import ExtensionFactory, Extension, EXTENSION_DEFAULT_PORT

__author__ = 'michele'


class Positions():
    def __init__(self, x=0, y=0, direction=0):
        self.x = x
        self.y = y
        self.direction = direction

    def update(self, x=None, y=None, direction=None):
        if x is not None:
            self.x = x
        if y is not None:
            self.y = y
        if direction is not None:
            self.direction = direction


class Slave(Extension):
    def __init__(self, base_name, *args, **kwargs):
        super().__init__(base_name+"-Slave", *args, **kwargs)
        self.base_name = base_name

    def do_init_components(self):
        self.x = SensorFactory(ed=None, name="x").create(self)
        self.y = SensorFactory(ed=None, name="y").create(self)
        self.direction = SensorFactory(ed=None, name="direction").create(self)
        return [self.x, self.y, self.direction]

    def set_new_positions(self, p):
        self.x.set(p.x)
        self.y.set(p.y)
        self.direction.set(p.direction)


class Master(Extension):
    def __init__(self, base_name, *args, **kwargs):
        super().__init__(base_name+"-Master", *args, **kwargs)
        self.base_name = base_name
        self.p = Positions()
        self.f = Positions(1, 1, 1)
        self.r = Positions()

    def _find_slave(self):
        g = self.group
        slave_name = self.base_name+"-Slave"
        for e in g.extensions:
            if e.name == slave_name:
                return e
        raise KeyError("Cannot find slave extension {} in my group".format(slave_name))

    def update(self):
        p, r, f = self.p, self.r, self.f
        new_point = Positions(r.x + (r.x - p.x) * f.x,
                              r.y + (r.y - p.y) * f.y,
                              r.direction + (r.direction - p.direction) * f.direction)
        try:
            self._find_slave().set_new_positions(new_point)
        except KeyError:
            logging.error("No slave extension!")

    def source_do_command(self, x, y, direction):
        self.p.update(float(x), float(y), float(direction))
        self.update()

    def factors_do_command(self, x, y, direction):
        self.f.update(float(x), float(y), float(direction))
        self.update()

    def references_do_command(self, x, y, direction):
        self.r.update(float(x), float(y), float(direction))
        self.update()

    def do_init_components(self):
        source = CommandFactory(ed=None, name="Source",
                                     description="Source x=%n y=%n direction=%n").create(self)
        source.do_command = self.source_do_command
        factors = CommandFactory(ed=None, name="Factors",
                                      description="Reference factors x=%n y=%n direction=%n").create(self)
        factors.do_command = self.factors_do_command
        references = CommandFactory(ed=None, name="References",
                                         description="References x=%n y=%n direction=%n").create(self)
        references.do_command = self.references_do_command
        return [source, factors, references]


class MirrorFactory(ExtensionFactory):
    def do_create(self, base_name, port=EXTENSION_DEFAULT_PORT, *args, **kwargs):
        if port != 0:
            ports = self.port_generator(port)
        else:
            def void():
                while True:
                    yield 0
            ports = void()
        return [Master(base_name=base_name, port=next(ports)),
                Slave(base_name=base_name, port=next(ports))]

    def __init__(self):
        super().__init__("Mirror")

factory = MirrorFactory()
g = factory.create("test", port=55066)
for e in g.extensions:
    with open(e.name+".sed", "w") as f:
        json.dump(e.description, fp=f)

g.start()
input("Enter to stop servers")

