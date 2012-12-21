import time

from unittest import TestCase
from datetime import datetime

from pytomation.devices import State2Device, State2
from pytomation.interfaces import Command

class State2Tests(TestCase):
    def test_instance(self):
        self.assertIsNotNone(State2Device())

    def test_unknown_initial(self):
        self.assertEqual(State2Device().state, State2.UNKNOWN)

    def test_initial(self):
        device = State2Device(
                        initial=State2.ON
                        )
        self.assertEqual(device.state, State2.ON)
        
    def test_command_on(self):
        device = State2Device()
        self.assertEqual(device.state, State2.UNKNOWN)
        device.on()
        self.assertEqual(device.state, State2.ON)
    
    def test_command_subcommand(self):
        device = State2Device()
        self.assertEqual(device.state, State2.UNKNOWN)
        device.level(80)
        self.assertEqual(device.state, (State2.LEVEL, 80))
        
    def test_time_off(self):
        now = datetime.now()
        hours, mins, secs = now.timetuple()[3:6]
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        trigger_time1 = '{h}:{m}:{s}'.format(
                                             h=hours,
                                             m=mins,
                                             s=secs,
                                                 )
        print 'Trigger Time' + trigger_time1
        secs = (secs + 2) % 60
        mins += (secs + 2) / 60
        trigger_time2 = '{h}:{m}:{s}'.format(
                                             h=hours,
                                             m=mins,
                                             s=secs,
                                                 )
        print 'Trigger Time' + trigger_time2
        device = State2Device(
                              time={
                                    'command': Command.OFF,
                                    'time': (trigger_time1, trigger_time2),
                                    }
                              )
        self.assertEqual(device.state, State2.UNKNOWN)
        time.sleep(3)
        print datetime.now()
        self.assertEqual(device.state, State2.OFF)
        device.on()
        time.sleep(3)
        print datetime.now()
        print device._times
        self.assertEqual(device.state, State2.OFF)
        
    def test_binding(self):
        d1 = State2Device()
        d1.off()
        d2 = State2Device(devices=d1)
        self.assertEqual(d2.state, State2.UNKNOWN)
        d1.on()
        self.assertEqual(d2.state, State2.ON)
        
        