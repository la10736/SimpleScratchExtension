import json
import logging
from scratch.components import Sensor, Command
from scratch.extension import Extension, EXTENSION_DEFAULT_PORT, ExtensionService
from scratch.utils import get_local_address
import sys

__author__ = 'michele'

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55066


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
    def do_init_components(self):
        self.x = Sensor.create(self, name="x")
        self.y = Sensor.create(self, name="y")
        self.direction = Sensor.create(self, name="direction")
        return [self.x, self.y, self.direction]

    def update(self, x=None, y=None, direction=None):
        if x is not None:
            self.x.set(x)
        if y is not None:
            self.y.set(y)
        if direction is not None:
            self.direction.set(direction)


class MasterBase(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slave = None

    @property
    def slave(self):
        return self._slave

    @slave.setter
    def slave(self, value):
        self._slave = value

    def update(self, x=None, y=None, direction=None):
        self.slave.update(x, y, direction)

    def do_command(self, x, y, direction):
        self.update(float(x), float(y), float(direction))

    def do_init_components(self):
        set_slave_point = Command.create(self, name="set_slave_point",
                                         description="Imposta remoto x=%n y=%n direction=%n",
                                         do_command=self.do_command)
        return [set_slave_point]


class Master(MasterBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.p = Positions()
        self.f = Positions(1, 1, 1)
        self.r = Positions()

    def update(self):
        p, r, f = self.p, self.r, self.f
        x = r.x + (r.x - p.x) * f.x
        y = r.y + (r.y - p.y) * f.y
        direction = r.direction + (r.direction - p.direction) * f.direction
        super().update(x, y, direction)

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
        source = Command.create(self, name="Source",
                                description="Source x=%n y=%n direction=%n",
                                do_command=self.source_do_command)
        factors = Command.create(self, name="Factors",
                                 description="Reference factors x=%n y=%n direction=%n",
                                 do_command=self.factors_do_command)
        references = Command.create(self, name="References",
                                    description="References x=%n y=%n direction=%n",
                                    do_command=self.references_do_command)
        return [source, factors, references]

def create_services(base_name, port=EXTENSION_DEFAULT_PORT, simple=False):
    master = MasterBase if simple else Master
    port_master = port
    port_slave = 0 if port_master == 0 else port_master + 1
    slave = Slave
    m = master()
    s = slave()
    m.slave = s
    es_m = ExtensionService(m, base_name+"-Master", port=port_master)
    es_s = ExtensionService(s, base_name+"-Slave", port=port_slave)
    return [es_m, es_s]


def usage(e=-1):
    print("""Use {} -h | -s [host [port]]
    -h      this help
    -s      Simple: just one master command to set slave point
    host    your ip address where scratch can reach
    port    the master extension port, slave will use port+1 (<0 use default = {}, 0 to leave the
            the SO get a free two)

    After start you will find in same directory two file test-Master.sed and test-Slave.sed. Load the
    first one in your master scratch application (hold shift, open file menu and select
    "import experimental HTTP extension") and the second one on an other scratch (can be the same
    application too).

    Look at more block and ...have fun!

    ....When you are done to play press enter.
    """.format(sys.argv[0]))
    exit(e)


if __name__ == '__main__':

    host = DEFAULT_HOST
    _simple = False
    pname = sys.argv[0]
    sys.argv = sys.argv[1:]
    if len(sys.argv) and sys.argv[0] == "-h":
        usage(0)
    if len(sys.argv) and sys.argv[0] == "-s":
        print("Simple version: just one command to set remote point")
        _simple = True
        sys.argv = sys.argv[1:]
    if len(sys.argv):
        host = sys.argv[0]
        if host.lower() == "guess":
            host = get_local_address("www.google.com")
            if not host:
                logging.warning("Cannot guess your host [default to {}]: "
                                "please use {} <your local address>".format(DEFAULT_HOST, pname))
                host = DEFAULT_HOST
        sys.argv = sys.argv[1:]
    if len(sys.argv):
        port = int(sys.argv[0])
        if port < 0:
            port = DEFAULT_PORT

    services = create_services("test", port=55066, simple=_simple)
    for s in services:
        with open(s.name + ".sed", "w") as f:
            d = s.description
            d["host"] = host
            json.dump(d, fp=f)
        s.start()
    input("Enter to stop servers")

