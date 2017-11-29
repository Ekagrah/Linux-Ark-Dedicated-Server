# Linux ARK Survival Evolved Dedicated Server

When we started this crazy idea to run our own dedicated server we knew very little. We manually managed copying of mods, this was running on a Windows machine, and my friend wasn't fond of administering the server. We learned a lot and as a system administrator I was a better fit. So when Ragnarok was released I set up my own server on Lubuntu 16.04, setup a dummy steam account so I could run easily access server updates. We had heard about SteamCMD but just didn't want to deal with trying to figure that out. I decided it was more fun to write my own scripts and figured my work may be helpful for someone else.

## Getting Started

First, after actually purchasing the game, decide what mods you want - this can be difficult as there is a lot of content out there. Here is a link (http://steamcommunity.com/sharedfiles/filedetails/?id=847707731) to what I use and you will see the list in my code.

Next, set up a virtual machine. I wont detail that here but see this guide https://linus.nci.nih.gov/bdge/installUbuntu.html (provided by National Cancer Institute). I use lvm with about 16GB provided to /opt.

Now we will install LinuxGSM:
1) Ensure write premissions to /opt 
2) Follow these instructions to get LinuxGSM - http://gameservermanagers.com/lgsm/arkserver/#gettingstarted
3) You will now have /opt/linuxgsm.sh, /opt/lgsm, and /opt/arkserver
4) Adjust configuration files per - https://github.com/GameServerManagers/LinuxGSM/wiki/LinuxGSM-Config-Files. The documentation talks about having an instance config, for me there already was an "/opt/lgsm/config-lgsm/arkserver/arkserver.cfg" instance config which is what I edited.

With LGSM setup and configuration set we can install the Dedicated Server, run:
```
/opt/arkserver install
```
This will install SteamCMD and the Dedicated server. Running \`/opt/arkserver\' without any flags will show you what options are available. Start the server with
```
/opt/arkserver st
```
After a few minutes your server should be available. Some may not see it on the ARK in-game server list so you if you message them via Steam with a link like \`steam://connect/\<external-ip\>:27015\' people should be able to connect - this link also works if entered in IE/Edge but not Chrome.... Note: I have not found a better work around for people not finding my server via in-game 'Join Ark' option. 

On your gaming rig you will add the scripts as described below and will need the putty tools plink.exe and pscp.exe (puttygen.exe is good to use for generating ssh keys)

On the server add the Dunto's python rcon client to /opt. So long as it is there and executable it will get referenced. If you want it somewhere else edit the ark_restart_v3.sh to point to the new location. Still working on logic to handle errors gracefully should the rcon client not be able to connect, not executable, etc.


## Using Scripts

MAKE SURE TO EDIT .SH AND .PS1 SCRIPT VARIABLES FOR YOUR INSTALL

My idea of managing the mods took several iterations and trial and error. Eventually I arrived at my posted scripts which should take minimal customization to work for anyone (be gentle its my first time writing code for a public audience).

The idea is that the powershell script, arkuxserv-v4.ps1, will live on your gaming rig. I typically run the ark-mod-probev2.ps1 first to see if there is anything to do, mainly habit from this process of experimentation. The arkserv_restart_v3.sh I have kept in my user home directory on the lubuntu server since I chose to use that user instead of another per the set up instructions.

* When Steam does a mod up date launch ARK and it will show progress of mod installation in the bottom right corner. Once that is completed launch the powershell script and everything should work to copy the designated mods that have updated and to restart the server.

## Troubleshooting

* Use \`netstat -puln 2\>/dev/null | grep ShooterGame\' to check status of server. When you have two lines with one showing ':7778' then the server should be accessible.
* Use \`ps -ef | grep -i ShooterGame\' to see that there are two processess, one of which is a tmux session.
* Report errors and I'll be happy to address them. I tried to anticipate as many scenarios as possible but like I said, this is a first for me.
* I no longer use Steam GUI for server updates, but if someone takes that route here is a link to fix the Steam app not launching in Ubuntu https://askubuntu.com/questions/771032/steam-not-opening-in-ubuntu-16-04-lts#771507.

## To-Do

* Setup and document Discord notifications

## Authors

Ekagrah - ekagrah.gamer@gmail.com, ekagrah@icloud.com

## License



## Acknowledgments

* Would be nowhere without alien.system's guide, highly recommend reading to really understand your dedicated server - http://steamcommunity.com/sharedfiles/filedetails/?id=656433788
* Dunto's python rcon client - see https://gist.github.com/Dunto/e310c00e84b98e0e90dd (which I have forked)
* Linux Game Server Manager - their method was what I was looking for to address the process being killed after the plink session closed (this is why I stopped using the Steam UI to do updates). They have done some solid work!
