import json
import logging
from queue import Queue, Empty
import threading
import time
from scratch.components import Command, BooleanBlock, Requester
from scratch.extension import Extension, ExtensionService

logging.getLogger().setLevel(logging.DEBUG)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 33445

__author__ = 'michele'


class SelectQueue():
    _reset_sentinel = object()

    def __init__(self):
        self._cond = threading.Condition()
        self._data = None
        self._init_data()

    def _init_data(self):
        self._data = []

    def put_nowait(self, d):
        with self._cond:
            self._data.append(d)
            self._cond.notify_all()

    def empty(self, condition=None):
        with self._cond:
            if self._data and len(self._data) == 1 and self._data[0] == self._reset_sentinel:
                self._init_data()
                return True
            if condition is not None:
                return not any(map(condition, self._data))
            else:
                return bool(self._data)

    def _no_block_get(self, condition=None):
        if condition is None:
            if self._data:
                return self._data.pop(0)
            return None
        for i, e in enumerate(self._data):
            if e is self._reset_sentinel or condition(e):
                del self._data[i]
                return e
        return None

    def _block_get(self, condition=None):
        ret = self._no_block_get(condition=condition)
        while ret is None:
            self._cond.wait()
            ret = self._no_block_get(condition=condition)
        logging.debug("$$$$$$$$$ ret = {}".format(ret))

        return ret

    def get(self, block=True, condition=None):
        with self._cond:
            if self._data and self._data[0] is self._reset_sentinel:
                self._data.pop(0)
            if block:
                ret = self._block_get(condition=condition)
            else:
                ret = self._no_block_get(condition=condition)
            if ret is self._reset_sentinel:
                return None
            return ret

    def reset(self):
        with self._cond:
            self._init_data()
            self._data.append(self._reset_sentinel)
            self._cond.notify_all()


class ChatUser(Extension):
    users = {}
    timeout = 5

    def __init__(self, username, all_users=None):
        self._username = username
        ChatUser.users[self._username] = self
        self._last_register = 0
        self._incoming_message = SelectQueue()
        self._all_users = all_users
        super().__init__()

    def _reset_incomin_message(self):
        self._incoming_message.reset()

    @property
    def username(self):
        return self._username

    @property
    def online(self):
        return (time.time() - self._last_register) < self.timeout

    def _is_on_line(self):
        return self.online


    def do_reset(self):
        self._last_register = time.time() - 2 * self.timeout
        self._reset_incomin_message()

    def _get_groups_dicts(self):
        """User defined groups and general group not implemented yet"""
        return [{name: [ex] for name, ex in self.users.items()}]

    def _resolve_destination(self, who):
        who = who.lower()
        if who in ["", "all", "tutti", "bradcast", "sparpaglia"]:
            return self.users.values()
        for d in self._get_groups_dicts():
            try:
                return d[who]
            except KeyError:
                pass
        logging.warning("Utente sconosciuto {}".format(who))

    def _send_to(self, msg, who):
        destinations = self._resolve_destination(who)
        for dst in destinations:
            if dst is not self:
                logging.info("############ invia {} a {}".format(msg, dst.username))
                dst._incoming_message.put_nowait((self._username, msg))

    def _incoming_mail(self, who=""):
        condition = lambda e: e[0] == who if who else None
        return not self._incoming_message.empty(condition=condition)

    def _get_message(self, who=""):
        condition = lambda e: e[0] == who if who else None
        ret = self._incoming_message.get(block=True, condition=condition)
        if ret is None:
            return ""
        u, m = ret
        return m if who else "[{}] {}".format(u, m)

    def _register(self, username):
        if self._username == username:
            self._last_register = time.time()
        else:
            logging.warning("Utente errato {}".format(username))
            self._last_register = 0

    def do_init_components(self):
        menu_source_str = "%s"
        menu_source = {}
        menu_dest_str = "%s"
        menu_dest = {}
        if self._all_users:
            menu_dest_str = "%m.dest_utenti"
            menu_dest = {"dest_utenti":["tutti"] + self._all_users}
            menu_source_str = "%m.src_utenti"
            menu_source = {"src_utenti":{x:x for x in self._all_users}}
            menu_source["src_utenti"]["tutti"] = ""

        self.register = Command.create(self, name="{}_register".format(self.username), description="Registra %s",
                                       do_command=self._register)
        self.is_online = BooleanBlock.create(self, name="{}_online".format(self.username), description="In Linea",
                                             do_read=self._is_on_line)
        self.send = Command.create(self, name="{}_send".format(self.username),
                                   description="Invia %s a {}".format(menu_dest_str),
                                   do_command=self._send_to, **menu_dest)
        self.receive = Requester.create(self, name="{}_receive".format(self.username),
                                        description="Prendi messaggio da {}".format(menu_source_str),
                                        do_read=self._get_message, **menu_source)
        self.some_mails = BooleanBlock.create(self, name="{}_incoming".format(self.username),
                                              description="Posta da {}".format(menu_source_str),
                                              do_read=self._incoming_mail, **menu_source)

        return [self.register, self.is_online, self.send, self.receive, self.some_mails]


if __name__ == "__main__":
    # utenti = []
    # while True:
    # utente = input("Nome utenet [Enter per finire]")
    #     if not utente:
    #         break
    #     if not utente in utenti:
    #         utenti.append(utente)
    utenti = ["pippo", "pluto", "Dan"]
    print("Utenti presenti:\n{}\n".format("\n".join(utenti)))
    chats = [ChatUser(username=utente, all_users=utenti) for utente in utenti]
    port = 33445
    chat_services = [ExtensionService(c, c.username, port=port + i) for i, c in enumerate(chats)]
    for s in chat_services:
        with open("chat_{}.sed".format(s.name), "w") as f:
            d = s.description
            d["host"] = DEFAULT_HOST
            json.dump(d, fp=f)
            s.start()

    input("Premi Enter per interrompere il servizio")

