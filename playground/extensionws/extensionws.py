import socket
from apport.fileutils import get_recent_crashes
import flask

__author__ = 'michele'

from flask import Flask, request, redirect, url_for, render_template, flash, make_response

from scratch.extension import Extension, ExtensionDefinition, ExtensionBase
from scratch.utils import get_local_address


# configuration
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000
SECRET_KEY = 'My wonderful secret key'

app = Flask(__name__)
app.config.from_object(__name__)
eds = [ExtensionDefinition("First Definition"), ExtensionDefinition("Other Definition")]


@app.route('/')
def show_entries():
    definitions = [ExtensionDefinition.get_registered(n) for n in ExtensionDefinition.registered()]
    extensions = [Extension.get_registered(n) for n in Extension.registered()]
    return render_template('show_entries.html', definitions=definitions, extensions=extensions)


@app.route('/<ex_name>.sed')
def get_extension_file(ex_name):
    e = Extension.get_registered(ex_name)
    d = e.description
    my_ip = get_local_address(request.remote_addr)
    d["host"] = my_ip
    response = make_response(flask.json.dumps(d))
    response.headers["Content-Disposition"] = "attachment; filename{}.sed".format(ex_name)
    return response


@app.route('/create_by_definition', methods=['POST'])
def create_extension():
    ed_name = request.form['definition']
    name = request.form['name']
    ed = ExtensionDefinition.get_registered(ed_name)
    ExtensionBase(ed, name, address=HOST)
    flash('New extension named {} from {} created'.format(name, ed_name))
    return redirect(url_for('show_entries'))


@app.route('/add_component_to_definition', methods=['POST'])
def add_component_to_definition():
    ed_name = request.form['ed_name']
    t = request.form['type']
    name = request.form['name']
    description = request.form['description']
    value = request.form['value']
    ed = ExtensionDefinition.get_registered(ed_name)
    print(t)
    if t == "sensor":
        ed.add_sensor(name=name, value=value, description=description)
        flash('We add new sensor named {} to {}'.format(name, ed_name))
    elif t == "command":
        ed.add_command(name=name, defult=value.split(","), description=description)
        flash('We add new command named {} to {}'.format(name, ed_name))
    return redirect(url_for('show_entries'))


@app.route('/<ex_name>/start')
def start_extension(ex_name):
    e = Extension.get_registered(ex_name)
    e.start()
    flash('Extension {} started'.format(ex_name))
    return redirect(url_for('show_entries'))


@app.route('/<ex_name>/stop')
def stop_extension(ex_name):
    e = Extension.get_registered(ex_name)
    e.stop()
    flash('Extension {} stopped'.format(ex_name))
    return redirect(url_for('show_entries'))


@app.route('/sensor_set', methods=['POST'])
def sensor_set():
    ex_name = request.form['ex_name']
    e = Extension.get_registered(ex_name)
    c_path = request.form['c']
    c = e.get_component(c_path)
    value = request.form['value']
    c.set(value)
    flash('Sensor {}.{} changed to {}'.format(ex_name, c_path, value))
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run(host=HOST)