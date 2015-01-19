from scratch.receiver14 import Scratch14SensorReceiver, Scratch14SensorReceiverHandler

__author__ = 'michele'


if __name__ == '__main__':
    import threading

    address = ('0.0.0.0', 42001)
    server = Scratch14SensorReceiver(address, Scratch14SensorReceiverHandler)
    ip, port = server.server_address  # find out what port we were given

    t = threading.Thread(target=server.serve_forever)
    t.setDaemon(True)  # don't hang on exit
    t.start()
    t.join()
