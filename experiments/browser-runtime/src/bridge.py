"""Transcrypt-only adapter. Uses native JS objects and promises."""
from org.transcrypt.stubs.browser import *

def decode(text):
    return JSON.parse(text)

def encode(obj):
    return JSON.stringify(obj)

async def request(method, payload):
    return await window.labBff(method, payload)

def grid_create(rows):
    window.labGridCreate(rows)

def grid_rows(rows):
    window.labGridRows(rows)

def value(name):
    return document.getElementById(name).value

def set_value(name, text):
    document.getElementById(name).value = text

def ready(count):
    window.labReady(count)

def status(text):
    document.getElementById('status').textContent = text
