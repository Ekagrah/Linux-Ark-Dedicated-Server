#!/usr/bin/env python3
## see my documentation on how linux server is set up
## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110

## Can change the server launch options in the similarly named function

## Auto managing of mods requires -automanagedmods specified on commandline for server launch, uses ActiveMods from GameUserSettings and running ... steamcmdsetup ... but doesn't play well with my server setup

##------Start user editable section------##

#MAP = 'TheIsland'
#MAP = 'ScorchedEarth_P'
#MAP = 'Aberration_P'
#MAP = 'Extinction'
#MAP = 'TheCenter'
MAP = 'Ragnarok'
#MAP = 'skiesofnazca'

SERV_ARK_INSTALLDIR = '/opt/game'
## Maximum number of players, default 70
NPLAYERS = '15'
SERV_PORT = '7777'
QUERY_PORT = '27015'
RCON_ACTIVE = 'True'
RCON_SERVER_PORT = '32330'
RCON_PASSWORD = 'password'

## Email address to send and receive from
EMAIL_ADDR = 'email@gmail.com'
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


def get_args():
    """Function to get action, specified on command line, to take for server"""
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
        '--rcon', help='Launches interactive rcon session', action='store_true')
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--emailstats', help='Sends an email with information on filesystems, cpu, etc.', action='store_true')
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
    ## Return all variable values
    return start, shutdown, restart, monitor, update, updateonly, cleanup, rcon, save, emailstats
    
    if not len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)


def SERV_STATUS_CHK():
    """Method for verifying server is running"""
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
    chktimeout=12
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
            sys.exit('Timeout waiting for users to log off')


def SERV_LAUNCH():
    """Make temporary file so command can be called from there and will run independently from python script"""
    
    launchcmd = '''#!/bin/bash
    {}/ShooterGame/Binaries/Linux/ShooterGameServer "{}?listen?MaxPlayers={}?QueryPort={}?Port={}?RCONEnabled={}?RCONPort={}?RCONServerGameLogBuffer=400?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -servergamelog -NoBattlEye -USEALLAVAILABLECORES" &
    exit 0'''.format(SERV_ARK_INSTALLDIR, MAP, NPLAYERS, QUERY_PORT, SERV_PORT, RCON_ACTIVE, RCON_SERVER_PORT)
    ## -usecache -server -automanagedmods ?PreventMateBoost ?PreventDownloadSurvivor=True?PreventDownloadDinos=True?PreventDownloadItems=True -ForceRespawnDinos
    
    tmpscript = tempfile.NamedTemporaryFile('wt')
    tmpscript.write(launchcmd)
    ## 
    tmpscript.flush()
    
    subprocess.Popen(['/bin/bash', tmpscript.name],
        close_fds=True,
        preexec_fn=os.setsid,
        )
    #subprocess.Popen(['/bin/bash', tmpscript.name], close_fds=True)


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
    else:
        print("Unable to find running server to shutdown")
        return False
            
    while True:
        if SERV_STATUS_CHK():
            print("Waiting for server to go down gracefully")
            time.sleep(10)
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
    RCON_CLIENT("broadcast Server going down for maintenance in 3 minutes")
    
    CHECK_PLAYERS()
    
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
    ## fix for conflicting file that can prevent getting the most recent version
    if os.path.isfile("{}/.steam/steam/appcache/appinfo.vdf".format(home)):
        os.remove("{}/.steam/steam/appcache/appinfo.vdf".format(home))
    pattern = re.compile(r"[0-9]{7,}")
    ## See if update is available
    ## should return a byte object as b'\t\t"branches"\n\t\t{\n\t\t\t"public"\n\t\t\t{\n\t\t\t\t"buildid"\t\t"3129691"\n'
    steamcmd = """/usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | sed -n '/"branches"/,/"buildid"/p' """
    steam_out = subprocess.check_output(steamcmd, shell=True).decode("utf-8")
    new_vers = pattern.search(steam_out).group()
    
    with open("{0}/steamapps/appmanifest_376030.acf".format(SERV_ARK_INSTALLDIR)) as inFile:
        for line in inFile:
            if 'buildid' in line:
                curr_vers = pattern.search(line).group()
    
    if int(new_vers) > int(curr_vers):
        return True
    elif int(new_vers) == int(curr_vers):
         sys.exit("Server reports up-to-date")
        

def UPDATE():
    """Perform update to server version"""
    fd, tfp = tempfile.mkstemp()
    if CHECK_SERV_UPDATE():
        updatetimeout = 5
        while updatetimeout > 0:
            ## this is slow and times out occasionally
            subprocess.run("/usr/games/steamcmd +login anonymous +force_install_dir {} +app_update 376030 public validate +quit > {}".format(SERV_ARK_INSTALLDIR, tfp), shell=True)
            ## poll until complete
            
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
    copy2("{}/ShooterGame/Saved/Config/LinuxServer/Game.ini".format(SERV_ARK_INSTALLDIR), "{}/".format(tardir))
    
    copy2("{}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini".format(SERV_ARK_INSTALLDIR), "{}/".format(tardir))
    
    copy2("{}/ShooterGame/Saved/SavedArks/{}.ark".format(SERV_ARK_INSTALLDIR, MAP), "{}/{}_{}.ark".format(tardir, MAP, CURR_DATE))
    
    copy2("{}/ShooterGame/Saved/SavedArks/{}_AntiCorruptionBackup.bak".format(SERV_ARK_INSTALLDIR, MAP), "{}/".format(tardir, MAP))
    
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


#============================#
## Run get_args
start, shutdown, restart, monitor, update, updateonly, cleanup, rcon, save, emailstats = get_args()

if start:
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
elif rcon:
    RCON_CLIENT()
elif save:
    FNC_DO_SAVE()
elif emailstats:
    EMAIL_STATS()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

