#!/bin/bash
## This is intended to be called by the
## powershell script following copy new mods to server
##
## I've typically used a sym link to $HOME/restart_server 
## with script located in $arkdir/binaries/

USAGE () {
echo -e "\nUsage: $0 [-s]
\tUse -s flag to make a copy of server config files."
}

if [[ $( pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
	echo 'Server does not seem to be running...please verify.'
	exit 4
fi

if [[ $# -gt 1 ]]; then
	USAGE
	exit 1
fi
case $1 in
	'-s') dosave=true ;;
	*) dosave=false ; echo 'No flags provided, continuing on...' ;;
esac

map='TheIsland'
arkdir='/opt/serverfiles'
savedir="/home/$USER/Documents/arksavedata"
curr_date="$( \date +%b%d_%H-%M )"

if [[ "${dosave}" == 'true' ]]; then
	if [[ ! -d "${savedir}" ]] ; then
		mkdir -p "${savedir}"
	fi
	echo "Copying files..."
	cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/Game.ini "${savedir}"/Game_${curr_date}.ini
	cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini "${savedir}"/GameUserSettings_${curr_date}.ini
	cp "${arkdir}"/ShooterGame/Saved/SavedArks/"$map".ark "${savedir}"/"$map"_${curr_date}.ark
	savefolder="$( echo "${savedir%/}" | awk -F "/" '{print $NF}' )"
	savedir_parent="$( echo "${savedir%/"${savefolder}"}" )"
	cd "${savedir_parent}"
	echo "Making tarball..."
	tar -czf ark-"${curr_date}".tar ./"${savefolder}"
fi
# Functions, some referencing the
# python based RCON client

checkplayers () {
servbroadcast=true
while [[ $servbroadcast == 'true' ]]; do 
	python /opt/rcon_client.py 'ServerChat Server going down for mod patching in 3 minutes.'
	echo 'Sending broadcast to server'
	servbroadcast=false
done
chktimeout=12
if [[ $( echo $(python /opt/rcon_client.py 'listplayers') ) == 'No Players Connected' ]]; then
	echo 'No Players Connected' 2>1
else
	until [[ $( echo $(python /opt/rcon_client.py 'listplayers') ) == 'No Players Connected' ]]; do
		if [[ $chktimeout -eq 0 ]]; then
			echo -e "\e[93;41mTimeout waiting for users to log off\e[00;39m"
			exit 2
		fi
		python /opt/rcon_client.py 'listplayers'
		sleep 20
		let chktimeout-=1
	done
fi
}

downserver () {
echo -e "\e[35mTaking server down...\e[00;39m"
/opt/arkserver sp
downcounter=24
until [[ $( \pgrep -x ShooterGameServ 2>/dev/null) == '' ]]; do 
if [[ $downcounter -eq 0 ]]; then
##kill process for dedicated server
	for i in $( pgrep -x ShooterGameServ ); do kill -9 $i; done
	break
fi
\netstat -puln 2>/dev/null | \grep ShooterGame
sleep 5
let downcounter-=1
done
echo 'Successfully exited server'
sleep 10
}

upserver () {
echo "Starting Ark Server."
/opt/arkserver st
}

#==============#
checkplayers

##if the last modification/save of map is less than 3 min
if [[ $( (( $(\date +%s) - $(stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/$map.ark) )) ) -lt 180 ]]; then
	echo "World recently saved."
	downserver
	upserver
else
	python /opt/rcon_client.py 'saveworld'
	if [[ $( (( $(\date +%s) - $(stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/$map.ark) )) ) -lt 60 ]]; then
		downserver
		upserver
	fi
fi

ckservup='false'
servstatus='down'
upcounter=12
until [[ "${ckservup}" == 'true' ]]; do
	if [[ $upcounter -eq 0 ]]; then
		echo "Server not sarted yet, manually monitor status..."
		exit 3
	fi
	while read -r line ; do case "$line" in udp*:7778*) export servstatus='up' ;; esac ; done < <(\netstat -puln 2>/dev/null | grep ShooterGame)
	if [[ "${servstatus}" == 'up' ]]; then echo -e "\e[35mServer is ready.\e[00;39m" ; ckservup='true'; break ; fi
	echo "Waiting on server..."
	sleep 20
	let upcounter-=1
done

exit 0