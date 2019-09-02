#!/usr/bin/env python3

## see my documentation on how linux server is set up
## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110

## Can change the server launch options in the similarly named function

## Auto managing of mods requires -automanagedmods specified on commandline for server launch, uses ActiveMods from GameUserSettings and running ... steamcmdsetup ... but doesn't play well with my server setup, submitted a bug

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
#MAP_NAME = 'skiesofnazca'

SERV_ARK_INSTALLDIR = '/opt/game'
## Maximum number of players, default 70
NPLAYERS = '15'
SERV_PORT = '7777'
QUERY_PORT = '27015'

## File used to to track if a new connection has been made
CONN_TRACK_FILE = '/opt/bin/estb-conn'

RCON_ACTIVE = 'True'
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'secret'

## Email address to send and receive from
EMAIL_ADDR = 'email@example.com'
## Directory used when creating data archive
SERV_SAVE_DIR = '/home/user/Documents/arksavedata'

##------End user editable section------##

import argparse
import os
from pathlib import Path
import re
from shutil import copy2, rmtree
import socket
import struct
import subprocess
import sys
import tempfile
import time

SERV_PORT_B = int(SERV_PORT) + 1
CURR_DATE = time.strftime("%b%d_%H-%M")
## In Python 3.5+ you can use pathlib.Path.home()
home = str(Path.home())
devnull = open(os.devnull, 'w')


def VARIABLE_CHK():
    """Verify needed variables have proper value"""
    
    class TermColor:
        RED = '\033[93;41m'
        MAGENTA = '\033[35m'
        DEFAULT = '\033[00m'
    
    varchk = [MAP, SERV_ARK_INSTALLDIR, NPLAYERS, SERV_PORT, QUERY_PORT, RCON_ACTIVE, RCON_SERVER_PORT, RCON_PASSWORD, EMAIL_ADDR, SERV_SAVE_DIR]
    
    varlist = ["MAP", "SERV_ARK_INSTALLDIR", "NPLAYERS", "SERV_PORT", "QUERY_PORT", "RCON_ACTIVE", "RCON_SERVER_PORT", "RCON_PASSWORD", "EMAIL_ADDR", "SERV_SAVE_DIR"]
    
    err_on_var = []
    invalid_var = []
    for id, x in enumerate(varchk):
        if not x:
            err_on_var.append(varlist[id])
            break
        elif id == 2:
            ## interval comparison
            if not 1 <= int(x) <= 70:
                invalid_var.append(varlist[id])
        elif id in  ("3", "4", "6"):
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


#def get_args(args=None):
def get_args():
    """Function to get action, specified on command line"""
    
    ## Assign description to help doc
    parser = argparse.ArgumentParser(description='Script manages various functions taken on local linux ARK server. One action accepted at a time.', allow_abbrev=False)
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
        '--cleanup', help='Removes unnecessary mod content', action='store_true')
    parser.add_argument(
        '--rcon', help='Launches interactive rcon session, can also specify command to be sent', action=RconAction)
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--emailstats', help='Sends an email with information on filesystems, cpu, etc.', action='store_true')
    parser.add_argument(
        '--connections', help='Monitor connections, intended for use as a cronjob', action='store_true')
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    start = args.start
    shutdown = args.shutdown
    restart = args.restart
    monitor = args.monitor
    update = args.update
    updateonly = args.updateonly
    cleanup = args.cleanup
    rcon = args.rcon
    save = args.save
    emailstats = args.emailstats
    connections = args.connections
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, cleanup, rcon, save, emailstats, connections
    
    if not len(sys.argv) >= 2:
        parser.print_help()
        sys.exit(1)


def SERV_STATUS_CHK():
    """function for verifying server is running"""
    output = ''
    try:
        output = subprocess.check_output("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", shell=True).decode("utf-8")
    except subprocess.CalledProcessError:
        return False
        
    if not output:
        return False
    else:   
        pattern = re.compile("[0-9]{3,}")
        for line in output.split('\n'):
                if pattern.match(line):
                    return True
                else:
                    return False
                

def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available. Original code by Dunto, updated/modified by Ekagrah"""
    
    if not SERV_STATUS_CHK():
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
            ## per Source RCON protocol documentation
            ## id=4 + type=4 + message len in bytes + null terminator=2 (1 for python string and 1 for message terminator)
            message_size = (4 + 4 + command_len + 2)
            ## struct string formatting
            ## '='=native byte order + 'l'=long integer + message len in bytes + 's'=bytes character(default = 1) + '2s'=count len of two bytes not a repeat count
            message_format = ''.join(['=lll', str(command_len), 's2s'])
            ## \x indicates hexidecimal notation, 0x00 = null
            ## see ASCII table
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
                print('\tUse exit or Exit to quit.')
                print('Tested commands: briadcast, ')
                continue
            elif command_string in ('') or not command_string:
                continue

        try:
            sock = socket.create_connection(("127.0.0.1", RCON_SERVER_PORT))
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


def SERV_LAUNCH():
    """Make temporary file so command can be called from there and will run independently from python script"""
    
    launchcmd = '''#!/bin/bash
    {}/ShooterGame/Binaries/Linux/ShooterGameServer "{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?RCONServerGameLogBuffer=400?ForceFlyerExplosives=True?PreventMateBoost -servergamelog -NoBattlEye -USEALLAVAILABLECORES" &
    exit 0'''.format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT, RCON_PASSWORD)
    ## -usecache -server -automanagedmods ?PreventDownloadSurvivor=True ?PreventDownloadDinos=True ?PreventDownloadItems=True ?ServerAdminPassword= ?AllowRaidDinoFeeding=True -ForceRespawnDinos -structurememopts
    
    tmpscript = tempfile.NamedTemporaryFile('wt')
    tmpscript.write(launchcmd)
    tmpscript.flush()
    
    subprocess.Popen(['/bin/bash', tmpscript.name],
        close_fds=True,
        preexec_fn=os.setsid,
        )


def UPSERVER():
    if SERV_STATUS_CHK():
        sys.exit("Server seems to be running already")
    else:
        print("Starting server")
        SERV_LAUNCH()
    time.sleep(10)


def DOWNSERVER():
    downcounter = 4
    CHECK_PLAYERS()
    
    if SERV_STATUS_CHK():
        #RCON_CLIENT("do exit")
        SERV_PID = subprocess.run("/usr/bin/pgrep -x ShooterGameServ 2>/dev/null", stdout=subprocess.PIPE, shell=True).stdout.decode("utf-8")
        subprocess.run("kill -2 {}".format(SERV_PID), shell=True)
        time.sleep(10)
    else:
        print("Unable to find running server to shutdown")
        return False
            
    while True:
        if SERV_STATUS_CHK():
            print("Waiting for server to go down gracefully")
            time.sleep(5)
            downcounter -= 1
        else:
            print("Unable to find running server to shutdown")
            return False
        if downcounter == 0:
            if SERV_STATUS_CHK():
                print("Running server still found, forcefully killing server process.")
                subprocess.run("for i in $(/usr/bin/pgrep -x ShooterGameServ); do kill -9 $i; done", shell=True, stdout=subprocess.PIPE)
                return False
            if SERV_STATUS_CHK():
                print("Unable to take server down, manual shutdown needed")
                print("Example: run 'do exit' via rcon client")
                sys.exit(3)


def RESTART_SERVER():
    """Check if no players connected, shutdown then start server"""
    
    if not CHECK_PLAYERS():
        pass
    else:
        RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
        PLAYER_MONITOR()
    
    ITEM_MTIME = os.path.getmtime(r'{}/ShooterGame/Saved/SavedArks/{}.ark'.format(SERV_ARK_INSTALLDIR, MAP))
    RECENT_SAVE = (time.time() - ITEM_MTIME)
    ## if the time difference (current time - file modification time) is greater than 3 minutes then act
    if RECENT_SAVE > 180:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        ITEM_MTIME = os.path.getmtime(r'{}/ShooterGame/Saved/SavedArks/{}.ark'.format(SERV_ARK_INSTALLDIR, MAP))
        RECENT_SAVE = (time.time() - ITEM_MTIME)
        if RECENT_SAVE <= 180:
            print("Recent save found")
            DOWNSERVER()
            time.sleep(10)
            UPSERVER()
        else:
            sys.exit("Unable to verify save, not restarting server")
    else:
        print("Recent save found")
        DOWNSERVER()
        time.sleep(10)
        UPSERVER()
    

def SERV_MONITOR():
    """Checks on status of server"""
    
    ## Increase as needed, especially for community maps
    upcounter = 7
    if SERV_STATUS_CHK():
        print("Server is running")
    else:
        sys.exit("Server does not seem to be running")
    
    while True:
        rpattern = '.*:{}.*ShooterGame.*'.format(SERV_PORT_B)
        pattern = re.compile(rpattern)
        PORT_CHK = subprocess.run("/bin/netstat -puln 2>/dev/null | /bin/grep  -E '{}'".format(SERV_PORT_B, rpattern), stdout=subprocess.PIPE, shell=True) 
        if pattern.search(PORT_CHK.stdout.decode("utf-8")):
            sys.exit("Server is up and should be accessible")
        else:
            if upcounter > 0:
                print("Waiting on server...")
                time.sleep(20)
                upcounter -= 1
            else:
                sys.exit("Server not up yet, manually monitor status...")
   

def CHECK_SERV_UPDATE():
    """Check if update to server has been posted"""
    
    ## workaround for conflicting file that can prevent getting the most recent version
    if os.path.isfile("{}/.steam/steam/appcache/appinfo.vdf".format(home)):
        os.remove("{}/.steam/steam/appcache/appinfo.vdf".format(home))
    
    pattern = re.compile(r"[0-9]{7,}")
    ## See if update is available
    ## should return a byte object as b'\t\t"branches"\n\t\t{\n\t\t\t"public"\n\t\t\t{\n\t\t\t\t"buildid"\t\t"3129691"\n'
    steamcmd = """/usr/games/steamcmd +login anonymous +app_info_update 1 +app_info_print 376030 +quit | sed -n '/"branches"/,/"buildid"/p' """
    steam_out = subprocess.check_output(steamcmd, shell=True).decode("utf-8")
    new_vers = pattern.search(steam_out).group()
    
    with open("{0}/steamapps/appmanifest_376030.acf".format(SERV_ARK_INSTALLDIR)) as inFile:
        for line in inFile:
            if 'buildid' in line:
                curr_vers = pattern.search(line).group()
    
    if int(new_vers) > int(curr_vers):
        return True
    elif int(new_vers) == int(curr_vers):
         print("Server reports up-to-date")
         sys.exit()
        

def UPDATE():
    """Perform update to server version"""
    fd, tfp = tempfile.mkstemp()
    if CHECK_SERV_UPDATE():
        updatetimeout = 5
        while updatetimeout > 0:
            ## this is slow and times out occasionally
            subprocess.run("/usr/games/steamcmd +login anonymous +force_install_dir {} +app_update 376030 public validate +quit > {}".format(SERV_ARK_INSTALLDIR, tfp), shell=True)
            ## poll until complete? WIP
            
            ## so we must verify it completed
            ## Escape {} for python using {{ }}
            UPD_OUTPUT = subprocess.check_output("/usr/bin/tail -5 {} | awk -F \" \" '/.*App.*376030.*/{{print $1}}' )\"".format(tfp), shell=True)
            pattern = re.compile("Success.*")
            for line in UPD_OUTPUT.split('\n'):
                if pattern.match(line):
                    print("Ark server is up-to-date")
                    os.close(fd)
                    return True
                elif updatetimeout == 0:
                    print("Issue completing update. Check permissions\nand disk space for starters.")
                    sys.exit(10)
                else:
                    print("restarting update")
                    updatetimeout -= 1


def SAVE_ACTIONS():
    import errno
    import glob
    import tarfile
    
    def make_tarfile(output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    
    if not SERV_SAVE_DIR:
        sys.exit(11)
    tardir = "{}/{}-{}/".format(SERV_SAVE_DIR, MAP, CURR_DATE)
    
    try:
        os.makedirs(tardir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            sys.exit(11)
    ## copy game config files to temp folder for tarball
    copy2("{}/ShooterGame/Saved/Config/LinuxServer/Game.ini".format(SERV_ARK_INSTALLDIR), "{}/".format(tardir))
    
    copy2("{}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini".format(SERV_ARK_INSTALLDIR), "{}/".format(tardir))
    
    ## copy map sace data to temp dir
    copy2("{}/ShooterGame/Saved/SavedArks/{}.ark".format(SERV_ARK_INSTALLDIR, MAP), "{}/{}_{}.ark".format(tardir, MAP, CURR_DATE))
    
    copy2("{}/ShooterGame/Saved/SavedArks/{}_AntiCorruptionBackup.bak".format(SERV_ARK_INSTALLDIR, MAP), "{}/".format(tardir, MAP))
    
    ## copy player and tribe data to temp dir
    for file in glob.glob(r"{}/ShooterGame/Saved/SavedArks/*.arkprofile".format(SERV_ARK_INSTALLDIR)):
        copy2(file, "{}/".format(tardir))
    
    for file in glob.glob(r"{}/ShooterGame/Saved/SavedArks/*.arktribe".format(SERV_ARK_INSTALLDIR)):
        copy2(file, "{}/".format(tardir))
    
    try:
        print("Making tarball...")
        make_tarfile('{}/ark-{}-{}.tgz'.format(SERV_SAVE_DIR, MAP, CURR_DATE), '{}'.format(tardir))
    except FileExistsError:
        print("Unable to make tarball...")
    
    if os.path.exists('{}/ark-{}-{}.tgz'.format(SERV_SAVE_DIR, MAP, CURR_DATE)):
        print("Successfully made save bundle")
        rmtree("{}".format(tardir), ignore_errors=True)
    else:
        sys.exit("Tarball create failed...")


def FNC_DO_SAVE():
    """Archive map, player/tribe, and configuration files into a tarball"""
    
    #try:
        #MAP = MAP_NAME
    #except:
        #pass
        
    ITEM_MTIME = os.path.getmtime(r'{}/ShooterGame/Saved/SavedArks/{}.ark'.format(SERV_ARK_INSTALLDIR, MAP))
    RECENT_SAVE = (time.time() - ITEM_MTIME)
    if RECENT_SAVE <= 180:
        SAVE_ACTIONS()
    else:
        RCON_CLIENT("saveworld")
        time.sleep(10)
        ITEM_MTIME = os.path.getmtime(r'{}/ShooterGame/Saved/SavedArks/{}.ark'.format(SERV_ARK_INSTALLDIR, MAP))
        SAVE_CHK = (time.time() - ITEM_MTIME)
        if SAVE_CHK <= 180:
            SAVE_ACTIONS()
        else:
            print("Unable to verify world was recently saved, exiting...")
            sys.exit(12)

   
def MOD_CLEANUP():
    """Clean up extra mod content that is not part of the active mods in GameUserSettings.ini"""
    
    MODDIR = "{}/ShooterGame/Content/Mods".format(SERV_ARK_INSTALLDIR)
    if not os.path.exists(MODDIR):
        print('{} seems invalid'.format(MODDIR))
        sys.exit(13)
    
    ACTIVE_MODS = []
    with open('{}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini'.format(SERV_ARK_INSTALLDIR), 'r') as inFile:
        for line in inFile:
            if 'ActiveMods=' in line:
                ACTIVE_MODS = line.split(',')
                break
    ## Count through list and replace non-digit items with empty entry
    ## \D is opposite of \d; matches any character which is not a decimal digit
    for i, id in enumerate(ACTIVE_MODS):
        ACTIVE_MODS[i] = re.sub(r"\D", "", id)
        
    DIR_MODS = []
    for i in os.listdir(MODDIR):
        if (re.compile(r"[0-9]{9,}").fullmatch(i) and i != '111111111'):
            DIR_MODS.append(i)
    ## Get the difference between the two lists
    s = set(ACTIVE_MODS)
    RMMODS = [ x for x in DIR_MODS if x not in s ]
    if not RMMODS:
        print("No mod data to clean up")
        sys.exit(0)
    for id in RMMODS:
        try:
            os.remove('{}/{}.mod'.format(MODDIR, id))
            rmtree('{}/{}'.format(MODDIR,id))
            print("Removed mod data for {}".format(id))
        except:
            print("Unable to remove mod data for {}".format(id))


def EMAIL(content, subject):
    import smtplib,email.utils
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
    RUNNING_MAP = SUBPROC_CMD('/bin/ps -efH --sort=+ppid | /usr/bin/awk \'/[S]hooterGameServer/{{$0=$9; nextfile}} END {{FS="?"; ORS=""; NF=11; $0=$0; print $1}}\'')
    RUNNING_VERSION = SUBPROC_CMD("/usr/bin/find {}/ShooterGame/Saved/Logs/ -maxdepth 1 -mtime -2 -iname \"ShooterGame*.log\" -exec awk -F \": \" '/Version/{{print $2}}' {{}} \; | tail -1".format(SERV_ARK_INSTALLDIR))
    f.write("\nRunning map and version: {} {}".format(RUNNING_MAP, RUNNING_VERSION))
    f.write("\n------\n")
    f.write(RCON_CLIENT("listplayers"))
    f.write("\n------\n")
    f.write("CPU Info:\n")
    f.write(SUBPROC_CMD("/bin/cat /proc/cpuinfo | /usr/bin/head -15 | /usr/bin/awk '/model name/{{print}} ; /cpu cores/{{print}}'"))
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
    
    
def ESTB_CONN():
    '''Function to capture packets looking for specific source session and find destination
    
    Similar to:
    tcpdump udp src port ${ephemeral_port} -c 1 -s 80 -n
    
    Also like tcpdump, using this function (via --connections) will require root privileges. Add something like below to sudoers:
    
    user        ALL=(ALL:ALL)   NOPASSWD: /opt/bin/arkserv_mgmt_local.py
    
    And something like this to crontab:
        
    */3 * * * * sudo /opt/bin/arkserv_mgmt_local.py --connections
    
    '''
    
    import binascii,os
    
    capture_size = 80
    class unpack:
        '''see http://www.bitforestinfo.com/2017/01/how-to-write-simple-packet-sniffer.html'''
        def __cinit__(self):
            self.data=None
        
        ## IP Header Extraction
        def ip_header(self, data):
            storeobj=struct.unpack("!BBHHHBBH4s4s", data)
            
            _version=storeobj[0] 
            _tos=storeobj[1]
            _total_length =storeobj[2]
            _identification =storeobj[3]
            _fragment_Offset =storeobj[4]
            _ttl =storeobj[5]
            _protocol =storeobj[6]
            _header_checksum =storeobj[7]
            _source_address =socket.inet_ntoa(storeobj[8])
            _destination_address =socket.inet_ntoa(storeobj[9])
            
            data={'Version':_version,
            "Tos":_tos,
            "Total Length":_total_length,
            "Identification":_identification,
            "Fragment":_fragment_Offset,
            "TTL":_ttl,
            "Protocol":_protocol,
            "Header CheckSum":_header_checksum,
            "Source Address":_source_address,
            "Destination Address":_destination_address}
            return data
            
        ## UDP Header Extraction
        def udp_header(self, data):
            storeobj=struct.unpack('!HHHH', data)
            
            _source_port = storeobj[0]
            _dest_port = storeobj[1]
            _length = storeobj[2]
            _checksum = storeobj[3]
            data={"Source Port":_source_port,
            "Destination Port":_dest_port,
            "Length":_length,
            "CheckSum":_checksum}
            return data
            
    def packet_selection(src_port):
        '''From captured ethernet frame search the udp header containing the ephemeral ports in the list of ports'''
        
        target_src_pkt = 0
        while target_src_pkt < 1:
            # Capture packets from network
            pkt = s.recvfrom(int(capture_size))
            
            # extract packets with the help of unpack class 
            try:
                udp_port = unpack().udp_header(pkt[0][34:42])["Source Port"]
                if int(udp_port) == int(src_port):
                    target_dst_addr = unpack().ip_header(pkt[0][14:34])["Destination Address"]
                    target_src_pkt += 1
            except:
                raise Fatal('Issue unpacking capture')
        return target_dst_addr
  
    ## GGP protocol, see /etc/protocols
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.settimeout(2)

    ## Generate list of open ports that are not for the base game but program contains ShooterGame
    ports = subprocess.run("/bin/netstat -plne4 2>/dev/null | /usr/bin/awk '/.*\/ShooterGame.*/ && !/{}/ && !/{}/ && !/{}/ {{print $4}}' | /usr/bin/cut -d ':' -f 2 | /usr/bin/tr '\n' ' '".format(QUERY_PORT, SERV_PORT_B, RCON_SERVER_PORT), shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    port_list = ports.split()

    with open(CONN_TRACK_FILE, 'r+') as f:
        estb = f.readline()
        if len(port_list) > int(estb):
            conn_list = []
            for i in port_list:
                conn_ip = packet_selection(i)
                conn_list.append(conn_ip)
            print(conn_list)
            EMAIL('\n'.join(conn_list), "New players connected")
        else:
            print('No new connections')
            
        f.seek(0)
        f.write(str(len(port_list)))
        f.truncate()
    
    s.shutdown()
    s.close()


#============================#
## Run get_args
start, shutdown, restart, monitor, update, updateonly, cleanup, rcon, save, emailstats, connections = get_args()

if rcon:
    ## based on return of custom action, check if True to start interactively else run command
    if isinstance(rcon, bool):
        RCON_CLIENT()
    else:
        rcon_return = RCON_CLIENT(' '.join(rcon))
        print(rcon_return)
elif start:
    UPSERVER()
    SERV_MONITOR()
elif shutdown:
    DOWNSERVER()
    time.sleep(15)
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
elif cleanup:
    MOD_CLEANUP()
elif save:
    FNC_DO_SAVE()
elif emailstats:
    EMAIL_STATS()
elif connections:
    ESTB_CONN()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

