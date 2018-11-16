#!/usr/bin/env python3

## paramiko library is needed and scp module for paramiko, pip install paramiko and pip install scp

## Designed to run from a Windows machine to a linux hosted server, paths
## in MOD_MGMT method would need to be changed to run successfully on Mac OS or Linux

## Additionally, I am using an ssh key, if password is preferred, leave LINUX_USER_KEY empty
## To connect with password and comment out connection via key and the user key variable

## See my documentation on how linux server is set up


##------Start user editable section------##

#MAP = 'TheIsland'
#MAP = 'ScorchedEarth_P'
#MAP = 'Aberration_P'
MAP = 'Extinction'
#MAP = 'TheCenter'
#MAP = 'Ragnarok'
#MAP = 'skiesofnazca'

LOCAL_ARK_INSTALLDIR = 'F:\steam-games\steamapps\common\ARK'
SERV_ARK_INSTALLDIR = '/opt/game'
SERVER_HOSTNAME = '10.0.0.1'
## Maximum number of players
NPLAYERS = '15'
SERV_PORT = '7777'
QUERY_PORT = '27015'
RCON_ACTIVE = 'True'
SERV_SAVE_DIR = '${HOME}/Documents/arksavedata'

LINUX_USER = 'servmana'
## key needs to be an openssh compatible format
LINUX_USER_KEY = 'F:\putty\id_rsa'
LINUX_USER_PASSWORD = 'password'
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'password'

## Dictionary for desired mods
MODNAMES = {
        923607638:"More Stack",
        719928795:"Platforms Plus",
        821530042:"Upgrade Station",
        736236773:"Backpack",
        889745138:"Awesome Teleporter",
        731604991:"Structures Plus",
        506506101:"Better Beacons",
        754885087:"More Tranq + Arrow",
        859198322:"Craftable Element",
        764755314:"CKF Arch",
        703724165:"Versatile Rafts",
        1439559887:"Ammo Switcher",
        1380777369:"Additional Lighting",
        1256264907:"Tools Evolved",
        873924848:"Flying Rafts",
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
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save, emailstats


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
    
    def sendCommand(self, command, stdoutwrite=False, timeout=10, recv_size=2048):
        """Send command over ssh transport connection"""
        if self.client:
            self.transport = self.client.get_transport()
            self.channel = self.transport.open_session()
            ## verify transport open or exit gracefully
            if self.channel:
                self.channel.settimeout(timeout)
                self.channel.exec_command(command)
                self.channel.shutdown_write()
                stdout, stderr = [], []
                while not self.channel.exit_status_ready():
                    if self.channel.recv_ready():
                        stdout.append(self.channel.recv(recv_size).decode("utf-8"))
                        if stdoutwrite:
                            sys.stdout.write(' '.join(stdout))    
                    
                    if self.channel.recv_stderr_ready():
                        stderr.append(self.channel.recv_stderr(recv_size).decode("utf-8"))
                exit_status = self.channel.recv_exit_status()
                
                while True:
                    try:
                        remainder_recvd = self.channel.recv(recv_size).decode("utf-8")
                        if not remainder_recvd and not self.channel.recv_ready():
                            break
                        else:
                            stdout.append(remainder_recvd)
                            if stdoutwrite:
                                sys.stdout.write(' '.join(stdout))
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
                        
                stdout = ''.join(stdout)
                stderr = ''.join(stderr)
                
                #return (stdout, stderr, exit_status)
                return stdout
                        
        else:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
    ## end def sendCommand
    
    def parseCommand(self, command, target, stdoutwrite=False, timeout=0, recv_size=2048):
        """Send command over ssh transport connection, regex pattern matching to see if return is desireable"""
        if self.client:
            self.transport = self.client.get_transport()
            self.channel = self.transport.open_session()
            if self.channel:
                self.channel.settimeout(timeout)
                self.channel.exec_command(command)
                self.channel.shutdown_write()
                fd, fp = tempfile.mkstemp()
                f = open(fp, 'a+')
                stdout, stderr = [], []
                while not self.channel.exit_status_ready():
                    if self.channel.recv_ready():
                        recvd = self.channel.recv(recv_size).decode("utf-8")
                        f.write(recvd)
                        if stdoutwrite:
                            sys.stdout.write(recvd)
                    
                    if self.channel.recv_stderr_ready():
                        stderr.append(self.channel.recv_stderr(recv_size).decode("utf-8"))
                exit_status = self.channel.recv_exit_status()
                
                while True:
                    try:
                        remainder_recvd = self.channel.recv(recv_size).decode("utf-8")
                        if not remainder_recvd and not self.channel.recv_ready():
                            break
                        else:
                            f.write(remainder_recvd)
                            if stdoutwrite:
                                sys.stdout.write(remainder_recvd)
                    except socket.timeout:
                        continue
                        
                while True:
                    try:
                        remainder_stderr = self.channel.recv_stderr(recv_size).decode("utf-8")
                        if not remainder_stderr and not self.channel.recv_stderr_ready():
                            break
                        else:
                            stderr.append(remainder_stderr)
                    except socket.timeout:
                        continue
                        
                with open(fp) as f:
                    f.seek(0)
                    pattern = re.compile(target)
                    for line in f:
                        if pattern.match(line):
                            return True
                            break
                        else:
                            return False
                        
        else:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
    ## end def parseCommand
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


def CHECK_PLAYERS():
    """Check if players are connected to server"""
    chktimeout=9
    while True:
        if chktimeout > 0:
            PLAYER_LIST = RCON_CLIENT('listplayers')
            pattern = re.compile(".*[Nn]o.[Pp]layers.[Cc]onnected.*")
            if pattern.search(PLAYER_LIST):
                return False
            else:
                print(PLAYER_LIST)
                time.sleep(20)
                chktimeout -= 1
        else:
            print('Timeout waiting for users to log off')
            ## Notify
            break


def UPSERVER():
    TMUX_CHK = sshconnect.parseCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
    if TMUX_CHK:
        print("Server seems to be running already")
    else:
        print("Starting server")
        sshconnect.sendCommand('{}/ShooterGame/Binaries/Linux/ShooterGameServer "{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?RCONServerGameLogBuffer=400?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -servergamelog -NoBattlEye -USEALLAVAILABLECORES" &'.format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT))
        ## -usecache -server -automanagedmods ?PreventMateBoost ?PreventDownloadSurvivor=True?PreventDownloadDinos=True?PreventDownloadItems=True -ForceRespawnDinos
    

def DOWNSERVER():
    """Shutdown server instance"""
    
    downcounter = 7
    UPCHK = sshconnect.parseCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
    SERV_PID = sshconnect.sendCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null")
    if UPCHK:
        print("Shutting down server...")
        sshconnect.sendCommand("kill -2 {}".format(SERV_PID))
        time.sleep(10)
    else:
        print("Unable to find running server")
    while True:
        ALT_CHK = sshconnect.parseCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
        if ALT_CHK:
            if downcounter == 0:
                print('Forcfully killing server instance')
                sshconnect.sendCommand("for i in $(/usr/bin/pgrep -c ShooterGameServ 2>/dev/null); do kill -9 $i; done")
                break
            else:
                print("Waiting for server to go down gracefully")
                time.sleep(10)
                downcounter -= 1
        else:
            print("Unable to find running server")
            break


def RESTART_SERVER():
    """Check if players connected then shutdown and start server"""
    
    RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
    
    CHECK_PLAYERS()
    
    RECENT_SAVE = sshconnect.parseCommand('if [[ $(( $(/bin/date +%s) - $(/usr/bin/stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
    if not RECENT_SAVE:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.parseCommand('if [[ $(( $(/bin/date +%s) - $(/usr/bin/stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
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
    SERV_STATUS_CHK = sshconnect.parseCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
    if SERV_STATUS_CHK:
        print("Server is running")
        while True:
            PORT_CHK = sshconnect.parseCommand("/bin/netstat -puln 2>/dev/null | /bin/grep -E '.*:{}.*'".format(SERV_PORT_B), ".*:{}.*".format(SERV_PORT_B))
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
    UPDATE_CHK = sshconnect.parseCommand('new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | /bin/grep -A5 "branches" | awk -F \'\"\' \'/buildid/{{print $4}}\' )" ; curr_vers="$( awk -F \'\"\' \'/buildid/{{print $4}}\' {0}/steamapps/appmanifest_376030.acf )\" ; if [[ ${{new_vers}} -gt ${{curr_vers}} ]]; then echo "update-needed" ; else echo "up-to-date" ; fi'.format(SERV_ARK_INSTALLDIR), "up-to-date")
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
            UPD_STATE = sshconnect.parseCommand("/usr/games/steamcmd +login anonymous +force_install_dir {} +app_update 376030 public validate +quit".format(SERV_ARK_INSTALLDIR), ".*Success.*App.*376030.*", stdoutwrite=True, timeout=90)
            ## so we must verify it completed
        
            if UPD_STATE:
                print("Ark server is up-to-date")
                return True
            elif not UPD_STATE:
                print("Issue completing update. Trying again...")
                updatetimeout -= 1
                #break
            elif updatetimeout == 0:
                print("Issue completing update.\nCheck permissions and disk space for starters.")
            else:
                print("restarting update")
                updatetimeout -= 1


def FNC_DO_SAVE():
    """Archive map, player/tribe, and configuration files into a tar"""
    RECENT_SAVE = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
    if RECENT_SAVE:
        ## is a find command better?
        sshconnect.sendCommand("curr_date=\"$( /bin/date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then /bin/mkdir -p \"${{tar_dir}}\" ; fi ; echo \"Copying files to {2}/${{tar_dir}}...\" ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; echo \"Making tarball...\" ; /bin/tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && (echo \"Successfully made save bundle\") || (echo \"Unable to make tarball...\") ; rm -rf ./${{tar_dir}}".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR), stdoutwrite=True)
        
    else:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
        if SAVE_CHK:
            sshconnect.sendCommand("curr_date=\"$( /bin/date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then /bin/mkdir -p \"${{tar_dir}}\" ; fi ; echo \"Copying files to {2}/${{tar_dir}}...\" ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; echo \"Making tarball...\" ; /bin/tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && (echo \"Successfully made save bundle\") || (echo \"Unable to make tarball...\") ; rm -rf ./${{tar_dir}}".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR), stdoutwrite=True)
        else:
            print("Unable to verify world was recently saved, not performing save.")
## end def FNC_DO_SAVE
        

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
    scp.close()

   
def MOD_CLEANUP():
    """Clean up extra mod content that is not part of the active mods in GameUserSettings.ini"""
    DIR_CHK = sshconnect.parseCommand("if [[ -d {}/ShooterGame/Content/Mods ]]; then echo 'exists' ; fi".format(SERV_ARK_INSTALLDIR), "exists")
    if DIR_CHK:
        ## if existing file has match under ActiveMods then remove it from array
        sshconnect.sendCommand("\sed -n 's/ActiveMods=//p' {0}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini | \awk -v FS=\",\" '{{OFS=\" \"; $1=$1; print $0}}' ; declare -a mod_list ; while IFS=  read -r -d $'\0'; do mod_list+=(\"$REPLY\") ; done < <(\find ./ -name '*.mod' -print0 | \sed -e 's|./111111111.mod||' -e 's|./||g' -e 's|.mod||g') ; arr_id=0 ; for m in $(\echo ${{mod_list[@]}} ) ; do if [[ $(\echo ${{active_mods}} | \grep -o ${{m}}) == \"${{m}}\" ]]; then unset mod_list[${{arr_id}}] ; else echo \"Marking ${{m}} for removal\" fi ; let arr_id++ ; done ; unset arr_id ; if [[ ${{#mod_list[@]}} -gt 0 ]] ; then cd {0}/ShooterGame/Content/Mods ; for d in $(\echo ${{mod_list[@]}}) ; do ; echo \"Deleting data for mod: ${{d}}\" ; rm -rf ./${{d}}* ; done ; else echo \"No files to remove/modify\" ; fi ; cd /opt ; unset active_mods ; unset mod_list ".format(SERV_ARK_INSTALLDIR))
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
    def SUBPROC_CMD(command):
        output = subprocess.check_output(command, shell=True)
        return output.decode("utf-8")
    
    EMAIL_DATE = time.strftime("%F-%R")
    fd, fp = tempfile.mkstemp()
    f = open(fp, 'a+')
    RUNNING_MAP = SUBPROC_CMD("/bin/ps -efH --sort=+ppid | grep -E '[S]hooterGameServer' | awk '{{print $9}}' | awk -F '?' '{{print $1}}'")
    f.write("\nStats as of {} running map: {} \n".format(EMAIL_DATE, RUNNING_MAP))
    f.write(RCON_CLIENT("listplayers"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/usr/bin/top -b -n 1 | awk 'BEGIN {{}}; FNR <= 7; /ShooterG/{print}'"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/usr/bin/iostat -N -m"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/bin/df -h --exclude-type=tmpfs --total"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/usr/bin/du -h /opt --max-depth=1"))
    f.seek(0)
    
    EMAIL(f.read(), "Ark Server report as of {}".format(EMAIL_DATE))
    
    os.close(fd)


#============================#
## Run get_args
start, shutdown, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save, emailstats = get_args()

if rcon:
    RCON_CLIENT()
    sys.exit(0)

## Create ssh connection
sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)

if start:
    UPSERVER()
    SERV_MONITOR()
elif shutdown:
    DOWNSERVER()
    SERV_MONITOR()
elif restart:
    RESTART_SERVER()
    SERV_MONITOR()
elif monitor:
    SERV_MONITOR()
elif update:
    UPDATE()
    RESTART_SERVER()
    SERV_MONITOR()
elif updateonly:
    UPDATE()
elif modsupdate:
    MOD_MGMT()
elif cleanup:
    MOD_CLEANUP()
elif save:
    FNC_DO_SAVE()
elif emailstats:
    #EMAIL_STATS()
    print('WIP')
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

## Close ssh connection, this is also done in functions
sshconnect.client.close()
