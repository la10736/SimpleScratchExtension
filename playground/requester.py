import logging
logging.getLogger().setLevel(logging.DEBUG)

import json
from scratch.components import Requester
from scratch.extension import Extension, ExtensionService

__author__ = 'michele'

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 55080



class ExtensionRequester(Extension):
    def do_init_components(self):
        self.requester = Requester.create(self, name="message")
        return [self.requester]


if __name__ == "__main__":
    e = ExtensionRequester()
    es = ExtensionService(e, "Requester Test", port=DEFAULT_PORT)
    with open("requester_test.sed", "w") as f:
        d = es.description
        d["host"] = DEFAULT_HOST
        json.dump(d, fp=f)
        es.start()
    while True:
        message = input("Write message to send and press enter [Ctrl-C to stop the service]")
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> '{}'".format(message))
        e.requester.set(message)
