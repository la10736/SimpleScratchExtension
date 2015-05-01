import os
from scratch.components import Sensor
from scratch.extension import Extension, ExtensionService
from scratch.utils import get_local_address, save_service_description

__author__ = 'michele'

class MyFirstScratchExtension(Extension):
    def do_init_components(self):
        self.component = Sensor.create(self, name="position")
        return [self.component]
    
    def change_position(self, position):
        self.component.set(position)

port = 49411
name = "first_extension"
fname = name + ".json"

instruction = """Open scratch, hold shift and click File menu: Chose "Import experimental HTTP Extension"
Browse to this directory [{}] and select {}
Build: When "green flag" clicked, forever set x to position
Where position is a gray sensor in More Blocks - {} -
""".format(os.path.abspath(os.path.curdir), fname, name)

if __name__=="__main__":
    extension = MyFirstScratchExtension()
    # Without fix the port ExtensionService() will use a random port that will change at every service start
    service = ExtensionService(extension, name, port=port)
    # You should know how scratch can reach your service (host name or ip address). You can use a fixed name or ip
    # or use get_local_address() helper function to guess it.
    host = get_local_address("www.google.com")
    save_service_description(service, fname, host)
    service.start()
    print(instruction)
    while True:
        val = input("Type new position or enter to exit")
        if not val:
            break
        try:
            extension.change_position(int(val))
        except ValueError:
            print("Cannot convert {} in int value...".format(val))

    print("Goodbye!!!")
