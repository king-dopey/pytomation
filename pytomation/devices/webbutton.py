from pytomation.devices import InterfaceDevice, State
from pytomation.interfaces import Command

class WebButton(InterfaceDevice):
    STATES = [State.UNKNOWN, State.OFF, State.ON]
    COMMANDS = [Command.ON, Command.OFF, Command.STATUS]
    
    
