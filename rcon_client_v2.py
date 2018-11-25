#!/usr/bin/env python3

# This is an RCON client for games using the Source RCON protocol.
# Pass a RCON command via argument (or don't to use interactive mode)

# Copyright 2015 Dunto, see below for license information.
# This script was written as a quick solution to a personal requirement,
# it may or may not be improved on as time passes.  I make no promises
# as to whether it will work properly for you or not.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>


##Customized by Ekagrah, updated for python3
##Ark Help from http://www.ark-survival.net/en/2015/07/09/rcon-tutorial/
## and https://cjsavage.com/guides/linux/ark-dedicated-save-on-exit.html
## and https://developer.valvesoftware.com/wiki/Source_RCON_Protocol


import socket
import struct
import sys

##------Start user editable section------##
RCON_SERVER_HOSTNAME = 'serverip or dns'
RCON_SERVER_PORT = '27015'
RCON_PASSWORD = 'secret
# server response timeout in seconds, don't go too high
RCON_SERVER_TIMEOUT = 3
##------End user editable section------##


MESSAGE_TYPE_AUTH = 3
MESSAGE_TYPE_AUTH_RESP = 2
MESSAGE_TYPE_COMMAND = 2
MESSAGE_TYPE_RESP = 0
MESSAGE_ID = 0

def sendMessage(sock, command_string, message_type):
    "Packages up a command string into a message and sends it"
    try:
        command_len = len(command_string)
        byte_command = command_string.encode(encoding='ascii')
        #message in bytes, id=4 + type=4 + body=variable + null terminator=2 (1 for python string and 1 for message terminator)
        message_size = (4 + 4 + command_len + 2)
        message_format = ''.join(['=lll', str(command_len), 's2s'])
        # change formatting logic for struct.pack, see https://stackoverflow.com/questions/17218357/python-3-3-struct-pack-wont-accept-strings
        packed_message = struct.pack(message_format, message_size, MESSAGE_ID, message_type, byte_command, b'\x00\x00')
        sock.sendall(packed_message)
    except socket.timeout:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()


def getResponse(sock):
    "Gets the message response to a sent command and unpackages it"
    response_string = None
    response_dummy = None
    response_id = -1
    response_type = -1
    try:
        recv_packet = sock.recv(4)
        tmp_response_size = struct.unpack('=l', recv_packet)
        response_size_val = int(tmp_response_size[0])
        response_size = response_size_val - 9
        message_format = ''.join(['=ll', str(response_size), 's1s'])
        remain_packet = struct.unpack(message_format, sock.recv(response_size_val))
        (response_id,response_type,response_string,response_dummy) = remain_packet
        if (response_string is None or response_string is str(b'\x00')) and response_id is not 2:
            response_string = "(Empty Response)"
        return (response_string, response_id, response_type)
    except socket.timeout:
        response_string = "(Connection Timeout)"
        return (response_string, response_id, response_type)


# begin main loop
interactive_mode = True
sock = ''
while interactive_mode:
    command_string = None
    response_string = None
    response_id = -1
    response_type = -1
    if len(sys.argv) > 1:
        command_string = " ".join(sys.argv[1:])
        interactive_mode = False
        print("RCON command sent: {}".format(command_string))
    else:
        command_string = input("RCON Command: ")
        if command_string in ('exit', 'Exit', 'E'):
            
            if sock:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            sys.exit("Exiting rcon client...\n")
        elif command_string in ('help','h','Help'):
            print('\tUse exit or Exit to quit interactive mode.')
            print('Many commands can be used via RCON, see https://ark.gamepedia.com/Console_Commands')
            print('Tested commands:')
            print('\tbroadcast\n\tserverchat\n\tgetchat')
            print('\tsaveworld\n\tsetmessageoftheday\n\tdestroywilddinos\n\tsettimeofday')
            print('\tlistplayers\n\tkillplayer\n\tserverchattoplayer')
            continue
        elif command_string in ('') or not command_string:
            continue

    try:
        sock = socket.create_connection((RCON_SERVER_HOSTNAME, RCON_SERVER_PORT))
    except ConnectionRefusedError:
        print("Unable to make RCON connection")
        sys.exit(3)
    sock.settimeout(RCON_SERVER_TIMEOUT)
        # send SERVERDATA_AUTH
    sendMessage(sock, RCON_PASSWORD, MESSAGE_TYPE_AUTH)
        # get empty SERVERDATA_RESPONSE_VALUE (auth response 1 of 2)
    response_string,response_id,response_type = getResponse(sock)
        # get SERVERDATA_AUTH_RESPONSE (auth response 2 of 2)
    response_string,response_id,response_type = getResponse(sock)
        # send SERVERDATA_EXECCOMMAND
    sendMessage(sock, command_string, MESSAGE_TYPE_COMMAND)
        # get SERVERDATA_RESPONSE_VALUE (command response)
    response_string,response_id,response_type = getResponse(sock)
    # trim off null characters and new line
    response_txt = response_string.decode(encoding=('UTF-8'))[:-3]
    if interactive_mode:
        print(response_txt)
    else:
        print(response_txt)
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

# end main loop
