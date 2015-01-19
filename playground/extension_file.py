__author__ = 'michele'

from scratch import extension
import json

name = "TestBaseSensor"
ed = extension.ExtensionDefinition("def")
ed.add_sensor("volume", "0", "The Volume meter")
e = extension.ExtensionBase(ed, name)

with open(name + ".sef", "w") as f:
    json.dump(e.description, fp=f)