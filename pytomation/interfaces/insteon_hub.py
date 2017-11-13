"""
Insteon Hub Pytomation Interface
Provides an interface to Insteon Hub tested with 2245-222
It may work for the Insteon Hub 2242-222, SmartLinc 2414N, 
    or other hub with a HTTP local API. 
    However, it has not been tested with these hubs

This interface combines code copied from the InsteonPLM insterface and
sections of the InsteonLocal library code available at 
https://github.com/phareous/insteonlocal 

Love GPL -- No need to recreate great work

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>

Author(s):
Based on https://github.com/phareous/insteonlocal created by
    Michael Long <mplong@gmail.com>

Based on InsteonPLN created by
    Pyjamasam@github <>
    Jason Sharpee <jason@sharpee.com>  http://www.sharpee.com
    George Farris <farrisg@gmsys.com>
    
    Which was based loosely on the Insteon_PLM.pm code:
    -       Expanded by Gregg Liming <gregg@limings.net>

This file's authors
David Heaps - <king.dopey.10111@gmail.com>
"""
from .common import Interface, Command
from .ha_interface import HAInterface
from time import sleep
from collections import OrderedDict
from io import StringIO
import pprint
import pkg_resources
import json

def simpleMap(value, in_min, in_max, out_min, out_max):
    #stolen from the arduino implimentation.  I am sure there is a nice python way to do it, but I have yet to stublem across it
    return (float(value) - float(in_min)) * (float(out_max) - float(out_min)) / (float(in_max) - float(in_min)) + float(out_min);

class InsteonHub(HAInterface):
    VERSION = '1.0.0'
    
    def __init__(self, *args, **kwargs):
        super(InsteonHub, self).__init__(*args, **kwargs)
        json_cats = pkg_resources.resource_string(__name__, 'insteon/device_categories.json')
        json_cats_str = json_cats.decode('utf-8')
        self.device_categories = json.loads(json_cats_str)
        self._previous_buffer = ''

        json_models = pkg_resources.resource_string(__name__, 'insteon/device_models.json')
        json_models_str = json_models.decode('utf-8')
        self.device_models = json.loads(json_models_str)

    def _init(self, *args, **kwargs):
        super(InsteonHub, self)._init(*args, **kwargs)        
        self._command_waits = {}
    
    def _wait_for_command(self, deviceId, cmd, cmd2, timeout=3):
        self._command_waits[deviceId][cmd+'ff']= False
        itteration = 0
        while itteration > timeout:
            itteration += 1
            device_waits = self._command_waits.get(deviceId, None)
            if device_waits and not device_waits[cmd+cmd2]:
                sleep(1)
            del device_waits[cmd+cmd2]
            if (len(self._command_waits[deviceId]) == 0):
                del self._command_waits[deviceId]
            return True
    
    def _readInterface(self, lastPacketHash):
        stati = self._get_buffer_status()
        for status in stati['msgs']:
            'Status Update'
            address = status.get('id_from','')
            device_waits = self._command_waits.get(address, None)
            cmd = status.get('cmd1','')
            cmd2 = status.get('cmd2','FF')
            if (device_waits and not device_waits.get(cmd+cmd2,True)):
                device_waits[cmd+cmd2] = True
                
            if (status.get('im_code','') == '50'):
                if (cmd == '11'):
                        self._onCommand(address=address, command=Command.ON)
                elif (cmd == '02'):
                    if (cmd2 == 'FF' or cmd2 == 'FE'): 
                        self._onCommand(address=address, command=Command.ON)
                    elif (cmd2 == '00'):
                        self._onCommand(address=address, command=Command.OFF)
                    else:
                        self._onCommand(address=address, command=(Command.LEVEL,self.hex_to_brightness(cmd2)))
                elif (cmd == '13'):
                    self._onCommand(address=address, command=Command.OFF)
            if (status.get('im_code','') == '62'):
                if (cmd == '13' or cmd == '11'):
                    if (cmd2 == 'FF' or cmd2 == 'FE'): 
                        self._onCommand(address=address, command=Command.ON)
                    elif (cmd2 == '00'):
                        self._onCommand(address=address, command=Command.OFF)
                    else:
                        self._onCommand(address=address, command=(Command.LEVEL,self.hex_to_brightness(cmd2)))
        sleep(1)
    
    def brightness_to_hex(self, level):
        """Convert numeric brightness percentage into hex for insteon"""
        level_int = int(level)
        new_int = int((level_int * 255)/100)
        new_level = format(new_int, '02X')
        self._logger.debug("brightness_to_hex: %s to %s", level, str(new_level))
        return str(new_level)
    
    def hex_to_brightness(self, level_hex):
        """Convert numeric brightness percentage into hex for insteon"""
        level_int = float(int(level_hex, 16))
        new_level = int((level_int / 255.0) * 100.0)
        self._logger.debug("hex_to_brightness: %s to %s", level_hex, str(new_level))
        return str(new_level)


    def _post_direct_command(self, command_url):
        """Send raw command via post"""
        self._logger.info("post_direct_command: %s", command_url)
        return self._interface.write(command_url)


    def _get_direct_command(self, command_url):
        """Send raw command via get"""
        self._logger.info("_get_direct_command: %s", command_url)
        return self._interface.read(command_url)
    
    def _clear_buffer(self):
        """Clear the hub buffer"""
        command_url = '1?XB=M=1'
        response = self._post_direct_command(command_url)
        self._logger.info("clear_buffer: %s", response)
        return response

    def _direct_command(self, device_id, command, command2, extended_payload=None):
        """Wrapper to send posted direct command and get response. Level is 0-100.
        extended_payload is 14 bytes/28 chars..but last 2 chars is a generated checksum so leave off"""
        extended_payload = extended_payload or ''
        if not extended_payload:
            msg_type = '0'
            msg_type_desc = 'Standard'
        else:
            msg_type = '1'
            msg_type_desc = 'Extended'

            extended_payload = extended_payload.ljust(26, '0')

            ### Determine checksum to add onto the payload for I2CS support
            checksum_payload_hex = [int("0x" + extended_payload[i:i+2],16) for i in range(0,len(extended_payload)-1,2)]
            checksum_payload_hex.insert(0, int("0x" + command2, 16))
            checksum_payload_hex.insert(0, int("0x" + command, 16))

            # Get sum of all hex bytes
            bytessum = 0
            for ch in checksum_payload_hex:
                bytessum += ch
            bytessumStr = hex(bytessum)

            # Get last byte of the bytessum
            lastByte = bytessumStr[-2:]
            lastByte = '0x' + lastByte.zfill(2)
            # Determine compliment of last byte
            lastByteHex = int(lastByte, 16)
            lastCompliment = lastByteHex ^ 0xFF
            # Add one to create checksum
            checksum = hex(lastCompliment + 0x01)
            # Remove 0x prefix
            checksum_final = (format(int(checksum, 16), 'x'))
            checksum_final = checksum_final.upper()
            #print("final checksum")
            #pprint.pprint(checksum_final)
            extended_payload = extended_payload + checksum_final

        self._logger.info("_direct_command: Device: %s Command: %s Command 2: %s Extended: %s MsgType: %s", device_id, command, command2, extended_payload, msg_type_desc)
        device_id = device_id.upper()
        command_url = ('3?' + "0262"
                       + device_id + msg_type + "F"
                       + command + command2 + extended_payload + "=I=3")
        return self._post_direct_command(command_url)


    def _direct_command_hub(self, command):
        """Send direct hub command"""
        self._logger.info("direct_command_hub: Command %s", command)
        command_url = ('3?' + command + "=I=3")
        return self._post_direct_command(command_url)


    def _direct_command_short(self, command):
        """Wrapper for short-form commands (doesn't need device id or flags byte)"""
        self._logger.info("direct_command_short: Command %s", command)
        command_url = ('3?' + command + "=I=0")
        return self._post_direct_command(command_url)
    
    def _get_buffer_status(self):
        """Main method to read from buffer. Optionally pass in device to
        only get response from that device"""

        # only used if device_from passed in
        return_record = OrderedDict()
        return_record['success'] = False
        return_record['error'] = True

        command_url = 'buffstatus.xml'
        self._logger.info("get_buffer_status: %s", command_url)

        raw_text = self._get_direct_command(command_url)
        raw_text = raw_text.replace('<response><BS>', '')
        raw_text = raw_text.replace('</BS></response>', '')
        raw_text = raw_text.strip()
        buffer_length = len(raw_text)
        self._logger.info('get_buffer_status: Got raw text with size %s and contents: %s',
                         buffer_length, raw_text)

        if buffer_length == 202:
            # 2015 hub
            # the last byte in the buffer indicates where it stopped writing.
            # checking for text after that position would show if the buffer
            # has overlapped and allow ignoring the old stuff after
            buffer_end = raw_text[-2:]
            buffer_end_int = int(buffer_end, 16)
            raw_text = raw_text[0:buffer_end_int]
            
        full_buffer = raw_text
        raw_text = raw_text.replace(self._previous_buffer, '')
        self._previous_buffer = full_buffer
        self._logger.info('bufferEnd hex %s dec %s', buffer_end, buffer_end_int)
        self._logger.info('get_buffer_status: non wrapped %s', raw_text)
        
        buffer_status = OrderedDict()

        buffer_status['error'] = False
        buffer_status['success'] = True
        buffer_status['message'] = ''
        buffer_status['msgs'] = []

        buffer_contents = StringIO(raw_text)
        while True:

            msg = buffer_contents.read(4)
            if (len(msg) < 4) or (msg == '') or (msg == '0000'):
                break

            #im_start = msg[0:2]
            im_cmd = msg[2:4]

            response_record = OrderedDict()
            response_record['im_code'] = im_cmd
            # Standard Message Received
            if im_cmd == '50':
                msg = msg + buffer_contents.read(18)
                response_record['im_code_desc'] = 'Standard Message Received'
                response_record['raw'] = msg
                response_record['id_from'] = msg[4:10]
                # direct id high, group group_id, broadcast cat
                response_record['id_high'] = msg[10:12]
                # direct id mid, broadcast subcat
                response_record['id_mid'] = msg[12:14]
                # direct id low, broadcast firmware version
                response_record['id_low'] = msg[14:16]
                # 2 ack, 8 broadcast
                response_record['flag1'] = msg[16:17]
                # hop count B
                response_record['flag2'] = msg[17:18]
                # direct cmd, broadcast 01, status db delta
                response_record['cmd1'] = msg[18:20]
                # direct cmd 2, broadcast 00, status on level
                response_record['cmd2'] = msg[20:22]

            # Extended Mesage Received
            elif im_cmd == '51':
                msg = msg + buffer_contents.read(46)

                response_record['im_code_desc'] = 'Extended Message Received'
                response_record['raw'] = msg
                response_record['id_from'] = msg[4:10]
                # direct id high, group group_id, broadcast cat
                response_record['id_high'] = msg[10:12]
                # direct id mid, broadcast subcat
                response_record['id_mid'] = msg[12:14]
                # direct id low, broadcast firmware version
                response_record['id_low'] = msg[14:16]
                # 2 ack, 8 broadcast + hop count B
                response_record['flags'] = msg[16:18]
                # direct cmd, broadcast 01, status db delta
                response_record['cmd1'] = msg[18:20]
                # direct cmd 2, broadcast 00, status on level
                response_record['cmd2'] = msg[20:22]
                response_record['user_data_1'] = msg[22:24]
                response_record['user_data_2'] = msg[24:26]
                response_record['user_data_3'] = msg[26:28]
                response_record['user_data_4'] = msg[28:30]
                response_record['user_data_5'] = msg[30:32]
                response_record['user_data_6'] = msg[32:34]
                response_record['user_data_7'] = msg[34:36]
                response_record['user_data_8'] = msg[36:38]
                response_record['user_data_9'] = msg[38:40]
                response_record['user_data_10'] = msg[40:42]
                response_record['user_data_11'] = msg[42:44]
                response_record['user_data_12'] = msg[44:46]
                response_record['user_data_13'] = msg[46:48]
                response_record['user_data_14'] = msg[48:50]

            # X10 Received (not implemented)
            elif im_cmd == '52':
                self._logger.error('Not implemented handling of 0252 X10 Received')
                break

            # ALL-Linking Completed
            elif im_cmd == '53':
                msg = msg = buffer_contents.read(16)

                response_record['im_code_desc'] = 'ALL-Linking Completed'
                response_record['raw'] = msg
                response_record['link_status'] = msg[4:6]

                if response_record['link_status'] == '00':
                    response_record['link_status_desc'] = 'IM is Responder'
                elif response_record['link_status'] == '01':
                    response_record['link_status_desc'] = 'IM is Controller'
                elif response_record['link_status'] == 'FF':
                    response_record['link_status_desc'] = 'Link Deleted'

                response_record['group'] = msg[6:8]
                response_record['id_high'] = msg[8:10]
                response_record['id_mid'] = msg[10:12]
                response_record['id_low'] = msg[12:14]
                response_record['dev_cat'] = msg[14:16]
                response_record['dev_subcat'] = msg[16:18]
                response_record['dev_firmware_rev'] = msg[18:20] # or FF for newer devices

            # Button Event Report
            elif im_cmd == '54':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Button Event Report'
                response_record['raw'] = msg
                response_record['report_type'] = msg[4:6]
                if response_record['report_type'] == "02":
                    response_record['report_type_desc'] = "IM's SET Button tapped"
                elif response_record['report_type'] == "03":
                    response_record['report_type_desc'] = "IM's SET Button held"
                elif response_record['report_type'] == "04":
                    response_record['report_type_desc'] = "IM's SET Button released after hold"
                elif response_record['report_type'] == "12":
                    response_record['report_type_desc'] = "IM's Button 2 tapped"
                elif response_record['report_type'] == "13":
                    response_record['report_type_desc'] = "IM's Button 2 held"
                elif response_record['report_type'] == "14":
                    response_record['report_type_desc'] = "IM's Button 2 released after hold"
                elif response_record['report_type'] == "22":
                    response_record['report_type_desc'] = "IM's Button 3 tapped"
                elif response_record['report_type'] == "23":
                    response_record['report_type_desc'] = "IM's Button 3 held"
                elif response_record['report_type'] == "24":
                    response_record['report_type_desc'] = "IM's Button 3 released after hold"

            # User Reset Detected
            elif im_cmd == '55':
                response_record['im_code_desc'] = 'User Reset Detected'
                response_record['raw'] = msg
                response_record['im_code_desc2'] = "User pushed and held IM's " \
                                                   "SET Button on power up"

            # ALL-Link Cleanup Failure Report
            elif im_cmd == '56':
                msg = msg + buffer_contents.read(10)

                response_record['im_code_desc'] = 'ALL-Link Cleanup Failure Report'
                response_record['raw'] = msg
                response_record['group'] = msg[4:6]
                # 01 means member did not acknlowedge all-link cleanup cmd
                response_record['ack'] = msg[6:8]
                response_record['id_high'] = msg[8:10]
                response_record['id_mid'] = msg[10:12]
                response_record['id_low'] = msg[12:14]

            # ALL-Link Record Response
            elif im_cmd == '57':
                msg = msg + buffer_contents.read(20)

                response_record['im_code_desc'] = 'ALL-Link Record Response'
                response_record['raw'] = msg
                response_record['flags'] = msg[4:6] # hub dev manual p 39
                response_record['group'] = msg[6:8]
                response_record['id_high'] = msg[8:10]
                response_record['id_mid'] = msg[10:12]
                response_record['id_low'] = msg[12:14]
                response_record['link_data_1'] = msg[14:16]
                response_record['link_data_2'] = msg[16:18]
                response_record['link_data_3'] = msg[18:20]

            # ALL-Link Cleanup Status Report
            elif im_cmd == '58':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'ALL-Link Cleanup Status Report'
                response_record['raw'] = msg
                response_record['cleanup_status'] = msg[4:6]
                if response_record['cleanup_status'] == '06':
                    response_record['cleanup_status_desc'] = 'ALL-Link Cleanup ' \
                                                            'sequence completed'
                elif response_record['cleanup_status'] == '15':
                    response_record['cleanup_status_desc'] = 'ALL-Link Cleanup ' \
                                                             'sequence aborted due ' \
                                                             'to INSTEON traffic'

            # Database Record Found
            elif im_cmd == '59':
                msg = msg + buffer_contents.read(18)

                response_record['im_code_desc'] = 'Database Record Found'
                response_record['raw'] = msg
                response_record['address_low'] = msg[4:6]
                response_record['record_flags'] = msg[6:8]
                response_record['group'] = msg[8:10]
                response_record['id_high'] = msg[10:12]
                response_record['id_mid'] = msg[12:14]
                response_record['id_low'] = msg[14:16]
                response_record['link_data_1'] = msg[16:18]
                response_record['link_data_2'] = msg[18:20]
                response_record['link_data_3'] = msg[20:22]

            # Get IM Info
            elif im_cmd == '60':
                msg = msg + buffer_contents.read(14)

                response_record['im_code_desc'] = 'Get IM Info'
                response_record['raw'] = msg
                response_record['id_high'] = msg[4:6]
                response_record['id_mid'] = msg[6:8]
                response_record['id_low'] = msg[8:10]
                response_record['dev_cat'] = msg[10:12]
                response_record['dev_subcat'] = msg[12:14]
                response_record['dev_firmware_rev'] = msg[14:16]
                response_record['ack_or_nak'] = msg[16:18] # 06 ack

            # Send ALL-Link Command
            elif im_cmd == '61':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc'] = 'Send ALL-Link Command'
                response_record['raw'] = msg
                response_record['group'] = msg[4:6]
                response_record['cmd'] = msg[6:8]
                response_record['broadcast_cmd2'] = msg[8:10] # FF or 00
                response_record['ack_or_nak'] = msg[10:12] # 06 ack

            # Send Message (Pass through command to PLM)
            elif im_cmd == '62':
                msg = msg + buffer_contents.read(8)
                response_record['id_from'] = msg[4:10]
                response_record['flags'] = msg[10:12]

                # Standard Message
                if response_record['flags'][0] == '0':
                    response_record['im_code_desc'] = 'Send Standard Message'
                    msg = msg + buffer_contents.read(6)
                    response_record['cmd1'] = msg[12:14]
                    response_record['cmd2'] = msg[14:16]
                    response_record['ack_or_nak'] = msg[16:18] # 06 ack 15 nak

                # Extended Message
                elif response_record['flags'][0] == '1':
                    response_record['im_code_desc'] = 'Send Extended Message'
                    msg = msg + buffer_contents.read(34)
                    response_record['cmd1'] = msg[12:14]
                    response_record['cmd2'] = msg[14:16]
                    response_record['user_data_1'] = msg[16:18]
                    response_record['user_data_2'] = msg[18:20]
                    response_record['user_data_3'] = msg[20:22]
                    response_record['user_data_4'] = msg[22:24]
                    response_record['user_data_5'] = msg[24:26]
                    response_record['user_data_6'] = msg[26:28]
                    response_record['user_data_7'] = msg[28:30]
                    response_record['user_data_8'] = msg[30:32]
                    response_record['user_data_9'] = msg[32:34]
                    response_record['user_data_10'] = msg[34:36]
                    response_record['user_data_11'] = msg[36:38]
                    response_record['user_data_12'] = msg[38:40]
                    response_record['user_data_13'] = msg[40:42]
                    response_record['user_data_14'] = msg[42:44]
                    response_record['ack_or_nak'] = msg[44:46] # 06 ack 15 nak

                # Not implemented
                else:
                    self._logger.error('Not implemented, message flag %s' % response_record['flags'])

                response_record['raw'] = msg

            # Send X10 (not implemented)
            elif im_cmd == '63':
                self._logger.error('Not implemented handling of 0263 Send X10')
                break

            # Start ALL-Linking
            elif im_cmd == '64':
                msg = msg + buffer_contents.read(6)

                response_record['im_code_desc'] = 'Start ALL-Linking'
                response_record['raw'] = msg
                response_record['link_type'] = msg[4:6]

                if response_record['link_type'] == '00':
                    response_record['link_type_desc'] = 'IM is Responder'
                elif response_record['link_type'] == '01':
                    response_record['link_type_desc'] = 'IM is Controller'
                elif response_record['link_type'] == '03':
                    response_record['link_type_desc'] = 'IM is Either Responder ' \
                                                        'or Controller'
                elif response_record['link_type'] == 'FF':
                    response_record['link_type_desc'] = 'Link Deleted'

                response_record['group'] = msg[6:8]
                response_record['ack_or_nak'] = msg[8:10] # 06 ack 15 nak

            # Cancel ALL-Linking
            elif im_cmd == '65':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Cancel ALL-Linking'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Set Host Device Category
            elif im_cmd == '66':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc'] = 'Set Host Device Category'
                response_record['raw'] = msg
                response_record['dev_cat'] = msg[4:6]
                response_record['dev_subcat'] = msg[6:8]
                response_record['dev_firmware_rev'] = msg[8:10] # or 00
                response_record['ack_or_nak'] = msg[10:12] # 06 ack 15 nak

            # Reset the IM
            elif im_cmd == '67':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Reset the IM'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Set INSTEON ACK Message Byte
            elif im_cmd == '68':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc'] = 'Set INSTEON ACK Message Byte'
                response_record['raw'] = msg
                response_record['cmd2_data'] = msg[4:6]
                response_record['ack_or_nak'] = msg[6:8] # 06 ack 15 nak

            # Get First ALL-Link Record
            elif im_cmd == '69':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Get First ALL-Link Record'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Get Next ALL-Link Record
            elif im_cmd == '6A':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Get Next ALL-Link Record'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Set IM Configuration
            elif im_cmd == '6B':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc'] = 'Set IM Configuration'
                response_record['raw'] = msg
                response_record['im_cfg_flags'] = msg[4:6]
                response_record['ack_or_nak'] = msg[6:8] # 06 ack 15 nak

            # Get ALL-Link Record for Sender
            elif im_cmd == '6C':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Get ALL-Link Record for Sender'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # LED On
            elif im_cmd == '6D':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'LED On'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # LED Off
            elif im_cmd == '6E':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'LED Off'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Manage ALL-Link Record
            elif im_cmd == '6F':
                msg = msg + buffer_contents.read(20)

                response_record['im_code_desc'] = 'Manage ALL-Link Record'
                response_record['raw'] = msg
                response_record['ctrl_flags'] = msg[4:6]
                response_record['record_flags'] = msg[6:8]
                response_record['group'] = msg[8:10]
                response_record['id_high'] = msg[10:12]
                response_record['id_mid'] = msg[12:14]
                response_record['id_low'] = msg[14:16]
                response_record['link_data_1'] = msg[16:18]
                response_record['link_data_2'] = msg[18:20]
                response_record['link_data_3'] = msg[20:22]
                response_record['ack_or_nak'] = msg[22:24] # 06 ack

            # Set INSTEON ACK Message Two Bytes
            elif im_cmd == '71':
                msg = msg + buffer_contents.read(6)

                response_record['im_code_desc'] = 'Set INSTEON ACK Message Two Bytes'
                response_record['raw'] = msg
                response_record['cmd1_data'] = msg[4:6]
                response_record['cmd2_data'] = msg[6:8]
                response_record['ack_or_nak'] = msg[8:10] # 06 ack

            # RF Sleep
            elif im_cmd == '72':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'RF Sleep'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack

            # Get IM Configuration
            elif im_cmd == '73':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc'] = 'Get IM Configuration'
                response_record['raw'] = msg
                response_record['im_cfg_flags'] = msg[4:6]
                response_record['spare1'] = msg[6:8]
                response_record['spare2'] = msg[8:10]
                response_record['ack_or_nak'] = msg[10:12] # 06 ack

            # Cancel Cleanup
            elif im_cmd == '74':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Cancel Cleanup'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Read 8 bytes from Database
            elif im_cmd == '75':
                msg = msg + buffer_contents.read(30)

                response_record['im_code_desc'] = 'Read 8 bytes from Database'
                response_record['raw'] = msg
                response_record['db_addr_high'] = msg[4:6]
                response_record['db_addr_low'] = msg[6:8] # low nibble F, or 8
                response_record['ack_or_nak'] = msg[8:10] # 06 ack
                response_record['record'] = msg[10:34] # database record founnd
                                                       # response 12 bytes

            # Write 8 bytes to Database
            elif im_cmd == '76':
                msg = msg + buffer_contents.read(22)

                response_record['im_code_desc'] = 'Write 8 bytes to Database'
                response_record['raw'] = msg
                response_record['db_addr_high'] = msg[4:6]
                response_record['db_addr_low'] = msg[6:8] # low nibble F, or 8
                response_record['record_flags'] = msg[8:10]
                response_record['group'] = msg[10:12]
                response_record['id_high'] = msg[12:14]
                response_record['id_middle'] = msg[14:16]
                response_record['id_low'] = msg[16:18]
                response_record['link_data_1'] = msg[18:20]
                response_record['link_data_2'] = msg[20:22]
                response_record['link_data_3'] = msg[22:24]
                response_record['ack_or_nak'] = msg[24:26] # 06 ac

            # Beep
            elif im_cmd == '77':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Beep'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack 15 nak

            # Set Status
            # IM reports Status in cmd2 of direct Status Request command (19)
            elif im_cmd == '78':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Set Status'
                response_record['raw'] = msg
                response_record['ack_or_nak'] = msg[4:6] # 06 ack

            # Set Database Link Data for Next Link
            elif im_cmd == '79':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc'] = 'Set Database Link Data for Next Link'
                response_record['raw'] = msg
                response_record['link_data_1'] = msg[4:6]
                response_record['link_data_2'] = msg[6:8]
                response_record['link_data_3'] = msg[8:10]
                response_record['ack_or_nak'] = msg[10:12] # 06 ack

            # Set Application Retries for New Links
            elif im_cmd == '7A':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc'] = 'Set Application Retries for New Links'
                response_record['raw'] = msg
                response_record['num_retries'] = msg[4:6]
                response_record['ack_or_nak'] = msg[6:8] # 06 ack

            # Set RF Frequency Offset
            elif im_cmd == '7B':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc'] = 'Set RF Frequency Offset'
                response_record['raw'] = msg
                response_record['rf_freq_offset'] = msg[4:6]
                response_record['ack_or_nak'] = msg[6:8] # 06 ack

            # Set Acknowledge for TempLinc Command (not implemented)
            elif im_cmd == '7C':
                self._logger.error('Not implemented handling of 027C Set '
                                  'Acknowledge for TempLinc command')
                break

            if response_record.get('ack_or_nak', '') == '15':
                buffer_status['error'] = True
                buffer_status['success'] = False
                buffer_status['message'] = 'Device returned nak'

            buffer_status['msgs'].append(response_record)

        #Remove unfinished command chars from buffer to clear
        unfinished_commands_chars = -len(buffer_contents.read())
        if unfinished_commands_chars:
            self._previous_buffer = self._previous_buffer[:unfinished_commands_chars] 
            
        buffer_contents.close()
        #pprint.pprint(buffer_status)
        self._logger.debug("get_buffer_status: %s", pprint.pformat(buffer_status))

        return buffer_status

    def on(self, deviceId, fast=None, timeout=3):
        if fast == 'fast':
            cmd = '12'
        else:
            cmd = '11'
        self._direct_command(deviceId, cmd, 'ff')
        return self._wait_for_command(deviceId, cmd, 'ff', timeout)

    def off(self, deviceId, fast=None, timeout=3):
        if fast == 'fast':
            cmd = '14'
        else:
            cmd = '13'
        self._direct_command(deviceId, cmd, '00')
        return self._wait_for_command(deviceId, cmd, '00', timeout)    
      
    # if rate the bits 0-3 is 2 x ramprate +1, bits 4-7 on level + 0x0F
    def level(self, deviceId, level, rate=None, timeout=3):
        if level > 100 or level <0:
            self._logger.error("{name} cannot set light level {level} beyond 1-15".format(
                                                                                    name=self.name,
                                                                                    level=level,
                                                                                     ))
            return
        else:
            if rate == None:
                # make it 0 to 255                                                                                     
                level = int((int(level) / 100.0) * int(0xFF))
                self._direct_command(deviceId, '11', '%02x' % level)
                return self._wait_for_command(deviceId, '11', '%02x' % level, timeout)
            else:
                if rate > 15 or rate <1:
                    self._logger.error("{name} cannot set light ramp rate {rate} beyond 1-15".format(
                                                                                    name=self.name,
                                                                                    level=level,
                                                                                     ))
                    return
                else:
                    lev = int(simpleMap(level, 1, 100, 1, 15))                                                                                     
                    levelramp = (int(lev) << 4) + rate
                    self._direct_command(deviceId, '2E', '%02x' % levelramp)
                    return self._wait_for_command(deviceId, '2E', '%02x' % levelramp, timeout)
    
    def status(self, deviceId, return_led='0', timeout=3):
        self._direct_command(deviceId, '19', return_led)
        return self._wait_for_command(deviceId, '19', return_led, timeout)

    def version(self):
        self._logger.info("Insteon Hub Pytomation Wrapper Interface version " + self.VERSION + '\n')