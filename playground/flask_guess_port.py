from pyparsing import originalTextFor

__author__ = 'michele'

from flask import Flask
import socketserver
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello World!'

orig_bind = socketserver.TCPServer.server_bind
def my_server_bind(self):
    ret = orig_bind(self)
    print(self.socket.getsockname())
    socketserver.TCPServer.server_bind = orig_bind
    return ret

socketserver.TCPServer.server_bind = my_server_bind

if __name__ == '__main__':
    app.run(port=0)
