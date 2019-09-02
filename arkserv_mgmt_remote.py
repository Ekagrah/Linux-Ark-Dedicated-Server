#!/usr/bin/env python3

## paramiko library is needed and scp module for paramiko, pip install paramiko and pip install scp

## Designed to run from a Windows machine to a linux hosted server, paths in MOD_MGMT method would need to be changed to run successfully on Mac OS or Linux

## Additionally, I am using an ssh key. If password is preferred, leave LINUX_USER_KEY empty and provide password

## See my documentation on how linux server is set up
## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110


##------Start user editable section------##

#MAP = 'TheIsland'
#MAP = 'ScorchedEarth_P'
#MAP = 'Aberration_P'
#MAP = 'Extinction'
#MAP = 'TheCenter'
#MAP = 'Ragnarok'
MAP = 'Valguero_P'

## Use this when playing a community map
## Different var needed for some functions
#MAP = '-MapModId=504122600'
#MAP_NAME = 'Valhalla'
#MAP = 'skiesofnazca'

LOCAL_ARK_INSTALLDIR = 'D:\steam-games\steamapps\common\ARK'
SERV_ARK_INSTALLDIR = '/opt/game'
SERVER_HOSTNAME = '192.168.0.0'
## Maximum number of players
NPLAYERS = '15'
SERV_PORT = '7777'
QUERY_PORT = '27015'
SERV_SAVE_DIR = '${HOME}/Documents/arksavedata'

LINUX_USER = 'user'
## key needs to be an openssh compatible format, if key file exists use that otherwise use password
LINUX_USER_KEY = 'C:\keys\id_rsa'
LINUX_USER_PASSWORD = ''
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'secret'

## Dictionary for desired mods
MODNAMES = {
        1380777369:"Additional Lighting",
        893735676:"Ark Eternal",
        1420423699:"ARKaeology Dinos",
        889745138:"Awesome Teleporter",
        736236773:"Backpack",
        1364327869:"Better Reusables",
        764755314:"CKF Arch",
        1267677473:"Cross Aberration",
        1230977449:"Exiles of the ARK",
        849985437:"HG Stacking Mod 5000-90",
        754885087:"More Tranq + Narcotic",
        719928795:"Platforms Plus",
        916807417:"Tek Helper",
        821530042:"Upgrade Station",
        703724165:"Versatile Rafts",
        1623256655:"Resource+",
        1730382678:"Stark Industries",
        665094472:"Deadly Weapons",
        1529972975:"smuMeraBabyu",
        1640117392:"Ark Settlements",
        1430633911:"Upgradeable Tek Weapons"
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


RCON_ACTIVE = 'True'
SERV_PORT_B = int(SERV_PORT) + 1
CURR_DATE = time.strftime("%b%d_%H-%M")
devnull = open(os.devnull, 'w')


def VARIABLE_CHK():
    """Verify needed variables have proper value"""
    
    class TermColor:
        RED = '\033[93;41m'
        MAGENTA = '\033[35m'
        DEFAULT = '\033[00m'
    
    varchk = [MAP, SERV_ARK_INSTALLDIR, SERVER_HOSTNAME, NPLAYERS, SERV_PORT, QUERY_PORT, RCON_ACTIVE, RCON_SERVER_PORT, RCON_PASSWORD, SERV_SAVE_DIR, LINUX_USER]
    
    varlist = ["MAP", "SERV_ARK_INSTALLDIR", "SERVER_HOSTNAME", "NPLAYERS", "SERV_PORT", "QUERY_PORT", "RCON_ACTIVE", "RCON_SERVER_PORT", "RCON_PASSWORD", "SERV_SAVE_DIR", "LINUX_USER"]
    
    err_on_var = []
    invalid_var = []
    for id, x in enumerate(varchk):
        if not x:
            err_on_var.append(varlist[id])
            break
        elif id == 3:
            ## interval comparison
            if not 1 <= int(x) <= 70:
                invalid_var.append(varlist[id])
        elif id in  ("4", "5", "7"):
            ## if these variables are not integers then flag, converting to float for good measure
            if not float(x).is_integer():
                invalid_var.append(varlist[id])
    
    if err_on_var:
        print(TermColor.MAGENTA)
        print('Missing value for:')
        print(*err_on_var, sep='\n')
        print(TermColor.DEFAULT)
        
    if invalid_var:
        print(TermColor.RED)
        print('Invalid value for:')
        print(*invalid_var, sep='\n')    
        print(TermColor.DEFAULT)
        
    if any((err_on_var, invalid_var)):
        sys.exit(1)
        
VARIABLE_CHK()


class RconAction(argparse.Action):
    '''Custom argparse action to open rcon interactively or to run specified command; used when --rcon provided on command line'''
    
    def __init__(self, option_strings, dest, nargs='*', const=True, default=None, type=None, choices=None, required=False, help=None, metavar=None):
        super(RconAction, self).__init__(option_strings=option_strings, dest=dest, nargs=nargs, const=const, default=default, type=type, choices=choices, required=required, help=help, metavar=metavar)
            
    def __call__(self, parser, namespace, values, option_string=None):
        if values:
            setattr(namespace, self.dest, values)
        else:
            setattr(namespace, self.dest, self.const)


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
        '--rcon', help='Launches interactive rcon session', action=RconAction)
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--emailstats', help='Sends an email with information on filesystems, cpu, etc.', action='store_true')
    
    if not len(sys.argv) >= 2:
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
    modupdate = args.modupdate
    cleanup = args.cleanup
    rcon = args.rcon
    save = args.save
    emailstats = args.emailstats
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, modupdate, cleanup, rcon, save, emailstats


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
    
    def sendCommand(self, command, stdoutwrite=False, parse=False, target=None, timeout=10, recv_size=2048):
        """Method to send command over ssh transport channel"""
        
        parse_return = None
        self.transport = self.client.get_transport()
        self.channel = self.transport.open_channel(kind='session')
        self.channel.settimeout(timeout)
        ## verify channel open or exit gracefully
        try:
            self.channel.exec_command(command)
            self.channel.shutdown(1)
            fd, fp = tempfile.mkstemp()
            f = open(fp, 'a+')
            stdout, stderr = [], []
            while not self.channel.exit_status_ready():
                if self.channel.recv_ready():
                    recvd = self.channel.recv(recv_size).decode("utf-8")
                    stdout.append(recvd)
                    if stdoutwrite:
                        sys.stdout.write(''.join(recvd))
                    if parse:
                        f.write(recvd)
                
                if self.channel.recv_stderr_ready():
                    stderr.append(self.channel.recv_stderr(recv_size).decode("utf-8"))
            
            while True:
                try:
                    remainder_recvd = self.channel.recv(recv_size).decode("utf-8")
                    if not remainder_recvd and not self.channel.recv_ready():
                        break
                    else:
                        stdout.append(remainder_recvd)
                        
                        if stdoutwrite:
                            sys.stdout.write(''.join(stdout))
                        if parse:
                            f.write(remainder_recvd)
                except socket.timeout:
                    break
                    
            while True:
                try:
                    remainder_stderr = self.channel.recv_stderr(recv_size).decode("utf-8")
                    if not remainder_stderr and not self.channel.recv_stderr_ready():
                        break
                    else:
                        stderr.append(remainder_stderr)
                        
                        if stdoutwrite:
                            sys.stdout.write(''.join("Error ", stderr))
                            
                except socket.timeout:
                    break
            
            exit_status = self.channel.recv_exit_status()
            
            if parse:
                with open(fp) as f:
                    f.seek(0)
                    pattern = re.compile(target)
                    for line in f:
                        if pattern.match(line):
                            parse_return = True
                            break
                        else:
                            parse_return = False
        except:
            ## SSHException
            err, err_value, err_trace = sys.exc_info()
            sys.exit("Error {}: {}".format(err_value, err))
            
        if parse:
            return parse_return
        else:
            return stdout, stderr, exit_status
    ## end def sendCommand
## end ssh class


def UPCHK():
    '''Check if there is a "ShooterGameServ" process '''
    
    do_check = sshconnect.sendCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", parse=True, target="[0-9]*")
    return do_check


def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available. Original code by Dunto, updated/modified by Ekagrah"""
    
    if not UPCHK():
        sys.exit("Server not running, no RCON available")
        
    ##Ark Help from http://www.ark-survival.net/en/2015/07/09/rcon-tutorial/
    ## and https://cjsavage.com/guides/linux/ark-dedicated-save-on-exit.html

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
    sock = None
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
            if command_string in ('exit', 'Exit'):
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                sys.exit("Exiting rcon client...")
            elif command_string in ('help','h','Help'):
                print('\tUse exit or Exit to quit interactive mode.')
                print('Many commands can be used via RCON, see https://ark.gamepedia.com/Console_Commands')
                print('Tested commands:')
                print('\tbroadcast\n\tserverchat\n\tgetchat')
                print('\tsaveworld\n\tsetmessageoftheday\n\tdestroywilddinos\n\tsettimeofday')
                print('\tlistplayers\n\tkillplayer\n\tserverchattoplayer\n\tGetSteamIDForPlayerID\n\tKickPlayer')
                continue
            elif command_string in ('') or not command_string:
                continue

        try:
            sock = socket.create_connection((SERVER_HOSTNAME, RCON_SERVER_PORT))
        except ConnectionRefusedError:
            print("Unable to make RCON connection")
            break
        
        sock.settimeout(RCON_SERVER_TIMEOUT)
        
        sendMessage(sock, RCON_PASSWORD, MESSAGE_TYPE_AUTH)
        response_string,response_id,response_type = getResponse(sock)
        response_string,response_id,response_type = getResponse(sock)

        sendMessage(sock, command_string, MESSAGE_TYPE_COMMAND)
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


def CHECK_PLAYERS():
    """Check if players are connected to server"""
    
    pattern = re.compile(".*[Nn]o.[Pp]layers.[Cc]onnected.*")

    PLAYER_LIST = RCON_CLIENT('listplayers')
    if pattern.search(PLAYER_LIST):
        return False
    else:
        return PLAYER_LIST
        

def PLAYER_MONITOR():
    """Monitor which players are connected, if any"""
    
    chktimeout=9
    while chktimeout > 0:
        _ret = CHECK_PLAYERS()
        if not _ret:
            return True
        else:
            print(_ret)
            time.sleep(20)
            chktimeout -= 1
    else:
        print('Timeout waiting for users to log off')
        sys.exit(7)


def UPSERVER():
    
    if UPCHK():
        print("Server seems to be running already")
    else:
        print("Starting server")
        sshconnect.sendCommand('{}/ShooterGame/Binaries/Linux/ShooterGameServer "{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?RCONServerGameLogBuffer=400?ForceFlyerExplosives=True?PreventMateBoost -servergamelog -NoBattlEye -USEALLAVAILABLECORES" &'.format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT))
        ## -usecache -server -automanagedmods  ?PreventDownloadSurvivor=True ?PreventDownloadDinos=True ?PreventDownloadItems=True ?ServerAdminPassword= ?AllowRaidDinoFeeding=True -ForceRespawnDinos
    

def DOWNSERVER():
    """Shutdown server instance"""
    
    downcounter = 4
    
    if UPCHK():
        SERV_PID = sshconnect.sendCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null")
        print("Shutting down server...")
        sshconnect.sendCommand("kill -2 {}".format(SERV_PID))
        time.sleep(10)
    else:
        print("Unable to find running server")
    while True:
        if UPCHK():
            if downcounter == 0:
                print('Forcfully killing server instance')
                sshconnect.sendCommand("for i in $(/usr/bin/pgrep -u {} ShooterGameServ -d ' ' 2>/dev/null); do kill -9 $i; done".format(LINUX_USER), stdoutwrite=True)
                time.sleep(5)
                break
            else:
                print("Waiting for server to go down gracefully")
                time.sleep(5)
                downcounter -= 1
        else:
            print("Unable to find running server")
            break


def RESTART_SERVER():
    """Check if no players connected, shutdown then start server"""
    
    #try:
        #MAP = MAP_NAME
    #except:
        #pass
    
    if not CHECK_PLAYERS():
        pass
    else:
        RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
        PLAYER_MONITOR()
    
    RECENT_SAVE = sshconnect.sendCommand('if [[ $(( $(/bin/date +%s) - $(/usr/bin/stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), parse=True, target="save-found")
    if not RECENT_SAVE:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.sendCommand('if [[ $(( $(/bin/date +%s) - $(/usr/bin/stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), parse=True, target="save-found")
        if SAVE_CHK:
            print("Recent save found")
            DOWNSERVER()
            time.sleep(10)
            UPSERVER()
        else:
            print("Unable to verify save, not restarting server")
    else:
        print("Recent save found")
        DOWNSERVER()
        time.sleep(10)
        UPSERVER()
    

def SERV_MONITOR():
    """Checks on status of server"""
    ## increase as needed, especially for community maps
    upcounter = 7
    SERV_STATUS_CHK = sshconnect.sendCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", parse=True, target="[0-9]*")
    if SERV_STATUS_CHK:
        print("Server is running")
        while True:
            PORT_CHK = sshconnect.sendCommand("/bin/netstat -puln 2>/dev/null | /bin/grep -E '.*:{}.*'".format(SERV_PORT_B), parse=True, target=".*:{}.*".format(SERV_PORT_B))
            if PORT_CHK:
                print("Server is up and should be accessible")
                break
            else:
                if upcounter > 0:
                    print("Waiting on server...")
                    time.sleep(20)
                    upcounter -= 1
                else:
                    print("Server not up yet, manually monitor status...")
                    break
    else:
        print("Server does not seem to be running")
   
    
def CHECK_SERV_UPDATE():
    """Check if update to server has been posted"""
    ## fix for conflicting file that can prevent getting the most recent version
    sshconnect.sendCommand("if [[ -e ${HOME}/.steam/steam/appcache/appinfo.vdf ]]; then rm ${HOME}/.steam/steam/appcache/appinfo.vdf ; fi")
    ## See if update is available
    UPDATE_CHK = sshconnect.sendCommand('new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | /bin/grep -A5 "branches" | /usr/bin/awk -F \'\"\' \'/buildid/{{print $4}}\' )" ; curr_vers="$( /usr/bin/awk -F \'\"\' \'/buildid/{{print $4}}\' {0}/steamapps/appmanifest_376030.acf )\" ; if [[ ${{new_vers}} -gt ${{curr_vers}} ]]; then echo "update-needed" ; else echo "up-to-date" ; fi'.format(SERV_ARK_INSTALLDIR), parse=True, target="up-to-date")
    if UPDATE_CHK:
        print("Server reports up-to-date")
        return False
    else: 
        return True
        

def UPDATE():
    """Perform update to server version"""
    if CHECK_SERV_UPDATE():
        updatetimeout = 3
        while updatetimeout > 0:
            ## this is slow and times out occasionally
            sshconnect.sendCommand("/usr/games/steamcmd +login anonymous +force_install_dir {} +app_update 376030 public validate +quit | /usr/bin/tee /tmp/arkudtmp".format(SERV_ARK_INSTALLDIR), stdoutwrite=True, timeout=90)
            UPD_STATE = sshconnect.sendCommand("/usr/bin/tail -5 /tmp/arkudtmp | /usr/bin/awk -F \" \" '/.*App.*376030.*/{{print $1}}' ", parse=True, target="Success.*")
            ## so we must verify it completed
        
            if UPD_STATE:
                #print("Ark server is up-to-date")
                sshconnect.sendCommand("/bin/rm -f /tmp/arkudtmp")
                return True
            elif updatetimeout == 0:
                print("Issue completing update.\nCheck permissions and disk space for starters.")
                ## Not removing temp file, may help with troubleshooting
                return False
            elif not UPD_STATE:
                print("Issue completing update. Trying again...")
                updatetimeout -= 1
            else:
                print("restarting update")
                updatetimeout -= 1
    else:
        return False


def FNC_DO_SAVE():
    """Archive map, player/tribe, and configuration files into a tar"""
    
    RECENT_SAVE = sshconnect.sendCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), parse=True, target="save-found")
    if RECENT_SAVE:
        sshconnect.sendCommand("curr_date=\"$( /bin/date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then /bin/mkdir -p \"${{tar_dir}}\" ; fi ; /bin/echo \"Copying files to {2}/${{tar_dir}}...\" ; /bin/cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; /bin/echo \"Making tarball...\" ; /bin/tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && (/bin/echo \"Successfully made save bundle\") || (/bin/echo \"Unable to make tarball...\") ; /bin/rm -rf ./${{tar_dir}}".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR), stdoutwrite=True)
        
    else:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.sendCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), parse=True, target="save-found")
        if SAVE_CHK:
            sshconnect.sendCommand("curr_date=\"$( /bin/date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then /bin/mkdir -p \"${{tar_dir}}\" ; fi ; /bin/echo \"Copying files to {2}/${{tar_dir}}...\" ; /bin/cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; /bin/cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; /bin/echo \"Making tarball...\" ; /bin/tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && (/bin/echo \"Successfully made save bundle\") || (/bin/echo \"Unable to make tarball...\") ; /bin/rm -rf ./${{tar_dir}}".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR), stdoutwrite=True)
        else:
            print("Unable to verify world was recently saved, not performing save.")
## end def FNC_DO_SAVE
        

def MOD_MGMT():
    """Check for updates to local mod files and copy to server"""
    
    MODS_UPDATED = {}
    
    def progress(filename, size, sent):
        sys.stdout.write("{}\'s progress: {:.2f} \r".format(filename.decode("utf-8"), float(sent)/float(size)*100) )
    
    scp = SCPClient(sshconnect.client.get_transport(), progress = progress)
    
    def transfer(mod_id):
        ## copy items to server
        scp.put('{0}\ShooterGame\Content\Mods\{1}.mod'.format(LOCAL_ARK_INSTALLDIR, mod_id), '{}/ShooterGame/Content/Mods/'. format(SERV_ARK_INSTALLDIR))
        sys.stdout.flush()
        sys.stdout.write("\n")
        scp.put('{0}\ShooterGame\Content\Mods\{1}'.format(LOCAL_ARK_INSTALLDIR, mod_id), recursive=True, remote_path='{}/ShooterGame/Content/Mods/'.format(SERV_ARK_INSTALLDIR))
        sys.stdout.flush()
        sys.stdout.write("\n")
        
    
    for id, name in MODNAMES.items():
        ITEM_MTIME = os.path.getmtime(r'{}\ShooterGame\Content\Mods\{}.mod'.format(LOCAL_ARK_INSTALLDIR, id))
        time_diff = (time.time() - ITEM_MTIME)
        
        ## if the time difference (current time - file modification time) is less than 24 hours then act
        if time_diff < 86400:
            ## add to dictonary used to log updates
            MODS_UPDATED[id] = name
    
    if MODS_UPDATED:
        print(MODS_UPDATED)
        
        if not UPCHK():
            for id, name in MODS_UPDATED.items():
                transfer(id)
            print('Server not started automatically')
        elif UPCHK() and not CHECK_PLAYERS():
            DOWNSERVER()
            for id, name in MODS_UPDATED.items():
                transfer(id)
            UPSERVER()
        elif CHECK_PLAYERS():
            RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
            print('Players are connected, wait or kick to continue.')
        else:
            print("Server restart will be required, verify no one is connected and that server is shutdown.")
    else:
        print('No updates found')
    
    scp.close()

   
def MOD_CLEANUP():
    """Clean up extra mod content that is not part of the active mods in GameUserSettings.ini"""
    DIR_CHK = sshconnect.sendCommand("if [[ -d {}/ShooterGame/Content/Mods ]]; then echo 'exists' ; fi".format(SERV_ARK_INSTALLDIR), parse=True, target="exists")
    if DIR_CHK:
        ## if existing file has match under ActiveMods then remove it from array
        sshconnect.sendCommand("/bin/sed -n 's/ActiveMods=//p' {0}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini | /usr/bin/awk -v FS=\",\" '{{OFS=\" \"; $1=$1; print $0}}' ; declare -a mod_list ; while IFS=  read -r -d $'\0'; do mod_list+=(\"$REPLY\") ; done < <(/usr/bin/find ./ -name '*.mod' -print0 | /bin/sed -e 's|./111111111.mod||' -e 's|./||g' -e 's|.mod||g') ; arr_id=0 ; for m in $(/bin/echo ${{mod_list[@]}} ) ; do if [[ $(/bin/echo ${{active_mods}} | /bin/grep -o ${{m}}) == \"${{m}}\" ]]; then unset mod_list[${{arr_id}}] ; else /bin/echo \"Marking ${{m}} for removal\" fi ; let arr_id++ ; done ; unset arr_id ; if [[ ${{#mod_list[@]}} -gt 0 ]] ; then cd {0}/ShooterGame/Content/Mods ; for d in $(/bin/echo ${{mod_list[@]}}) ; do ; /bin/echo \"Deleting data for mod: ${{d}}\" ; rm -rf ./${{d}}* ; done ; else /bin/echo \"No files to remove/modify\" ; fi ; cd /opt ; unset active_mods ; unset mod_list ".format(SERV_ARK_INSTALLDIR))
        sys.exit()
    else:
        print('SERV_ARK_INSTALLDIR seems invalid to access mod data')
        sys.exit(12)
        
        
def EMAIL(content, subject):
    import smtplib
    import email.utils
    from email.mime.text import MIMEText
    
    if not SERV_STATUS_CHK():
        sys.exit("Server not running, not sending email")
    
    msg = MIMEText(content)
    msg['To'] = email.utils.formataddr(('Server Manager', EMAIL_ADDR))
    msg['From'] = email.utils.formataddr(('Ark Server', EMAIL_ADDR))
    msg['Subject'] = subject
    
    ## To send via SSL use SMTP_SSL()
    server = smtplib.SMTP()
    ## Specifying an empty server.connect() statment defaults to ('localhost', '25')
    server.connect()
    ## Send debug to terminal
    #server.set_debuglevel(True)
    
    try:
        server.sendmail(EMAIL_ADDR, [EMAIL_ADDR], msg.as_string())
    finally:
        server.quit()


def EMAIL_STATS():
    fd, fp = tempfile.mkstemp()
    f = open(fp, 'a+')
    
    EMAIL_DATE = time.strftime("%F-%R")
    RUNNING_MAP = sshconnect.sendCommand("""/bin/ps -efH --sort=+ppid | /usr/bin/awk '/[S]hooterGameServer/{{$0=$9; nextfile}} END {{FS="?"; ORS=""; NF=11; $0=$0; print $1}}'""", stdoutwrite=True)
    RUNNING_VERSION = sshconnect.sendCommand("/usr/bin/find {}/ShooterGame/Saved/Logs/ -maxdepth 1 -mtime -2 -iname \"ShooterGame*.log\" -exec awk -F \": \" '/Version/{{print $2}}' {{}} \; | tail -1".format(SERV_ARK_INSTALLDIR), stdoutwrite=True)
    f.write("\nRunning map and version: {} {}".format(RUNNING_MAP, RUNNING_VERSION))
    f.write(RCON_CLIENT("listplayers"))
    f.write("\n------\n")
    f.write("CPU Info:\n")
    f.write(sshconnect.sendCommand("/bin/cat /proc/cpuinfo | /usr/bin/head -15 | /usr/bin/awk '/model name/{{print}} ; /cpu cores/{{print}}'", stdoutwrite=True))
    f.write("\n------\n")
    f.write(sshconnect.sendCommand("/usr/bin/top -b -n 1 | awk 'BEGIN {{}}; FNR <= 7; /ShooterG/{print}'", stdoutwrite=True))
    f.write("\n------\n")
    f.write(sshconnect.sendCommand("/usr/bin/iostat -N -m", stdoutwrite=True))
    f.write("\n------\n")
    f.write(sshconnect.sendCommand("/bin/df -h --exclude-type=tmpfs --total", stdoutwrite=True))
    f.write("\n------\n")
    f.write(sshconnect.sendCommand("/usr/bin/du -h /opt --max-depth=1", stdoutwrite=True))
    f.seek(0)
    
    EMAIL(f.read(), "Ark Server report as of {}".format(EMAIL_DATE))
    
    os.close(fd)


#============================#
## Run get_args
start, shutdown, restart, monitor, update, updateonly, modupdate, cleanup, rcon, save, emailstats = get_args()

## Create ssh connection
sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)

if rcon:
    if isinstance(rcon, bool):
        RCON_CLIENT()
    else:
        rcon_return = RCON_CLIENT(' '.join(rcon))
        print(rcon_return)
elif start:
    UPSERVER()
    SERV_MONITOR()
elif shutdown:
    PLAYER_MONITOR()
    DOWNSERVER()
    SERV_MONITOR()
elif restart:
    RESTART_SERVER()
    SERV_MONITOR()
elif monitor:
    SERV_MONITOR()
elif update:
    if UPDATE():
        RESTART_SERVER()
        SERV_MONITOR()
elif updateonly:
    UPDATE()
elif modupdate:
    MOD_MGMT()
    SERV_MONITOR()
elif cleanup:
    MOD_CLEANUP()
elif save:
    FNC_DO_SAVE()
elif emailstats:
    EMAIL_STATS()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

## Close ssh connection, this is also done in functions
sshconnect.client.close()
