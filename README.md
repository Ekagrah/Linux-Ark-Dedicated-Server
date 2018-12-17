# Linux ARK Survival Evolved Dedicated Server

When we started this crazy idea to run our own dedicated server we knew very little. We manually managed copying of mods, this was running on a Windows machine, and my friend wasn't fond of administering the server. When Ragnarok was released, I set up a dedicated server on Lubuntu 16.04 using LGSM but decided it was more fun to write my own scripts.


Getting Started
------

First, decide what mods you want. Here is a [link](http://steamcommunity.com/sharedfiles/filedetails/?id=847707731) to my Steam Collection and you will see the list in my code.
  
Next, set up a virtual machine. I'm sinply using VirtualBox. I wont detail that here but see this guide https://linus.nci.nih.gov/bdge/installUbuntu.html (provided by National Cancer Institute). I use lvm with about 20GB provided to /opt, 9GB of RAM, and 2 CPU (3.2 GHz Xeon). This has been sufficient for 5 or so people playing at a time.

#### Install steamcmd and ARK Dedicated Server

1. Install steamcmd package. Example:
```
sudo apt-get install steamcmd
```

2. Launch steamcmd once for it to update
```
/usr/games/steamcmd
steam> exit
```

3. Install dedicated server to desired location (given after force_install_dir)
```
/usr/games/steamcmd +login anonymous +force_install_dir /opt/game +app_update 376030 public validate +quit
```
This same command is used to install and update the dedicated server

4. On your machine you will be playing Ark on, you will add the scripts as described below. Run CMD as administrator and run: pip install paramiko scp to install dependencies.
 

Using Scripts
------

#### UPDATE 2: Reorganize README structure. Instructions for new python script:

*MAKE SURE TO EDIT VARIABLES IN THE USER EDITABLE SECTION*

Copy arkserv_mgmt_local.py to linux server somewhere, the directory you place it in needs to match SERV_BIN within arkserv_mgmt.py.

When Steam does a mod update, launch ARK and it will show progress of mod installation in the bottom right corner. Once that is completed execute arkserv_mgmt.py --modupdate to copy mods to server.

Restart following copy completion using arkserv_mgmt.py --restart

See script help for more details on functions


*Notes:*

* arkserv_mgmt_remote.py can do everything but email stats, no need to have both arkserv_mgmt_local.py on the server and arkserv_mgmt.py just use the remote script for administration.
* I have a version of the remote script I use on my iPhone with Pythonista if anyone is interested.


#### UPDATE 1: Transition to full python

I have added a local python script to replace the bash script. Using this inconjunction with arkux-mod-mgmt.ps1. Will be adding a python script to do all management from a Windows machine.


#### ORIGINAL:
MAKE SURE TO EDIT .SH AND .PS1 SCRIPT VARIABLES FOR YOUR INSTALL

Will need the putty tools plink.exe and pscp.exe

On the server add the python rcon client and \*.sh scripts to /opt/bin. If you want them somewhere else edit the arkserv_dinoreset.sh, arkserv_mgmt.sh, all powershell scripts and arkcustomstats.sh to point to the new location. Still working on logic to handle errors gracefully within script should the rcon client not be able to connect.

My idea of managing the mods took several iterations and trial and error. Eventually I arrived at my posted scripts which should take minimal customization to work for anyone (be gentle its my first time writing code for a public audience).

When Steam does a mod update, launch ARK and it will show progress of mod installation in the bottom right corner. Once that is completed launch the powershell script and everything should work to copy to the server any of the specified mods that have updated then to restart the server.

The idea is that the powershell script, arkux-mod-mgmt.ps1, will live on your gaming rig and be run from there when mods update. I typically run the ark-mod-probe.ps1 first to see if there is anything to do, mainly habit from this process of experimentation. I used the arkuxserv_initialize.ps1 to get all the mods to the server when setting it up.

I have added some quality of life items:

  * arkserv_dinoreset.sh to work as a crontab entry for periodically resetting dino's on server  
  * arkcustomstats.sh also a crontab entry to email me stats several times a day
  * arkserv_monitor.sh to quickly let me know if server is running and accessible


## Troubleshooting

* Use \`netstat -puln 2\>/dev/null | grep ShooterGame\' to check status of server. When you have two lines with one showing ':7778' then the server should be accessible.
* Use \`ps -ef | grep -i ShooterGame\' ~~to see that there are two processess, one of which is a tmux session~~ to see related processess.
* Report errors and I'll be happy to address them. I tried to anticipate as many scenarios as possible but this is a first for me.
* I no longer use Steam GUI for server updates, but if someone takes that route here is a link to fix the Steam app not launching in Ubuntu https://askubuntu.com/questions/771032/steam-not-opening-in-ubuntu-16-04-lts#771507.

General Information
------
* You can customize the game experience using the Game.ini and GameUserSettings.ini found in the directory where you installed the dedicated server under /ShooterGame/Saved/Config/LinuxServer/. I have had to launch the server once to get all the rest of the folders auto created. ```/ShooterGame/Binaries/Linux/ShooterGameServer``` should be sufficient. Exit using CTRL+c.
* puttygen.exe is good to use for generating ssh keys.
* After a few minutes your server should be available. Some may not see it on the ARK in-game server list so you if you message them via Steam with a link like \`steam://connect/\<external-ip\>:27015\' people should be able to connect - this link also works if entered in IE/Edge but not Chrome.... Note: I have not found a better work around for people not finding my server via in-game 'Join Ark' option. Also, can connect via Steam > View > Servers.

## To-Do



## Authors

Ekagrah - ekagrah.gamer@gmail.com, ekagrah@icloud.com


## License


## Acknowledgments

* Would be nowhere without alien.system's guide, highly recommend reading to really understand your dedicated server - http://steamcommunity.com/sharedfiles/filedetails/?id=656433788
* Dunto's python rcon client - see https://gist.github.com/Dunto/e310c00e84b98e0e90dd (which I have forked)
* Linux Game Server Manager - their method was what I was looking for to address the process being killed after the plink session closed (this is why I stopped using the Steam UI to do updates). They have done some solid work!
* Gamepedia has been helpful finding information about managing the server, though it can be out of date. See https://ark/gamepedia.come/Console_Commands

## Old but may be helpful to someone

Install LinuxGSM:

1. Ensure write premissions to /opt 
2. Follow these instructions to get LinuxGSM - http://gameservermanagers.com/lgsm/arkserver/#gettingstarted
3. You will now have /opt/linuxgsm.sh, /opt/lgsm, and /opt/arkserver
4. Adjust configuration files per - https://github.com/GameServerManagers/LinuxGSM/wiki/LinuxGSM-Config-Files. The documentation talks about having an instance config, for me there already was an "/opt/lgsm/config-lgsm/arkserver/arkserver.cfg" instance config which is what I edited.

With LGSM setup and configuration set we can install the Dedicated Server, run:
```
/opt/arkserver install
```
This will install SteamCMD and the Dedicated server. Running \`/opt/arkserver\' without any flags will show you what options are available. Start the server with
```
/opt/arkserver st
```
