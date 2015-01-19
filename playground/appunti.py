__author__ = 'michele'


from scratch.extension import ExtensionBase as EB, ExtensionDefinition as ED
import json
import threading

ed = ED("test")
ed.add_sensor("PosizioneX", value=0)
ed.add_sensor("PosizioneY", value=0)
ed.add_sensor("Angolo", value=0)

e = EB(ed, "muovi")

with open("muovi.sef","w") as f:
    json.dump(e.description, fp=f)

threading.Thread(target=e._http.serve_forever).start()

x = e.get_component("PosizioneX")
y = e.get_component("PosizioneY")
a = e.get_component("Angolo")
