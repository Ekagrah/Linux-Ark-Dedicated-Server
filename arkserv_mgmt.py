#!/usr/bin/env python3

## paramiko library is needed and scp module for paramiko, pip install paramiko and pip install scp

## Designed to run from a Windows machine to a linux hosted server, interacting with  the arkserv_mgmt_local.py script

## Additionally, I am using an ssh key, if password is preferred, leave LINUX_USER_KEY empty
## To connect with password and comment out connection via key and the user key variable

## See my documentation on how linux server is set up
## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110


##------Start user editable section------##

LOCAL_ARK_INSTALLDIR = 'F:\steam-games\steamapps\common\ARK'
SERV_ARK_INSTALLDIR = '/opt/game'
## Directory for python script on server
SERV_BIN = '/opt/bin'
SERVER_HOSTNAME = '10.0.0.1'

LINUX_USER = 'user'
## key needs to be an openssh compatible format, if key file exists use that otherwise use password
LINUX_USER_KEY = 'F:\putty\id_rsa'
LINUX_USER_PASSWORD = ''
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'password'

## Dictionary for desired mods
## 12 Mods = ~ 1Gb
MODNAMES = {
        923607638:"More Stack",
        719928795:"Platforms Plus",
        821530042:"Upgrade Station",
        736236773:"Backpack",
        889745138:"Awesome Teleporter",
        731604991:"Structures Plus",
        754885087:"More Tranq + Arrow",
        859198322:"Craftable Element",
        764755314:"CKF Arch",
        703724165:"Versatile Rafts",
        1256264907:"Tools Evolved",
        864857312:"Undies Evolved"
}
##------End user editable section------##

import argparse
import datetime
import email.utils
from email.mime.text import MIMEText
import logging
import os
import paramiko
import re
from scp import SCPClient
import smtplib
import socket
import struct
import sys
import tempfile
import time

CURR_DATE = time.strftime("%b%d_%H-%M")
devnull = open(os.devnull, 'w')


def get_args():
    """Function to get action, specified on command line, to take for server"""
    ## Assign description to help doc
    parser = argparse.ArgumentParser(description='Script manages various functions taken on remote linux ARK server. One action accepted at a time.', allow_abbrev=False)
    ## Add arguments. When argument present on command line then it is stored as True, else returns False
    parser.add_argument(
        '--start', help='Start remote server', action='store_true')
    parser.add_argument(
        '--shutdown', help='Stop remote server', action='store_true')
    parser.add_argument(
        '--restart', help='Restart remote server', action='store_true')
    parser.add_argument(
        '--monitor', help='Reports back if server is running and accessible', action='store_true')
    parser.add_argument(
        '--update', help='Checks for and applies update to dedicated server, restarts instance', action='store_true')
    parser.add_argument(
        '--updateonly', help='Only checks for and applies update to dedicated server', action='store_true')
    parser.add_argument(
        '--modupdate', help='Checks for updates to mod content using local Windows ark install', action='store_true')
    parser.add_argument(
        '--cleanup', help='Removes unnecessary mod content', action='store_true')
    parser.add_argument(
        '--rcon', help='Launches interactive rcon session', action='store_true')
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--emailstats', help='Sends an email with information on filesystems, cpu, etc.', action='store_true')
    parser.add_argument(
        '--checkplayers', help='Checks if players are connected to server', action='store_true')
    
    if not len(sys.argv) == 2:
        parser.print_help()
        sys.exit(1)
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    start = args.start
    shutdown = args.shutdown
    restart = args.restart
    monitor = args.monitor
    update = args.update
    updateonly = args.updateonly
    modsupdate = args.modupdate
    cleanup = args.cleanup
    rcon = args.rcon
    save = args.save
    emailstats = args.emailstats
    checkplayers = args.checkplayers
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save, emailstats, checkplayers


class ssh:
    """Create ssh connection"""
    client = None
    def __init__(self, server, port, user, password=None):
        "Create ssh connection"
        self.client = paramiko.client.SSHClient()
        #self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if os.path.exists(LINUX_USER_KEY):
            self.client.load_system_host_keys()
            keyfile = paramiko.RSAKey.from_private_key_file(LINUX_USER_KEY)
            self.client.connect(server, port, username=user, pkey=keyfile)
        elif password:
            self.client.connect(server, port, username=user, password=password)
        else:
            print("No valid authenication methods provided")
            sys.exit(2)
    
    def sendCommand(self, command, timeout=10, recv_size=2048):
        """Send command over ssh transport connection"""
        if self.client:
            self.transport = self.client.get_transport()
            self.channel = self.transport.open_session()
            ## verify transport open or exit gracefully
            if self.channel:
                self.channel.settimeout(timeout)
                self.channel.get_pty()
                self.channel.exec_command(command)
                self.channel.shutdown_write()
                stderr = []
                while not self.channel.exit_status_ready():
                    if self.channel.recv_ready():
                        sys.stdout.write(self.channel.recv(recv_size).decode("utf-8"))
                        
                    if self.channel.recv_stderr_ready():
                        stderr.append(self.channel.recv_stderr(recv_size).decode("utf-8"))
                exit_status = self.channel.recv_exit_status()
                
                while True:
                    try:
                        remainder_recvd = self.channel.recv(recv_size).decode("utf-8")
                        if not remainder_recvd and not self.channel.recv_ready():
                            break
                        else:
                            sys.stdout.write(remainder_recvd)
                    except socket.timeout:
                        break
                        
                while True:
                    try:
                        remainder_stderr = self.channel.recv_stderr(recv_size).decode("utf-8")
                        if not remainder_stderr and not self.channel.recv_stderr_ready():
                            break
                        else:
                            stderr.append(remainder_stderr)
                    except socket.timeout:
                        break
                        
            stderr = ''.join(stderr)
            if stderr:
                return (stderr, exit_status)
                ## need to write better error reporting into local script
                    
        else:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
    ## end def sendCommand
## end ssh class


def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available. Original code by Dunto, updated/modified by Ekagrah"""
        
    ## DO NOT EDIT THESE VARIABLES UNLESS YOU UNDERSTAND THE CONSEQUENCES
    MESSAGE_TYPE_AUTH = 3
    MESSAGE_TYPE_AUTH_RESP = 2
    MESSAGE_TYPE_COMMAND = 2
    MESSAGE_TYPE_RESP = 0
    MESSAGE_ID = 0
    ## server response timeout in seconds
    RCON_SERVER_TIMEOUT = 3
    
    def sendMessage(sock, command_string, message_type):
        """Packages up a command string into a message and sends it"""
        try:
            command_len = len(command_string)
            byte_command = command_string.encode(encoding='ascii')
            message_size = (4 + 4 + command_len + 2)
            message_format = ''.join(['=lll', str(command_len), 's2s'])
            packed_message = struct.pack(message_format, message_size, MESSAGE_ID, message_type, byte_command, b'\x00\x00')
            sock.sendall(packed_message)
        except socket.timeout:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
    
    
    def getResponse(sock):
        """Gets the message response to a sent command and unpackages it"""
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

    
    ## Begin main loop
    interactive_mode = True
    while interactive_mode:
        command_string = None
        response_string = None
        response_id = -1
        response_type = -1
        if args:
            command_string = str(args[0])
            print("RCON command sent: {}".format(command_string))
            interactive_mode = False
        else:
            command_string = input("RCON Command: ")
            if command_string in ('exit', 'Exit', 'E'):
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                sys.exit("Exiting rcon client...")

        try:
            sock = socket.create_connection((SERVER_HOSTNAME, RCON_SERVER_PORT))
        except ConnectionRefusedError:
            print("Unable to make RCON connection")
            break
        
        sock.settimeout(RCON_SERVER_TIMEOUT)
            ## send SERVERDATA_AUTH
        sendMessage(sock, RCON_PASSWORD, MESSAGE_TYPE_AUTH)
            ## get empty SERVERDATA_RESPONSE_VALUE (auth response 1 of 2)
        response_string,response_id,response_type = getResponse(sock)
            ## get SERVERDATA_AUTH_RESPONSE (auth response 2 of 2)
        response_string,response_id,response_type = getResponse(sock)
            ## send SERVERDATA_EXECCOMMAND
        sendMessage(sock, command_string, MESSAGE_TYPE_COMMAND)
            ## get SERVERDATA_RESPONSE_VALUE (command response)
        response_string,response_id,response_type = getResponse(sock)
        ## trim off null characters and new line
        response_txt = response_string.decode(encoding=('UTF-8'))[:-3]
        
        if interactive_mode:
            print(response_txt)
        else:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            return response_txt
    ## end main loop
## end def RCON_CLIENT


def LIST_PLAYERS():
    """Check if players are connected to server"""
    PLAYER_LIST = RCON_CLIENT('listplayers')
    print(PLAYER_LIST)
    

def UPSERVER():
    """Start server instance"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --start".format(SERV_BIN), timeout=300)
    

def DOWNSERVER():
    """Shutdown server instance"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --shutdown".format(SERV_BIN), timeout=180)


def RESTART_SERVER():
    """Restart server instance"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --restart".format(SERV_BIN), timeout=90)
    

def SERV_MONITOR():
    """Checks on status of server"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --monitor".format(SERV_BIN), timeout=30)
    

def UPDATE():
    """Perform update to server version"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --update".format(SERV_BIN), timeout=300)
            
            
def UPDATEONLY():
    """Perform update to server version"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --updateonly".format(SERV_BIN), timeout=300)


def FNC_DO_SAVE():
    """Archive map, player/tribe, and configuration files into a tar"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --save".format(SERV_BIN), timeout=90)
        

def MOD_MGMT():
    """Check for updates to local mod files and copy to server"""
    MODS_UPDATED = {}
    def progress(filename, size, sent):
        sys.stdout.write("{}\'s progress: {:.2f} \r".format(filename.decode("utf-8"), float(sent)/float(size)*100) )
    scp = SCPClient(sshconnect.client.get_transport(), progress = progress)
    
    for id, name in MODNAMES.items():
        ITEM_MTIME = os.path.getmtime(r'{}\ShooterGame\Content\Mods\{}.mod'.format(LOCAL_ARK_INSTALLDIR, id))
        time_diff = (time.time() - ITEM_MTIME)
        
        ## if the time difference (current time - file modification time) is less than 24 hours then act
        if time_diff < 86400:
            ## add to dictonary used to log updates
            MODS_UPDATED[id]=name
            ## copy items to server
            scp.put('{0}\ShooterGame\Content\Mods\{1}.mod'.format(LOCAL_ARK_INSTALLDIR, id), '{}/ShooterGame/Content/Mods/'. format(SERV_ARK_INSTALLDIR))
            sys.stdout.flush()
            sys.stdout.write("\n")
            scp.put('{0}\ShooterGame\Content\Mods\{1}'.format(LOCAL_ARK_INSTALLDIR, id), recursive=True, remote_path='{}/ShooterGame/Content/Mods/'.format(SERV_ARK_INSTALLDIR))
            sys.stdout.flush()
            sys.stdout.write("\n")
    if MODS_UPDATED:
        print(MODS_UPDATED)
    else:
        print("No updated mods found")
    scp.close()

   
def MOD_CLEANUP():
    """Clean up extra mod content that is not part of the active mods in GameUserSettings.ini"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --cleanup".format(SERV_BIN), timeout=90)
    

def EMAIL_STATS():
    """Send email with information on server"""
    sshconnect.sendCommand("{}/arkserv_mgmt_local.py --emailstats".format(SERV_BIN), timeout=90)
    

#============================#
## Run get_args
start, shutdown, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save, emailstats, checkplayers = get_args()

if rcon:
    RCON_CLIENT()
    sys.exit(0)

## Create ssh connection
sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)

if start:
    UPSERVER()
elif shutdown:
    DOWNSERVER()
elif restart:
    RESTART_SERVER()
elif monitor:
    SERV_MONITOR()
elif update:
    UPDATE()
elif updateonly:
    UPDATEONLY()
elif modsupdate:
    MOD_MGMT()
elif cleanup:
    MOD_CLEANUP()
elif save:
    FNC_DO_SAVE()
elif emailstats:
    EMAIL_STATS()
elif checkplayers:
    LIST_PLAYERS()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

## Close ssh connection, this is also done in functions
sshconnect.client.close()
