import json
import logging
from queue import Queue, Empty
import time
from scratch.components import Command, BooleanBlock, Requester
from scratch.extension import Extension, ExtensionService

logging.getLogger().setLevel(logging.DEBUG)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 33445

__author__ = 'michele'


class ChatUser(Extension):
    users = {}
    timeout = 5

    def __init__(self, username):
        self._username = username
        ChatUser.users[self._username] = self
        self._last_register = 0
        self._incoming_message = {}
        super().__init__()

    def _reset_incomin_message(self):
        self._incoming_message = {}

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

    def _get_incoming_queue(self, from_user):
        if not from_user in self._incoming_message:
            self._incoming_message[from_user] = Queue()
        return self._incoming_message[from_user]

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
                dst._get_incoming_queue(self._username).put_nowait(msg)

    def _incoming_mail(self, who=""):
        if who:
            return not self._get_incoming_queue(who).empty()
        for q in self._incoming_message.values():
            if not q.empty():
                return True
        return False

    def _get_message(self, who=""):
        if who:
            return self._get_incoming_queue(who).get()
        else:
            for n, q in self._incoming_message.items():
                try:
                    return "[{}] {}".format(n, q.get(block=False))
                except Empty:
                    pass
            return ""

    def _register(self, username):
        if self._username == username:
            self._last_register = time.time()
        else:
            logging.warning("Utente errato {}".format(username))
            self._last_register = 0

    def do_init_components(self):
        self.register = Command.create(self, name="{}_register".format(self.username), description="Registra %s", do_command=self._register)
        self.is_online = BooleanBlock.create(self, name="{}_online".format(self.username), description="In Linea", do_read=self._is_on_line)
        self.send = Command.create(self, name="{}_send".format(self.username), description="Invia %s a %s", do_command=self._send_to)
        self.receive = Requester.create(self, name="{}_receive".format(self.username), description="Prendi messaggio",
                                        do_read=self._get_message)
        self.some_mails = BooleanBlock.create(self, name="{}_incoming".format(self.username), description="Posta presente",
                                              do_read=self._incoming_mail)

        return [self.register, self.is_online, self.send, self.receive, self.some_mails]


if __name__ == "__main__":
    # utenti = []
    # while True:
    #     utente = input("Nome utenet [Enter per finire]")
    #     if not utente:
    #         break
    #     if not utente in utenti:
    #         utenti.append(utente)
    utenti = ["pippo","pluto"]
    print("Utenti presenti:\n{}\n".format("\n".join(utenti)))
    chats = [ChatUser(username=utente) for utente in utenti]
    port = 33445
    chat_services = [ExtensionService(c, c.username, port=port+i) for i,c in enumerate(chats)]
    for s in chat_services:
        with open("chat_{}.sed".format(s.name), "w") as f:
            d = s.description
            d["host"] = DEFAULT_HOST
            json.dump(d, fp=f)
            s.start()

    input("Premi Enter per interrompere il servizio")

