#!/usr/bin/python

import os
from pytomation.common import config, pytomation_system, User

INSTANCES_DIR = './instances'


if __name__ == "__main__":
    print('Pytomation')
    scripts = []
    script_names = os.listdir(INSTANCES_DIR)
    for script_name in script_names:
        if script_name.lower()[-3:]==".py" and script_name.lower() != "__init__.py":
            try:
                module = "instances.%s" % script_name[0:len(script_name)-3]
                print("Found Instance Script: " + module)
                scripts.append( __import__(module, fromlist=['instances']))
            except ImportError as ex:
                print('Error' + str(ex))
    print("Total Scripts: " + str(len(scripts)))

    if len(scripts) > 0:
        # Start the whole system.  pytomation.common.system.start()
        try:
            loop_action=scripts[0].MainLoop
        except AttributeError as ex:
            loop_action=None

        #Create admin user
        if config.admin_user and config.admin_password:
            User(username=config.admin_user,password=config.admin_password, is_admin=True)

        pytomation_system.start(
            loop_action=loop_action,
            loop_time=config.loop_time, # Loop every 1 sec
            admin_user=config.admin_user,
            admin_password=config.admin_password,
            telnet_port=config.telnet_port
        )
    else:
        print("No Scripts found. Exiting")
