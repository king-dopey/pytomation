"""
Pytomation Web socket server

Author(s):
David Heaps - king.dopey.10111@gmail.com
"""

import mimetypes
import os
import collections

from geventwebsocket import WebSocketServer, WebSocketApplication, Resource
try:
    from .ha_interface import HAInterface
    from ..common.pytomation_api import PytomationAPI
    from ..common import config
    from ..devices import StateDevice
    from ..common.pytomation_object import PytomationObject
except Exception as ex:
    print(ex)

class PytoWebSocketApp(WebSocketApplication):
    _api = PytomationAPI()

    def on_open(self):
        if not self.ws.environ['user']:
            self.ws.send("Unauthorized")
        print("WebSocket Client connected")

    def on_message(self, message):
        if message:
            if not self.ws.environ['user']:
                if message in PytomationObject.users:
                    self.ws.environ['user'] = PytomationObject.users[message]
                else:
                    self.ws.send("Unauthorized")
            else:
                self.ws.send(self._api.get_response(data=message, type=self._api.WEBSOCKET, user=self.ws.environ['user']).encode('UTF-8'))

    def on_close(self, reason):
        print("WebSocket Client disconnected: ")


class PytoWebSocketServer(HAInterface):
    _api = PytomationAPI()

    def __init__(self, *args, **kwargs):
        self._address = kwargs.get('address', config.http_address)
        self._port = kwargs.get('port', int(config.http_port))
        self._path = kwargs.get('path', config.http_path)
        super(PytoWebSocketServer, self).__init__(self._address, *args, **kwargs)
        self.unrestricted = True  # To override light object restrictions

    def _init(self, *args, **kwargs):
        self._ssl_path = './ssl'
        self.ws = None
        try:
            self._ssl_path = config.ssl_path
        except:
            pass
        if not os.path.isdir(self._ssl_path):
                self._ssl_path = None
        super(PytoWebSocketServer, self)._init(*args, **kwargs)

    def run(self):
        resource = collections.OrderedDict()
        resource['/api/bridge'] = PytoWebSocketApp
        resource['/api/device*'] = self.api_app
        resource['/api/voice'] = self.api_app
        resource['/'] = self.http_file_app
        if self._ssl_path:
            self.ws = WebSocketServer(
            (self._address, self._port),
            Resource(resource),
            pre_start_hook=auth_hook, keyfile=self._ssl_path + '/server.key', certfile=self._ssl_path + '/server.crt')
        else:
            self.ws = WebSocketServer(
                (self._address, self._port),
                Resource(resource),
                pre_start_hook=auth_hook)

        print("Serving WebSocket Connection on", self._address, "port", self._port, "...")
        StateDevice.onStateChangedGlobal(self.broadcast_state)
        self.ws.serve_forever()

    def api_app(self, environ, start_response):
        method = environ['REQUEST_METHOD'].lower()
        if method == 'post':
            data = environ['wsgi.input'].read()
        else:
            data = None
        start_response("200 OK", [("Content-Type", "text/html"), ('Access-Control-Allow-Origin', '*')])
        return [self._api.get_response(path='/'.join(environ['PATH_INFO'].split('/')[2:]), source=PytoWebSocketServer,
                                      method=method, data=data, user=environ['user']).encode('UTF-8')]

    def http_file_app(self, environ, start_response):
        path_info = environ['PATH_INFO']
        http_file = self._path + path_info
        if self._ssl_path:
            protocol = 'https://'
        else:
            protocol = 'http://'

        if os.path.exists(http_file):
            if os.path.isdir(http_file):
                if http_file.endswith('/'):
                    http_file += 'index.html'
                else:
                    if path_info.startswith('/'):
                        location = protocol + self._address + ':' + str(self._port) + path_info + '/'
                    else:
                        location = protocol + self._address + ':' + str(self._port) + '/' + path_info + '/'
                    start_response("302 Found",
                                   [("Location", location), ('Access-Control-Allow-Origin', '*')])
                    return [b'']

            mime = mimetypes.guess_type(http_file)
            start_response("200 OK", [("Content-Type", mime[0]), ('Access-Control-Allow-Origin', '*')])
            return open(http_file, "rb")
        else:
            start_response("404 Not Found", [("Content-Type", "text/html"), ('Access-Control-Allow-Origin', '*')])
            return [b"404 Not Found"]

    def broadcast_state(self, state, source, prev, device):
        # TODO: add queue system and separate thread to avoid blocking on long network operations
        if self.ws:
            for client in list(self.ws.clients.values()):
                message = self._api.get_state_changed_message(state, source, prev, device, client.ws.environ['user'])
                if message:
                    client.ws.send(message)


def auth_hook(web_socket_handler):
    if config.auth_enabled == 'Y':
        auth = web_socket_handler.headers.get('Authorization', None)
        if not auth:
            if web_socket_handler.command == 'OPTIONS':
                web_socket_handler.start_response("200 OK",
                                                  [("Access-Control-Allow-Headers", "Authorization"),
                                                   ('Access-Control-Allow-Origin', '*')])
            else:
                web_socket_handler.environ['user'] = None
                web_socket_handler.start_response("401 Unauthorized", [('WWW-Authenticate', 'Basic realm=\"Pytomation\"'), ('Access-Control-Allow-Origin', '*')])
        else:
            if not auth in PytomationObject.users:
                web_socket_handler.start_response("401 Unauthorized", [('WWW-Authenticate', 'Basic realm=\"Pytomation\"'), ('Access-Control-Allow-Origin', '*')])
            else:
                web_socket_handler.environ['user'] = PytomationObject.users[auth]
                return False
    else:
        web_socket_handler.environ['user'] = list(PytomationObject.users.items())[0][1]
        return False
