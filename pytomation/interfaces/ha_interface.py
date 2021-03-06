'''
File:
        ha_interface.py

Description:


Author(s):
         Pyjamasam@github <>
         Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com

License:
    This free software is licensed under the terms of the GNU public license, Version 1

Usage:


Example:

Notes:


Created on Mar 26, 2011
'''
import threading
import time
import binascii
from collections import deque

from .common import *
from pytomation.common.pytomation_object import PytomationObject

class HAInterface(AsynchronousInterface, PytomationObject):
    "Base protocol interface"

    MODEM_PREFIX = '\x02'

    def __init__(self, interface, *args, **kwargs):
        kwargs.update({'interface': interface})
        #self._po_common(*args, **kwargs)
        super(HAInterface, self).__init__(*args, **kwargs)


    def _init(self, *args, **kwargs):
        super(HAInterface, self)._init(*args, **kwargs)
        self._shutdownEvent = threading.Event()
        self._interfaceRunningEvent = threading.Event()

        self._commandLock = threading.Lock()
        self._outboundQueue = deque()
        self._outboundCommandDetails = dict()
        self._retryCount = dict()

        self._pendingCommandDetails = dict()

        self._commandReturnData = dict()

        self._intersend_delay = 0.15  # 150 ms between network sends
        self._lastSendTime = 0

        self._interface = kwargs['interface']
        self._commandDelegates = []
        self._devices = []
        self._lastPacketHash = None

    def shutdown(self):
        if self._interfaceRunningEvent.isSet():
            self._shutdownEvent.set()

            #wait 2 seconds for the interface to shut down
            self._interfaceRunningEvent.wait(2000)

    def run(self, *args, **kwargs):
        self._interfaceRunningEvent.set()

        #for checking for duplicate messages received in a row

        while not self._shutdownEvent.isSet():
            try:
                self._readInterface(self._lastPacketHash)
                self._writeInterface()
            except Exception as ex:
                self._logger.error("Problem with interface: " + str(ex))

        self._interfaceRunningEvent.clear()

    def onCommand(self, callback=None, address=None, device=None):
        # Register a device for notification of commands
        if not device:
            self._commandDelegates.append({
                                       'address': address,
                                       'callback': callback,
                                       })
        else:
            self._devices.append(device)

    def _onCommand(self, command=None, address=None):
        # Received command from interface and this will delegate to subscribers
        self._logger.debug("Received Command:" + str(address) + ":" + str(command))
        self._logger.debug('Delegates for Command: ' + str(self._commandDelegates))

        addressC = address
        try:
            addressC = addressC.lower()
        except:
            pass
        for commandDelegate in self._commandDelegates:
            addressD = commandDelegate['address']
            try:
                addressD = addressC
            except:
                pass
            if commandDelegate['address'] == None or \
                addressD == addressC:
                commandDelegate['callback'](
                                            command=command,
                                            address=address,
                                            source=self
                                            )
        self._logger.debug('Devices for Command: ' + str(self._devices))
        for device in self._devices:
            if device.addressMatches(address):
                try:
                    device._on_command(
                                       command=command,
                                       address=address,
                                       source=self,
                                       )
                except Exception as ex:
                    device.command(
                                   command=command,
                                   source=self,
                                   address=address)

    def _onState(self, state, address):
        for device in self._devices:
            if device.addressMatches(address):
                try:
                    device.set_state(
                                       state,
                                       address=address,
                                       source=self,
                                       )
                except Exception as ex:
                    self._logger.debug('Could not set state for device: {device}'.format(device=device.name))


    def _sendInterfaceCommand(self, modemCommand,
                          commandDataString=None,
                          extraCommandDetails=None, modemCommandPrefix=None):
        returnValue = False
        try:
            if self._interface.disabled == True:
                return returnValue
        except AttributeError as ex:
            pass

        try:
            if modemCommandPrefix:
                bytesToSend = modemCommandPrefix + modemCommand
            else:
                bytesToSend = modemCommand
            if commandDataString != None:
                bytesToSend += commandDataString

            commandHash = hashPacket(bytesToSend)
            self._commandLock.acquire()
            if commandHash in self._outboundCommandDetails:
                #duplicate command.  Ignore
                pass

            else:
                waitEvent = threading.Event()

                basicCommandDetails = {'bytesToSend': bytesToSend,
                                       'waitEvent': waitEvent,
                                       'modemCommand': modemCommand}

                if extraCommandDetails != None:
                    basicCommandDetails = dict(
                                       list(basicCommandDetails.items()) + \
                                       list(extraCommandDetails.items()))

                self._outboundCommandDetails[commandHash] = basicCommandDetails

                self._outboundQueue.append(commandHash)
                self._retryCount[commandHash] = 0

                self._logger.debug("Queued %s" % commandHash)

                returnValue = {'commandHash': commandHash,
                               'waitEvent': waitEvent}

            self._commandLock.release()

        except Exception as ex:
            print(traceback.format_exc())

        finally:

            #ensure that we unlock the thread lock
            #the code below will ensure that we have a valid lock before we call release
            self._commandLock.acquire(False)
            self._commandLock.release()

        return returnValue

    def _writeInterface(self):
        #check to see if there are any outbound messages to deal with
        self._commandLock.acquire()
        if self._outboundQueue and (len(self._outboundQueue) > 0) and \
            (time.time() - self._lastSendTime > self._intersend_delay):
            commandHash = self._outboundQueue.popleft()

            try:
                commandExecutionDetails = self._outboundCommandDetails[commandHash]
            except Exception as ex:
                self._logger.error('Could not find execution details: {command} {error}'.format(
                                                                                                command=commandHash,
                                                                                                error=str(ex))
                                   )
            else:
                bytesToSend = commandExecutionDetails['bytesToSend']
                try:
                    self._logger.debug("Transmit>" + Conversions.ascii_to_hex(bytesToSend))
                except:
                    self._logger.debug("Transmit>" + str(bytesToSend))

                self._pendingCommandDetails[commandHash] = commandExecutionDetails
                result = self._writeInterfaceFinal(bytesToSend)
                self._lastSendTime = time.time()
                self._logger.debug("TransmitResult>" + str(result))
                del self._outboundCommandDetails[commandHash]
        try:
            self._commandLock.release()
        except Exception as te:
            self._logger.debug("Error trying to release unlocked lock %s" % (str(te)))

    def _writeInterfaceFinal(self, data):
        return self._interface.write(data)

    def _readInterface(self, lastPacketHash):
        response = None
        #check to see if there is anything we need to read
        if self._interface:
            try:
                response = self._interface.read()
            except Exception as ex:
                self._logger.debug("Error reading from interface {interface} exception: {ex}".format(
                                                                                     interface=str(self._interface),
                                                                                     ex=str(ex)
                                                                                     )
                                   )
        try:
            if response and len(response) != 0:
    #            self._logger.debug("[HAInterface-Serial] Response>\n" + hex_dump(response))
                self._logger.debug("Response>" + hex_dump(response) + "<")
                self._onCommand(command=response)
            else:
                #print "Sleeping"
                #X10 is slow.  Need to adjust based on protocol sent.  Or pay attention to NAK and auto adjust
                #time.sleep(0.1)
                time.sleep(0.5)
        except TypeError as ex:
            pass

    def _resend_failed_command(self, commandHash, commandDetails):
        """Resets the queues to resend a command
        This function assumes a thread lock has already been acquired."""

        if (self._retryCount[commandHash] < 5):
            self._logger.debug("Timed out for %s - Requeueing (already had %d retries)" % \
                                               (commandHash, self._retryCount[commandHash]))
            try:
                self._outboundQueue.remove(commandHash)
            except:
                pass
            try:
                del self._outboundCommandDetails[commandHash]
            except:
                pass
            self._outboundCommandDetails[commandHash] = commandDetails
            del self._pendingCommandDetails[commandHash]
            self._outboundQueue.append(commandHash)
            self._retryCount[commandHash] += 1
        elif(self._retryCount[commandHash] >= 5):
            self._logger.debug("Timed out for %s - Failing Command (already had %d retries)" % \
                               (commandHash, self._retryCount[commandHash]))
            try:
                self._outboundQueue.remove(commandHash)
            except:
                pass
            try:
                del self._outboundCommandDetails[commandHash]
            except:
                pass
            del self._pendingCommandDetails[commandHash]
            return False
        return True

    def _waitForCommandToFinish(self, commandExecutionDetails, timeout=None):

        if type(commandExecutionDetails) != type(dict()):
            self._logger.error("Unable to wait without a valid commandExecutionDetails parameter")
            return False
        # commandExecutionDetails
        # {'commandHash': '3f15d2889dcdb1ee72c9dee08ea2c895', 'waitEvent': <threading.Event object at 0x7feab411cc88>}

        waitEvent = commandExecutionDetails['waitEvent']
        commandHash = commandExecutionDetails['commandHash']

        realTimeout = 2  # default timeout of 2 seconds
        if timeout:
            realTimeout = timeout

        timeoutOccured = not waitEvent.wait(realTimeout)

        # print("timeout", timeoutOccured)
        if not timeoutOccured:
            # print("commandhash  --  self._commandReturnData", commandHash, self._commandReturnData)

            if commandHash in self._commandReturnData:
                return self._commandReturnData[commandHash]
            else:
                return True
        else:
            #re-queue the command to try again
            self._commandLock.acquire()

            if self._retryCount[commandHash] >= 5:
                #too many retries.  Bail out
                self._commandLock.release()
                return False

            self._logger.debug("Timed out for %s - Requeueing (already had %d retries)" % \
                (commandHash, self._retryCount[commandHash]))

            requiresRetry = True
            if commandHash in self._pendingCommandDetails:
                self._outboundCommandDetails[commandHash] = \
                    self._pendingCommandDetails[commandHash]

                del self._pendingCommandDetails[commandHash]

                self._outboundQueue.append(commandHash)
                self._retryCount[commandHash] += 1
            else:
                self._logger.debug("Interesting.  timed out for %s, but there are no pending command details" % commandHash)
                #to prevent a huge loop here we bail out
                requiresRetry = False

            try:
                self._logger.debug("Removing Lock " + str( self._commandLock))
                self._commandLock.release()
            except:
                self._logger.error("Could not release Lock! " + str(self._commandLock))

            if requiresRetry:
                return self._waitForCommandToFinish(commandExecutionDetails,
                                                    timeout=timeout)
            else:
                return False

    @property
    def name(self):
        return self.name_ex

    @name.setter
    def name(self, value):
        self.name_ex = value
        return self.name_ex

    def update_status(self):
        for d in self._devices:
            self.status(d.address)

    def status(self, address=None):
        return None
