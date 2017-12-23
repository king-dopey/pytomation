import time
from .pytomation_object import PytomationObject
from pytomation.utility import PeriodicTimer
from . import config
#from ..utility.manhole import Manhole

def get_instances():
    return PytomationObject.instances

def get_instances_detail(user=config.admin_user):
    details = {}
    sysDevices = {}
    if user.is_admin:
        sysDevices = PytomationObject.instances
    else:
        sysDevices = user.accessible_devices
    for pyObject in sysDevices.values():
        object_detail = {'instance': pyObject,
                         'name': pyObject.name,
                         'type_name': pyObject.type_name,
                         }
        try:
            object_detail.update({'commands': pyObject.COMMANDS})
            object_detail.update({'state': pyObject.state})
            object_detail.update({'devices': pyObject.device_list()})
        except Exception as ex:
            # Not a state device
            pass
        details.update({
                       pyObject.type_id: object_detail,
                       })

    return details

def get_instance_detail(object_id,user=config.admin_user):
    pyObject = []
    if user.is_admin:
        pyObject = PytomationObject.instances[object_id]
    else:
        pyObject = PytomationObject.users[object_id]
    
    object_detail = {'instance': pyObject,
                     'name': pyObject.name,
                     'type_name': pyObject.type_name,
                     }
    try:
        object_detail.update({'commands': pyObject.COMMANDS})
        object_detail.update({'state': pyObject.state})
        object_detail.update({'devices': pyObject.device_list()})
    except Exception as ex:
        # Not a state device
        pass

    return object_detail

def start(loop_action=None, loop_time=1, admin_user=None, admin_password=None, telnet_port=None):
    if loop_action:
        # run the loop for startup once
        loop_action(startup=True)
        # run periodically from now on
        myLooper = PeriodicTimer(loop_time) # loop every 1 sec
        myLooper.action(loop_action, None, {'startup': False} )
        myLooper.start()

    if telnet_port:
        from pytomation.utility import Manhole #must be enabled in pytomation.utility.__init__.py
        Manhole().start(user=admin_user, password=admin_password, port=telnet_port, instances=get_instances_detail())

    while True: time.sleep(1)
