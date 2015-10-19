from six.moves import zip_longest

__author__ = 'michele'

import logging
from six.moves import socketserver
import struct
import select
from collections import defaultdict
# Commonly used flag states
READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
READ_WRITE = READ_ONLY | select.POLLOUT

logging.getLogger().setLevel(logging.DEBUG)


def _extract(word):
    word = word.strip()
    if word.startswith('"') and word.endswith('"') and len(word) > 1:
        """Quoted"""
        return word[1:-1].replace('""', '"')
    try:
        return int(word)
    except ValueError:
        pass
    try:
        return float(word)
    except ValueError:
        pass
    return word


# noinspection PyPep8Naming
def tokenizer(s):
    s.strip()
    IDLE, DATA, QUOTEDDATA, QUOTEQUOTEDDATA = 0, 1, 2, 3
    EV_NONE, EV_START_TOKEN, EV_END_TOKEN = 0, 1, 2
    transactions = {IDLE: defaultdict(lambda: (EV_START_TOKEN, DATA), {'"': (EV_START_TOKEN, QUOTEDDATA),
                                                                       ' ': (EV_NONE, IDLE)}),
                    DATA: defaultdict(lambda: (EV_NONE, DATA), {' ': (EV_END_TOKEN, IDLE)}),
                    QUOTEDDATA: defaultdict(lambda: (EV_NONE, QUOTEDDATA), {'"': (EV_NONE, QUOTEQUOTEDDATA)}),
                    QUOTEQUOTEDDATA: defaultdict(lambda: (EV_NONE, QUOTEDDATA), {' ': (EV_END_TOKEN, IDLE)}),
    }
    start = 0
    state = IDLE
    for pos, c in enumerate(s):
        ev, state = transactions[state][c]
        if ev == EV_START_TOKEN:
            start = pos
        elif ev == EV_END_TOKEN:
            yield _extract(s[start:pos])
    if state != IDLE:
        yield _extract(s[start:])


def split_message(msg):
    for pos, c in enumerate(msg):
        if ord(c) <= 32:
            return msg[:pos].lower(), msg[pos + 1:]
    return msg.lower(), ""

class Scratch14SensorReceiverHandler(socketserver.StreamRequestHandler):
    timeout = 2
    s_size = struct.calcsize(">I")

    def __init__(self, request, client_address, srv):
        logging.debug('__init__')
        self.sensors = {}
        socketserver.StreamRequestHandler.__init__(self, request, client_address, srv)
        return

    def _sensor_update(self, args):
        """It works because tokenizer is a generator and [tokenizer(args)]*2 calls iterator
        2 times"""
        self.sensors.update(zip_longest(*[tokenizer(args)]*2, fillvalue=None))

    def _get(self, l):
        ret = b''
        while l > 0:
            r = self.request.recv(l)
            l -= len(r)
            ret += r
        return ret

    def _read_single(self):
        lstr = self._get(self.s_size)
        l = struct.unpack(">I", lstr)
        logging.debug("Message len = {}".format(l))
        msg = self._get(l[0]).decode()
        cmd, data = split_message(msg)
        #I should filter against cmd....
        if cmd=="sensor-update":
            self._sensor_update(data)
            logging.debug(self.sensors)
        if cmd=="broadcast":
            logging.debug("broadcast "+",".join(tokenizer(data)))

    def handle(self):
        logging.debug('CONNESIONE')
        p = select.poll()
        p.register(self.request, READ_ONLY)
        try:
            while True:
                events = p.poll(1)
                for fd, flag in events:
                    if flag & select.POLLIN:
                        self._read_single()
                    if flag & (select.POLLHUP | select.POLLERR):
                        logging.info("Connessione chiusa")
                        return
        except Exception as e:
            logging.exception(e)

class Scratch14SensorReceiver(socketserver.TCPServer):
    def __init__(self, server_address, handler_class=Scratch14SensorReceiverHandler):
        self.logger = logging.getLogger('Scratch14SensorReceiver')
        self.logger.debug('__init__')
        super(Scratch14SensorReceiver, self).__init__(server_address, handler_class)
        return
