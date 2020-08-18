'''
Created on Dec 17, 2017

@author: David Heaps
'''
from .pytomation_object import PytomationObject
import base64

class User(PytomationObject):
    def __init__(self, username, accessible_devices = None, is_admin = False, *args, **kwargs):
        self.username = username
        self.is_admin = is_admin
        self.accessible_devices = {}
        self.accessible_commands = {}
        if accessible_devices:
            for dev in accessible_devices:
                if isinstance(dev, tuple):
                    self.accessible_devices[dev[0]._type_id] = dev[0]
                    self.accessible_commands[dev[0]._type_id] = dev[1]
                else:
                    self.accessible_devices[dev._type_id] = dev
                    self.accessible_commands[dev._type_id] = dev.COMMANDS
        try:
            self.users['Basic ' + base64.urlsafe_b64encode((username + ':' + kwargs['password']).encode('UTF-8')).decode('ascii')] = self
        except:
            print("User name and password not supplied for user. Not adding user to security.")
        super(User, self).__init__(username = username, *args, **kwargs)
        if self.is_admin:
            print("Created admin user: " + username)
        else:
            print("Created user: " + username)

    def _initial_vars(self, *args, **kwargs):
        super(User, self)._initial_vars(*args, **kwargs)