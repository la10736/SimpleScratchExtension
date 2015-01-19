import threading

__author__ = 'michele'

from flask import Flask
app = Flask(__name__)

@app.route('/')
def dosnt_mater_hello_world():
    return 'Hello World!'

app1 = Flask(__name__)
@app1.route("/")
def altro():
    return 'altro World!'

@app1.route("/altrapagina")
def altropagina():
    return 'altra pagina'

if __name__ == '__main__':
    threading.Thread(target=app.run, daemon=True).start()
    app1.run(port=8080)
