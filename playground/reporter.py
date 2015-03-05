import logging
logging.getLogger().setLevel(logging.DEBUG)

import json
from scratch.components import Reporter
from scratch.extension import Extension, ExtensionService

__author__ = 'michele'

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55080



class ExtensionReporter(Extension):
    def do_init_components(self):
        self.reporter = Reporter.create(self, name="message", description="%m.coord value", coord={"x":0,"y":0})
        return [self.reporter]


if __name__ == "__main__":
    e = ExtensionReporter()
    es = ExtensionService(e, "Repporter Test", port=DEFAULT_PORT)
    with open("reporter_test.sed", "w") as f:
        d = es.description
        d["host"] = DEFAULT_HOST
        json.dump(d, fp=f)
        es.start()
    while True:
        val = input("Type <x|y> <val> [Ctrl-C to stop the service]")
        try:
            a,v = val.split(" ",maxsplit=1)
            e.reporter.set(v,a)
        except Exception as e:
            logging.warning(e)
