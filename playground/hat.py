import json
from scratch.components import Hat
from scratch.extension import Extension, ExtensionService

__author__ = 'michele'

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55076


class ExtensionHat(Extension):
    def do_init_components(self):
        self.hat = Hat.create(self, name="start")
        return [self.hat]


if __name__ == "__main__":
    e = ExtensionHat()
    es = ExtensionService(e, "Hat Test", port=DEFAULT_PORT)
    with open("hat_test.sed", "w") as f:
        d = es.description
        d["host"] = DEFAULT_HOST
        json.dump(d, fp=f)
        es.start()
    while True:
        input("Enter to raise start event [Ctrl-C to stop the service]")
        e.hat.flag()
