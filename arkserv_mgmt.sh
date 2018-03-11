#!/bin/bash
## I've typically placed scripts in /opt/bin
## https://steamdb.info/app/376030

curr_date="$( \date +%b%d_%H-%M )"
############
# User editable section
PYVERS="python3"
PYRCON='/opt/bin/rcon_client_v2.py'
arkdir='/opt/game'
savedir="/home/$USER/arksavedata/"${curr_date}""
map="Aberration_P"
nplayers="10"
serv_port="7777"
query_port="27015"
rcon_active="True"
rcon_port="27020"
#optional email or mail alias
EMAIL="servmana"
############

if [[ ! -e ${PYRCON} ]] ; then echo "Value for PYRCON for the python rcon tool does not seem to exist" ; exit 2 ; fi
serv_port_a="$(( ${serv_port} + 1 ))"

USAGE () {
echo -e "\nUsage: $0 <option>
\tFor the time being I am only accepting one per run:
\tstart\tStarts the game server
\tstop\tStops game server
\tmonitor\tReports back if server is running and accessible
\tupdate\tChecks for update to dedicated server
\t-s\tMakes a copy of server config files.
\t-h\tPrints this usage statement"
}

upserver () {
alt_query_port=$(( ${query_port} + 1 ))
tmux list-session 2>/dev/null | cut -d \: -f 1 | while read -r line ; do
	if [[ ${line} == 'arkserver' ]]; then
		tmux kill-session -t arkserver
		sleep 10
	fi
done
	if [[ $( pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]] ; then
		echo "Starting Ark Server."
		tmux new-session -d -x 23 -y 80 -s arkserver /opt/game/ShooterGame/Binaries/Linux/ShooterGameServer "${map}?listen?MaxPlayers=${nplayers}?QueryPort=${query_port}?RCONEnabled=${rcon_active}?RCONPort=${rcon_port}?Port=${serv_port}?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -USEALLAVAILABLECORES -usecache -servergamelog"
		fi
}

fnc_monitor () {
local chkservup='false'
local servstatus='down'
local upcounter=12
local MAIL_TMP="$(mktemp)"
if [[ -n $( pgrep -x ShooterGameServ 2>/dev/null) ]]; then
	echo -e "Server is running"
fi
until [[ "${chkservup}" == 'true' ]]; do
	if [[ $upcounter -eq 0 ]]; then
		echo "Server not ready yet, manually monitor status..."
		if [[ -x usr/bin/mail ]] ; then
		mail -s "ARK Server not accessible after 4 minutes" ${EMAIL} < ${MAIL_TMP}
		fi
		exit 3
	fi
	#check that the final port is up
	while read -r line ; do case "$line" in udp*:${serv_port_a}*) export servstatus='up' ;; esac ; done < <(\netstat -puln 2>/dev/null | grep ShooterGame)
	if [[ "${servstatus}" == 'up' ]]; then 
	echo "Server is ready"
	chkservup='true'; break ; fi
	echo "Waiting on server..."
	sleep 20
	let upcounter-=1
done
}

fnc_update () {
local tmpfile="$(mktemp)"
#update dedicated server
if [[ ${do_update} == true ]] ; then 
# this is slow and times out occasionally
	local upd_timeout=5
	while true ;do
	/usr/games/steamcmd +force_install_dir /opt/game/ +login anonymous +app_update 376030 public validate +quit | tee ${tmpfile}
# so we must verify it completed
	upd_state="$( tail -5 ${tmpfile} | awk -F " " '/.*App.*376030.*/{print $1}' )"
	case $upd_state in
		*[Ss]uccess*) echo "${upd_state} Ark server is up-to-date" ; break ;;
		*[Ee]rror*) echo "${upd_state}...restarting update" ; let upd_timeout=-1 ;;
	esac
	if [[ ${upd_timeout} -eq 0 ]] ;  then
		echo -e "Issue completing update. Check permissions\nand disk space for starters." | mail -s "Ark server update failed" servmana
		exit 2
	fi
	done
else
echo "No update" 
exit 0
fi
}

fnc_chkupdate () {
new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | grep -A5 "branches" | awk -F '"' '/buildid/{print $4}' )"
curr_vers="$( awk -F '"' '/buildid/{print $4}' /opt/game/steamapps/appmanifest_376030.acf )"
if [[ ${new_vers} -gt ${curr_vers} ]]; then
do_update=true
else
do_update=false
fi
}

fnc_dosave () {
	if [[ ! -d "${savedir}" ]] ; then
		mkdir -p "${savedir}"
	fi
	echo "Copying files..."
	cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/Game.ini "${savedir}"/
	cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini "${savedir}"/
	cp "${arkdir}"/ShooterGame/Saved/SavedArks/"$map".ark "${savedir}"/"$map"_${curr_date}.ark
	savefolder="$( echo "${savedir%/}" | awk -F "/" '{print $NF}' )"
	savedir_parent="$( echo "${savedir%/${savefolder}}" )"
	cd "${savedir_parent}"
	echo "Making tarball..."
	\tar -czf ark-"${curr_date}".tar ./"${savefolder}"
	rm -rf ${savedir}
}

checkplayers () {
local chktimeout=12
if [[ $( echo $(${PYVERS} ${PYRCON} listplayers) ) == 'No Players Connected' ]]; then
	echo 'No Players Connected' 2>1
else
	until [[ $( echo $(${PYVERS} ${PYRCON} listplayers) ) == 'No Players Connected' ]]; do
		if [[ $chktimeout -eq 0 ]]; then
			echo "Timeout waiting for users to log off"
			exit 2
		fi
		${PYVERS} ${PYRCON} listplayers
		sleep 20
		let chktimeout-=1
	done
fi
}

downserver () {
if [[ $( pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
	echo 'Server does not seem to be running...please verify.'
	exit 4
fi
echo "Taking server down..."
tmux send-keys C-c -t arkserver
local downcounter=24
until [[ $( \pgrep -x ShooterGameServ 2>/dev/null) == '' ]]; do 
if [[ $downcounter -eq 0 ]]; then
	#kill tmux session for server
	tmux kill-session -t arkserver
	sleep 20
	##forcefully kill process for dedicated server
	tmux list-session | cut -d \: -f 1 | while read -r line ; do
	if [[ ${line} == 'arkserver' ]]; then
	for i in $( \pgrep -x ShooterGameServ 2>/dev/null); do kill -9 $i; done
	fi ; done
	break
fi
\netstat -puln 2>/dev/null | \grep ShooterGame
sleep 5
let downcounter-=1
done
echo 'Successfully exited server'
}

fnc_restart () {
echo 'Sending broadcast to server'
${PYVERS} ${PYRCON} broadcast Server going down for maintinence in 3 minutes.

checkplayers

##if the last modification/save of map is less than 3 min
if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${map}.ark) )) -lt 180 ]]; then
	echo "World recently saved."
	downserver
	upserver
else
	${PYVERS} ${PYRCON} saveworld
	echo -e "Manually ran saveworld command..."
	if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${map}.ark) )) -lt 180 ]]; then
		downserver
		upserver
	else
		echo -e "Unable to verify world was recently saved, exiting..."
		exit 2
	fi
fi
}

#==============#
if [[ $# -gt 1 ]]; then
	USAGE
	exit 1
fi

case $1 in
	-s) fnc_dosave ;;
	-h) USAGE ;;
	start) upserver ; fnc_monitor ;;
	stop) downserver ;;
	monitor) fnc_monitor ;;
	update) fnc_chkupdate ; fnc_update ; fnc_restart ; fnc_monitor ;;
	restart) fnc_restart ; fnc_monitor ;;
	updmod) fnc_updmod ; fnc_restart ; fnc_monitor ;;
	*) USAGE ; exit 1 ;;
esac

exit 0
