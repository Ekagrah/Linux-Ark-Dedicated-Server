#!/usr/bin/env python3

## paramiko library is needed and scp module for paramiko, pip install paramiko and pip install scp
## Designed to run from a Windows machine to a linux hosted server, paths
## in MOD_MGMT method would need to be changed to run successfully on Mac OS or Linux

## Additionally, I am using an ssh key, if password is preferred adjust ssh class
## to connect with password and comment out connection via key and the user key variable

## See my documentation on how linux server is set up

## Start user editable section, default ports provided

MAP = 'TheIsland'
#MAP = 'ScorchedEarth_p'
#MAP = 'Aberration_P'
#MAP = 'Extinction_P'
#MAP = 'TheCenter'
#MAP = 'Ragnarok'
#MAP = 'skiesofnazca'

LOCAL_ARK_INSTALLDIR = 'F:\steam-games\steamapps\common\ARK'
SERV_ARK_INSTALLDIR = '/opt/game'
SERVER_HOSTNAME = 'arkserv'
## Maximum number of players
NPLAYERS = '5'
SERV_PORT = '7777'
QUERY_PORT = '27015'
RCON_ACTIVE = 'True'
SERV_SAVE_DIR = '${HOME}/Documents/arksavedata'

LINUX_USER = 'servmana'
## key needs to be an openssh compatible format
LINUX_USER_KEY = 'F:\putty\id_rsa'
#LINUX_USER_PASSWORD = 'password'
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'password'

## python dictionary for desired mods
MODNAMES = {
        923607638:"More Stack",
        719928795:"Platforms Plus",
        821530042:"Upgrade Station",
        736236773:"Backpack",
        889745138:"Awesome Teleporter",
        731604991:"Structures Plus",
        506506101:"Better Beacons",
        754885087:"More Tranq + Arrow",
        916807417:"Tek Helper",
        722649005:"Redwoods Anywhere",
        859198322:"Craftable Element",
        764755314:"CKF Arch",
        703724165:"Versatile Rafts",
        1439559887:"Ammo Switcher",
        1380777369:"Additional Lighting",
        1256264907:"Tools Evolved",
        934093568:"Alien Laser Pistol",
        873924848:"Flying Rafts",
        864857312:"Undies Evolved"
}
## End user editable section

import argparse
import datetime
import logging
import os
import paramiko
import re
from scp import SCPClient
import socket
import struct
import sys
import tempfile
import time

SERV_PORT_B = int(SERV_PORT) + 1
CURR_DATE = time.strftime("%b%d_%H-%M")
class TermColor:
    RED = '\033[93;41m'
    MAGENTA = '\033[35m'
    DEFAULT = '\033[00m'


if not MAP:
    print(TermColor.MAGENTA)
    sys.exit('Missing value for MAP')


def get_args():
    """Function to get action, specified on command line, to take"""
    ## Assign description to help doc
    parser = argparse.ArgumentParser(description='Script manages various functions taken on remote ARK server')
    ## Add arguments. When argument present on command line then it is stored as True, else returns False
    parser.add_argument(
        '--start', help='Start remote server', action='store_true')
    parser.add_argument(
        '--stop', help='Stop remote server', action='store_true')
    parser.add_argument(
        '--restart', help='Restart remote server', action='store_true')
    parser.add_argument(
        '--monitor', help='Reports back if server is running and accessible', action='store_true')
    parser.add_argument(
        '--update', help='Checks for and applies update to dedicated server, restarts instance', action='store_true')
    parser.add_argument(
        '--updateonly', help='Only checks for and applies update to dedicated server', action='store_true')
    parser.add_argument(
        '--modupdate', help='Checks for updates to mod content uing local ark install', action='store_true')
    parser.add_argument(
        '--cleanup', help='Removes unnecessary mod content', action='store_true')
    parser.add_argument(
        '--rcon', help='Launches interactive rcon session', action='store_true')
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    start = args.start
    stop = args.stop
    restart = args.restart
    monitor = args.monitor
    update = args.update
    updateonly = args.updateonly
    modsupdate = args.modupdate
    cleanup = args.cleanup
    rcon = args.rcon
    save = args.save
    ## Return all variable values
    return start, stop, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save
    

class ssh:
    """Create ssh connection"""
    ## something in the command functions makes things return inconsistently, like a delay is needed before after/while waiting for command return
    client = None
    def __init__(self, server, port, user):
        "Create ssh connection"
        self.client = paramiko.client.SSHClient()
        keyfile = paramiko.RSAKey.from_private_key_file(LINUX_USER_KEY)
        self.client.load_system_host_keys()
        #self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(server, port, username=user, pkey=keyfile)
        #self.client.connect(server, port, username=user, password=password)
    
    def sendCommand(self, command):
        """Send command over ssh transport connection"""
        if self.client:
            self.transport = self.client.get_transport()
            self.channel = self.transport.open_session()
            ## verify transport open and exit gracefully
            if self.channel:
                self.channel.exec_command(command)
                data_buffer = None
                while not self.channel.exit_status_ready():
                    if self.channel.recv_ready():
                        data_buffer = self.channel.recv(1024)
                        while data_buffer:
                            sys.stdout.write(data_buffer.decode())
                            data_buffer = self.channel.recv(1024)
                    if self.channel.recv_stderr_ready():
                        error_buffer = self.channel.recv_stderr(1024)
                        while error_buffer:
                            sys.stderr.write(error_buffer.decode("utf-8"))
                            error_buffer = self.channel.recv_stderr(1024)
                exit_status = self.channel.recv_exit_status()
        else:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
    ## end def sendCommand
    
    def parseCommand(self, command, target):
        """Send command over ssh transport connection"""
        if self.client:
            self.transport = self.client.get_transport()
            self.channel = self.transport.open_session()
            ## verify transport open and exit gracefully
            if self.channel:
                self.channel.exec_command(command)
                data_buffer = None
                fd, fp = tempfile.mkstemp()
                while not self.channel.exit_status_ready():
                    if self.channel.recv_ready():
                        #data_buffer.append(self.channel.recv(1024))
                        data_buffer = self.channel.recv(1024)
                        while data_buffer:
                            with open(fp, 'w') as f:
                                f.write(data_buffer.decode())
                            with open(fp) as f:
                                f.seek(0)
                                pattern = re.compile(target)
                                for line in f:
                                    if pattern.match(line):
                                        return True
                                    else:
                                        return False
                    if self.channel.recv_stderr_ready():
                        error_buffer = self.channel.recv_stderr(1024)
                        while error_buffer:
                            error = sys.stderr.write(error_buffer.decode("utf-8"))
                            error_buffer = self.channel.recv_stderr(1024)
                            
                os.close(fd)
                exit_status = self.channel.recv_exit_status()
        else:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
    ## end def parseCommand
## end ssh class


def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available"""
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
            command_string = input("Command: ")
            if command_string in ('exit', 'Exit', 'E'):
                sys.exit("Exiting rcon client...")

        sock = socket.create_connection((SERVER_HOSTNAME,RCON_SERVER_PORT))
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
        print(response_txt)
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
    
    ## end main loop
## end def RCON_CLIENT


def CHECK_PLAYERS():
    """Check if players are connected to server"""
    chktimeout=12
    while True:
        if chktimeout > 0:
            PLAYER_LIST = RCON_CLIENT("listplayers")
            if not PLAYER_LIST:
                return False
            else:
                RCON_CLIENT("listplayers")
                time.sleep(20)
                chktimeout -= 1
                    
        else:
            sshconnect.client.close()
            sys.exit('Timeout waiting for users to log off')


def UPSERVER():
    TMUX_CHK = sshconnect.parseCommand("tmux list-session 2>/dev/null | cut -d \: -f 1", "arkserver")
    if TMUX_CHK:
        sshconnect.sendCommand("tmux kill-session -t arkserver")
        time.sleep(10)
        print("Starting server")
        sshconnect.sendCommand("tmux new-session -d -x 23 -y 80 -s arkserver {}/ShooterGame/Binaries/Linux/ShooterGameServer \"{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -USEALLAVAILABLECORES -usecache -server -servergamelog\"".format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT))
    else:
        print("Starting server")
        sshconnect.sendCommand("tmux new-session -d -x 23 -y 80 -s arkserver {}/ShooterGame/Binaries/Linux/ShooterGameServer \"{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -USEALLAVAILABLECORES -usecache -server -servergamelog\"".format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT))
    

def DOWNSERVER():
    UPCHK = sshconnect.parseCommand("pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
    downcounter = 24
    if UPCHK:
        sshconnect.sendCommand("tmux send-keys C-c -t arkserver")
    else:
        print("Unable to find running server")
    while True:
        TMUX_CHK = sshconnect.parseCommand("tmux list-session 2>/dev/null | cut -d \: -f 1", "arkserver")
        if TMUX_CHK:
            if downcounter == 0:
                print('Forcfully killing server instance')
                sshconnect.sendCommand("tmux kill-session -t arkserver")
                time.sleep(5)
                sshconnect.sendCommand("for i in $(\pgrep -c ShooterGameServ 2>/dev/null); do kill -9 $i; done")
                return False
            else:
                print("Waiting for server to go down gracefully")
                time.sleep(5)
        else:
            print("Unable to find running server")
            return False


def RESTART_SERVER():
    RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
    CHECK_PLAYERS()
    RECENT_SAVE = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
    if not RECENT_SAVE:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
        if SAVE_CHK:
            print("Recent save found")
            DOWNSERVER()
            time.sleep(10)
            UPSERVER()
        else:
            sshconnect.client.close()
            sys.exit("Unable to verify save, not restarting server")
    else:
        print("Recent save found")
        DOWNSERVER()
        time.sleep(10)
        UPSERVER()
    

def SERV_MONITOR():
    """Checks on status of server"""
    upcounter = 15
    SERV_STATUS_CHK = sshconnect.parseCommand("pgrep -x ShooterGameServ 2>/dev/null", "[0-9]*")
    if SERV_STATUS_CHK:
        print("Server is running")
    else:
        sshconnect.client.close()
        sys.exit("Server does not seem to be running")
    while True:
        PORT_CHK = sshconnect.parseCommand("\\netstat -puln 2>/dev/null | \grep ShooterGame | \grep {}".format(SERV_PORT_B), ".*:{}.*".format(SERV_PORT_B))
        if PORT_CHK:
            sys.exit("Server is up and should be accessible")
        else:
            if upcounter > 0:
                print("Waiting on server...")
                time.sleep(20)
                upcounter -= 1
            else:
                sshconnect.client.close()
                sys.exit("Server not up yet, manually monitor status...")
   
    
def CHECK_SERV_UPDATE():
    """Check if update to server has been posted"""
    ## fix for conflicting file that can prevent getting the most recent version
    sshconnect.sendCommand("if [[ -e ${HOME}/.steam/steam/appcache/appinfo.vdf ]]; then rm ${HOME}/.steam/steam/appcache/appinfo.vdf ; fi")
    ## See if update is available
    UPDATE_CHK = sshconnect.parseCommand('new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | grep -A5 "branches" | awk -F \'\"\' \'/buildid/{{print $4}}\' )" ; curr_vers="$( awk -F \'\"\' \'/buildid/{{print $4}}\' {0}/steamapps/appmanifest_376030.acf )\" ; if [[ ${{new_vers}} -gt ${{curr_vers}} ]]; then echo "update-needed" ; else echo "up-to-date" ; fi'.format(SERV_ARK_INSTALLDIR), "up-to-date")
    if UPDATE_CHK:
        sshconnect.client.close()
        sys.exit("Server reports up-to-date")
    else: 
        return True
        

def UPDATE():
    """Perform update to server version"""
    if not CHECK_PLAYERS() and CHECK_SERV_UPDATE():
        updatetimeout = 5
        while updatetimeout > 0:
            ## this is slow and times out occasionally
            sshconnect.sendCommand("/usr/games/steamcmd +login anonymous +force_install_dir {} +app_update 376030 public validate +quit | tee /var/tmp/arktmp".format(SERV_ARK_INSTALLDIR))
            ## so we must verify it completed
            UPD_STATE = sshconnect.parseCommand("\tail -5 /var/tmp/arktmp | awk -F \" \" '/.*App.*376030.*/{{print $1}}' )\"", "Success")
            if UPD_STATE:
                print("Ark server is up-to-date")
                sshconnect.sendCommand("rm -f /var/tmp/arktmp")
                return True
            elif updatetimeout == 0:
                print("Issue completing update. Check permissions\nand disk space for starters.")
                sshconnect.sendCommand("rm -f /var/tmp/arktmp")
                sshconnect.client.close()
                sys.exit(10)
            else:
                print("restarting update")
                updatetimeout -= 1


def FNC_DO_SAVE():
    """Archive map, player/tribe, and configuration files into a zip"""
    RECENT_SAVE = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
    if RECENT_SAVE:
        ## is a find command better?
        sshconnect.sendCommand("curr_date=\"$( \date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then \mkdir -p \"${{tar_dir}}\" ; fi ; echo \"Copying files to {2}/${{tar_dir}}...\" ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; echo \"Making tarball...\" ; \tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && rm -rf ./${{tar_dir}} ; echo \"Successfully made save bundle\" || echo \"Unable to make tarball...\"".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR))
    else:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        SAVE_CHK = sshconnect.parseCommand('if [[ $(( $(\date +%s) - $(\stat -c %Y {}/ShooterGame/Saved/SavedArks/{}.ark) )) -lt 180 ]]; then echo "save-found" ; fi'.format(SERV_ARK_INSTALLDIR, MAP), "save-found")
        if SAVE_CHK:
            sshconnect.sendCommand("curr_date=\"$( \date +%b%d_%H-%M )\" map=\"{0}\"; cd {2} ; tar_dir=\"${{map%_P}}-${{curr_date}}\" ; if [[ ! -d \"${{tar_dir}}\" ]] ; then \mkdir -p \"${{tar_dir}}\" ; fi ; echo \"Copying files to {2}/${{tar_dir}}...\" ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/Game.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}.ark \"${{tar_dir}}\"/{0}_${{curr_date}}.ark ; cp \"{1}\"/ShooterGame/Saved/SavedArks/{0}_AntiCorruptionBackup.bak \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arkprofile \"${{tar_dir}}\"/ ; cp \"{1}\"/ShooterGame/Saved/SavedArks/*.arktribe \"${{tar_dir}}\"/ ; echo \"Making tarball...\" ; \\tar -czf ark-{0}-\"${{curr_date}}\".tar ./\"${{tar_dir}}\" && rm -rf ./${{tar_dir}} ; echo \"Successfully made save bundle\" || echo \"Unable to make tarball...\"".format(MAP, SERV_ARK_INSTALLDIR, SERV_SAVE_DIR))
        else:
            print("Unable to verify world was recently saved, exiting...")
            sys.exit(11)
        

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
    print(MODS_UPDATED)
    scp.close()

   
def MOD_CLEANUP():
    """Clean up extra mod content that is not part of the active mods in GameUserSettings.ini"""
    DIR_CHK = sshconnect.parseCommand("if [[ -d {} ]]; then echo 'exists' ; fi".format(SERV_ARK_INSTALLDIR), "exists")
    if DIR_CHK:
        ## if existing file has match under ActiveMods then remove it from array
        sshconnect.sendCommand("\sed -n 's/ActiveMods=//p' {}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini | \awk -v FS=\",\" '{{OFS=\" \"; $1=$1; print $0}}' ; declare -a mod_list ; while IFS=  read -r -d $'\0'; do mod_list+=(\"$REPLY\") ; done < <(\find ./ -name '*.mod' -print0 | \sed -e 's|./111111111.mod||' -e 's|./||g' -e 's|.mod||g') ; arr_id=0 ; for m in $(\echo ${{mod_list[@]}} ) ; do if [[ $(\echo ${{active_mods}} | \grep -o ${{m}}) == \"${{m}}\" ]]; then unset mod_list[${{arr_id}}] ; else echo \"Marking ${{m}} for removal\" fi ; let arr_id++ ; done ; unset arr_id ; if [[ ${{#mod_list[@]}} -gt 0 ]] ; then for d in $(\echo ${{mod_list[@]}}) ; do ; echo \"Deleting data for mod: ${{d}}\" ; rm -rf ./${{d}}* ; done ; else echo \"No files to remove/modify\" ; fi ; cd /opt ; unset active_mods ; unset mod_list ".format(SERV_ARK_INSTALLDIR))
        sys.exit()
    else:
        print('SERV_ARK_INSTALLDIR seems invalid')
        sys.exit(12) 


#============================#
## Run get_args
start, stop, restart, monitor, update, updateonly, modsupdate, cleanup, rcon, save = get_args()

if rcon:
    RCON_CLIENT()

## Create ssh connection
sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER)
#sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)

if start:
    UPSERVER()
    SERV_MONITOR()
elif stop:
    DOWNSERVER()
    SERV_MONITOR()
elif restart:
    RESTART_SERVER()
    time.sleep(10)
    SERV_MONITOR()
elif monitor:
    SERV_MONITOR()
elif update:
    UPDATE()
    RESTART_SERVER()
    time.sleep(10)
    SERV_MONITOR()
elif updateonly:
    UPDATE()
elif modsupdate:
    MOD_MGMT()
elif cleanup:
    MOD_CLEANUP()
elif save:
    FNC_DO_SAVE()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

## Close ssh connection, this is also done in functions
sshconnect.client.close()
