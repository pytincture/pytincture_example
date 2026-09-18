"""Adapter shared by Pyodide and MicroPython; only scalar strings cross FFI."""
import json
import js

def decode(text):
    return json.loads(text)

def encode(obj):
    return json.dumps(obj)

async def request(method, payload):
    return await js.labBff(method, payload)

def grid_create(rows):
    js.labGridCreate(rows)

def grid_rows(rows):
    js.labGridRows(rows)

def value(name):
    return js.document.getElementById(name).value

def set_value(name, text):
    js.document.getElementById(name).value = text

def ready(count):
    js.labReady(count)

def status(text):
    js.document.getElementById('status').textContent = text
