#!/usr/bin/env python3

## Designed to run from an iOS device with pythonista to a linux hosted server
## Look into flask

## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110


##------Start user editable section------##

#MAP = 'TheIsland'
#MAP = 'ScorchedEarth_P'
#MAP = 'Aberration_P'
#MAP = 'Extinction'
#MAP = 'TheCenter'
#MAP = 'Ragnarok'
#MAP = 'skiesofnazca'
MAP = 'Valguero_P'

## Use this when playing a community map
## Different var needed for some functions
#MAP = '-MapModId=504122600'
#MAP_NAME = 'Valhalla'

SERV_ARK_INSTALLDIR = '/opt/game'
SERVER_HOSTNAME = '192.168.0.0'
## Maximum number of players
NPLAYERS = '15'
SERV_PORT = '7777'
QUERY_PORT = '27015'
SERV_SAVE_DIR = '${HOME}/Documents/arksavedata'

LINUX_USER = 'user'
## key needs to be an openssh compatible format, if key file exists use that otherwise use password
LINUX_USER_KEY = ''
LINUX_USER_PASSWORD = 'secret'
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'secret'

##------End user editable section------##

import argparse
import datetime
import logging
import os
import paramiko
import re
import socket
import struct
import sys
import tempfile
import time

RCON_ACTIVE = 'True'
SERV_PORT_B = int(SERV_PORT) + 1
CURR_DATE = time.strftime("%b%d_%H-%M")


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
        #print('Using custom argparse action')
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
    
    ## Add arguments. When argument present on command line, then it is stored as True, else returns False
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
    ## custom action doesnt work due to how I am setting overall interactive behavior
    parser.add_argument(
        '--rcon', help='Launches interactive rcon session', action=RconAction)
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--checkplayers', help='Checks if players are connected to server', action='store_true')
        
        
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    start = args.start
    shutdown = args.shutdown
    restart = args.restart
    monitor = args.monitor
    update = args.update
    updateonly = args.updateonly
    rcon = args.rcon
    save = args.save
    checkplayers = args.checkplayers
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, rcon, save, checkplayers
    

class ssh:
    """Create ssh connection"""
    client = None
    def __init__(self, server, port, user, password=None):
        "Create ssh connection"
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        #self.client.set_missing_host_key_policy(paramiko.WarningPolicy())
        
        if os.path.exists(LINUX_USER_KEY):
            self.client.load_system_host_keys()
            keyfile = paramiko.RSAKey.from_private_key_file(LINUX_USER_KEY)
            self.client.connect(server, port, username=user, pkey=keyfile)
        elif password:
            self.client.connect(server, port, username=user, password=password)
        else:
            sys.exit("No valid authenication methods provided")

    
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
            print(TermColor.RED)
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
    sock = ''
    while interactive_mode:
        command_string = None
        response_string = None
        response_id = -1
        response_type = -1
        if args:
            interactive_mode = False
            command_string = str(args[0])
            print("RCON command sent: {}".format(command_string))
        else:
            command_string = input("RCON Command: ")
            if command_string in ('exit', 'Exit'):
                
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                print("Exiting rcon client...\n")
                break
            elif command_string in ('help','h','Help'):
                print('\tUse exit or Exit to quit.')
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
    TMUX_CHK = sshconnect.sendCommand("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", parse=True, target="[0-9]*")
    if TMUX_CHK:
        print("Server seems to be running already")
    else:
        print("Starting server")
        sshconnect.sendCommand('{}/ShooterGame/Binaries/Linux/ShooterGameServer "{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?RCONServerGameLogBuffer=400?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True?PreventMateBoost -servergamelog -NoBattlEye -USEALLAVAILABLECORES" &'.format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT), stdoutwrite=True, timeout=2)
        ## tmux new-session -d -x 23 -y 80 -s arkserv
        ## the server console accessed by:
        ## tmux attach-session -t arkserv
        ## ctrl + b then d to disconnect
        ## -usecache -server -automanagedmods  ?PreventDownloadSurvivor=True?PreventDownloadDinos=True?PreventDownloadItems=True ??ServerAdminPassword= ?AllowRaidDinoFeeding=True -ForceRespawnDinos
    

def DOWNSERVER():
    """Shutdown server instance"""
    
    downcounter = 4
    if UPCHK():
        SERV_PID = sshconnect.sendCommand("/usr/bin/pgrep -u {} ShooterGameServ 2>/dev/null".format(LINUX_USER))
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
    """Check if players are disconnected then shutdown then start server"""
    
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
    upcounter = 14
    if UPCHK():
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
    """Check if update to server has been posted
    
    new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | /bin/grep -A5 "branches" | /usr/bin/awk -F '\"' '/buildid/{{print $4}}' )" ; curr_vers="$( /usr/bin/awk -F '\"' '/buildid/{{print $4}}' /opt/game/steamapps/appmanifest_376030.acf )" ; if [[ ${new_vers} -gt ${curr_vers} ]]; then echo "update-needed" ; else echo "up-to-date" ; fi
    
    /usr/games/steamcmd +login anonymous +force_install_dir /opt/game +app_update 376030 public validate +quit
    """
    
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


#============================#

orig_sys_argv = sys.argv
cmdline = ''
sshconnect = ''
while True:
    sys.argv = orig_sys_argv
    working_sys_argv = orig_sys_argv
    mylist = []
    command_string = ''
    if len(sys.argv) < 2:
        command_string = input("Command: ")
        if command_string in ('exit', 'Exit'):
            if sshconnect:
                sshconnect.client.close()
            sys.exit('Exiting mgmt program')
        elif not command_string:
            continue
        elif command_string == 'help':
            print('With interactive mode, same args are available but accepted without "--"\n')
            mylist.append('-{}'.format(command_string))
            sys.argv = [working_sys_argv[0]] + mylist
        else:
            ## Format so that the option can be used with argparse
            mylist.append('--{}'.format(command_string))
            sys.argv = [working_sys_argv[0]] + mylist
    elif len(sys.argv) == 2:
        cmdline = True
    else:
        print('Too many arguments provided.')
        print(' --help, for usage')
        break
    
    ## Run get_args
    start, shutdown, restart, monitor, update, updateonly, rcon, save, checkplayers = get_args()
    
    ## Create ssh connection
    sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)
    
    if rcon:
        RCON_CLIENT()
    elif start:
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
        if UPDATE():
            RESTART_SERVER()
            SERV_MONITOR()
    elif updateonly:
        UPDATE()
    elif save:
        FNC_DO_SAVE()
    elif checkplayers:
        LIST_PLAYERS()

    if cmdline:
        ## Close ssh connection
        sshconnect.client.close()
        sys.exit(0)
