import json
from scratch.components import Hat, WaiterCommand
from scratch.extension import Extension, ExtensionService

__author__ = 'michele'

import random
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55078


class ExtensionWaiterCommand(Extension):

    i = 0

    def do_command(self):
        t = 1 + 2 * random.random()
        i = ExtensionWaiterCommand.i
        ExtensionWaiterCommand.i += 1
        print("===========================[{}]I'm waiting for {} seconds".format(i, t))
        time.sleep(t)
        print("+++++++++++++++++++++++++++[{}]Done".format(i))


    def do_init_components(self):
        self.w = WaiterCommand.create(self, name="random wait", do_command=self.do_command)
        return [self.w]


if __name__ == "__main__":
    e = ExtensionWaiterCommand()
    es = ExtensionService(e, "Waiter Test", port=DEFAULT_PORT)
    with open("wc_test.sed", "w") as f:
        d = es.description
        d["host"] = DEFAULT_HOST
        json.dump(d, fp=f)
        es.start()
    input("Enter to stop servers")
