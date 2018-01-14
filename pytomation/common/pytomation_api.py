from .pytomation_object import PytomationObject
from . import pytomation_system
import json
import urllib.parse
#from collections import OrderedDict

class PytomationAPI(PytomationObject):
    """
    Provides a REST WebAPI for Pytomation.
    """
    VERSION = '3.0'
    JSON = 'json'
    WEBSOCKET = 'websocket'

    def get_map(self):
        return {
                   ('get', 'devices'): PytomationAPI.get_devices,
                   ('get', 'device'): PytomationAPI.get_device,
                   ('post', 'device'): self.update_device,
                   ('post', 'voice'): self.run_voice_command
        }
    
    @staticmethod
    def has_security(user, device):
        if user.is_admin:
            return True
        elif device in user.accessible_devices:
            return True
        return False

    def run_voice_command(self, levels, data, source, user):
        for command in data:
            command =  command.lower()
            for dev_name in self.sorted_names_by_length:
                if command.find(dev_name) != -1:
                    #remove the name from command so it doesn't interfere
                    #with the next search
                    command = command.replace(dev_name,'')
                    dev_id = self.name_to_id_map[dev_name]
                    device = self.instances[dev_id]
                    levels = ['device', dev_id]
                    for device_command in device.COMMANDS:
                        if command.find(device_command) != -1:
                            if self.has_security(user,dev_id):
                                command = command.replace(device_command,'')
                                try:
                                    numeric_command = ''.join(ele for ele in command if ele.isdigit())
                                    if numeric_command:
                                        device_command = device_command + ',' + numeric_command
                                except:
                                    pass
                                return self.update_device(levels, 'command=' + device_command, source, user=user)
                            else:
                                return 'access denied'
                    try:
                        numeric_command = ''.join(ele for ele in command if ele.isdigit())
                        if numeric_command:
                            device_command = device.DEFAULT_NUMERIC_COMMAND + ',' + numeric_command
                            if self.has_security(user,dev_id):
                                return self.update_device(levels, 'command=' + device_command, source, user=user)
                            else:
                                return 'access denied'
                        else:
                            if self.has_security(user,dev_id):
                                return self.update_device(levels, 'command=' + device.DEFAULT_COMMAND, source, user=user)
                            else:
                                return 'access denied'
                    except:
                        if self.has_security(user,dev_id):
                            return self.update_device(levels, 'command=' + device.DEFAULT_COMMAND, source, user=user)
                        else:
                            return 'access denied'
        #Maybe we should ask the internet from here?
        return json.dumps("I'm sorry, can you please repeat that?")

    def get_response(self, method="GET", path=None, type=None, data=None, source=None, user=None):
        response = None
        type = type.lower() if type else self.JSON
        if type == self.WEBSOCKET:
            try:
                data = json.loads(data)
            except Exception as ex:
                pass

            path = data['path']

            try:
                data = data['command']
                if path != 'voice':
                    data = 'command=' + data if data else None
            except Exception as ex:
                #If no command just send back data being requested
                data = None
                type = self.JSON
            method = "post" if data else "get"
        elif path == 'voice':
            data = urllib.parse.unquote(data).replace('&', '').replace('+', ' ').split("command[]=")

        method = method.lower()
        levels = path.split('/')

        if data:
            if isinstance(data, list):
                tdata = []
                for i in data:
                    tdata.append(urllib.parse.unquote(i))
                data = tdata
            else:
                try:
                    data = urllib.parse.unquote(data)
                except:
                    data = urllib.parse.unquote(data.decode())

        f = self.get_map().get((method, levels[0]), None)
        if f:
            response = f(levels, data=data, source=source, user=user)
        elif levels[0].lower() == 'device':
            try:
                if self.has_security(user,levels[1]):
                    response = self.update_device(command=method, levels=levels, source=source, user=user)
                else:
                    return 'access denied'
            except Exception as ex:
                pass
        if type == self.JSON:
            return json.dumps(response)
        elif type == self.WEBSOCKET:
            if method != 'post':
                return json.dumps(response)
            else:
                return json.dumps("success")
        return None

    def get_state_changed_message(self, state, source, prev, device, user):
        if self.has_security(user,device.type_id):
            return json.dumps({
                'id': device.type_id,
                'name': device.name,
                'type_name': device.type_name,
                'state': state,
                'previous_state': prev
            })
        else:
            return "access denied"

    @staticmethod
    def get_devices(path=None, user=None, *args, **kwargs):
        """
        Returns all devices and status in JSON.
        """
        devices = []
        for (k, v) in pytomation_system.get_instances_detail(user).items():
            try:
                v.update({'id': k})
                a = v['instance']
                b = a.state
                del v['instance']
#                devices.append({k: v})
                devices.append(v)
            except Exception as ex:
                pass
#        f = OrderedDict(sorted(devices.items()))
#        odevices = OrderedDict(sorted(f.items(), key=lambda k: k[1]['type_name'])
#                            )
        return devices

    @staticmethod
    def get_device(levels, user, *args, **kwargs):
        """
        Returns one device's status in JSON.
        """
        dev_id = levels[1]
        if PytomationAPI.has_security(user,dev_id):
            detail = pytomation_system.get_instance_detail(dev_id, user)
            detail.update({'id': dev_id})
            del detail['instance']
            return detail
        else:
            return 'access denied'

    def update_device(self, levels, data=None, source=None, user=None, *args, **kwargs):
        """
        Issues command in POST from JSON format.
        """
        dev_id = levels[1]
        if not PytomationAPI.has_security(user,dev_id):
            return 'access denied'
        command = None
        response = None
        if not source:
            source = self

        if data:
            if isinstance(data, list):
                for d in data:
                    e = d.split('=')
                    if e[0] == 'command':
                        command = e[1]
            else:
                e = data.split('=')
                command = e[1]

        # look for tuples in the command and make it a tuple
        if ',' in command:
            e = command.split(',')
            l = []
            # lets convert any strings to int's if we can
            for i in e:
                t = i
                try:
                    t = int(i)
                except:
                    pass
                l.append(t)
            command = tuple(l)
        try:
            detail = pytomation_system.get_instances_detail(user)[dev_id]
            device = detail['instance']
            device.command(command=command, source=source)
            response = PytomationAPI.get_device(levels, user)
        except Exception as ex:
            pass
        return response
