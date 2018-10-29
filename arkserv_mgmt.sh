#!/bin/bash
## I've typically placed scripts in /opt/bin
## Dedicated Server - https://steamdb.info/app/376030
## Full Game - https://steamdb.info/app/346110

## Auto managing of mods requires:
##TBD

############
## User editable section
PYVERS="python3"
PYRCON='/opt/bin/rcon_client_v2.py'
arkdir='/opt/game'
savedir="${HOME}/Documents/arksavedata"
#map="TheIsland"
#map="ScorchedEarth_P"
#map="Aberration_P"
#map="Extinction_P"
#map="TheCenter"
map="Ragnarok"
#map="skiesofnazca"

nplayers="15"
serv_port="7777"
query_port="27015"
rcon_active="True"
rcon_port="32330"
##optional email or mail alias
EMAIL="servmana"
############

if [[ ! -e ${PYRCON} ]] ; then echo "Value for PYRCON for the python rcon tool does not seem to exist" ; exit 2 ; fi
if [[ ! -e ${map} ]] ; then echo "Need a value for \$map" ; exit 2 ; fi
serv_port_a="$(( ${serv_port} + 1 ))"
script_dir="$( cd "$( dirname "$(readlink -f "$0")" )" && pwd )"

USAGE () {
echo -e "\nUsage: $0 <option>
\tFor the time being I am only accepting one per run:
\tstart\tStarts the game server
\tstop\tStops game server
\trestart\tRestarts game server
\tmonitor\tReports back if server is running and accessible
\tupdate\tChecks if update to dedicated server has been posted,\n\t\tapplies update, and restarts server
\t-uo\tDoes server update only
\tcleanup\tRemoves unnecessary mod content               
\t-s\tMakes a copy of server config, map save data, and player data files
\t-h\tPrints this usage statement"
}
#\tmodconf\t Add active mods from GameUserSettings to be auto-managed

if [[ $# -gt 1 ]]; then USAGE ; exit 1 ; fi

upserver () {
tmux list-session 2>/dev/null | cut -d \: -f 1 | while read -r line ; do
	if [[ ${line} == 'arkserver' ]]; then
		tmux kill-session -t arkserver
		sleep 10
	fi
done
	if [[ $( \pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]] ; then
		echo "Starting Ark Server."
		tmux new-session -d -x 23 -y 80 -s arkserver /opt/game/ShooterGame/Binaries/Linux/ShooterGameServer "${map}?listen?MaxPlayers=${nplayers}?QueryPort=${query_port}?RCONEnabled=${rcon_active}?RCONPort=${rcon_port}?Port=${serv_port}?AllowRaidDinoFeeding=True?ForceFlyerExplosives=True -USEALLAVAILABLECORES -servergamelog"
		##-usecache -server -NoBattlEye -automanagedmods
		fi
}

fnc_monitor () {
local chkservup='false'
local servstatus='down'
local upcounter=15
if [[ $( \pgrep -x ShooterGameServ 2>/dev/null) = '' ]]; then
	echo -e "Server does not seem to be running..."
	exit 3
else
	echo -e "Server is running"
fi
until [[ "${chkservup}" == 'true' ]]; do
	if [[ $upcounter -eq 0 ]]; then
		echo "Server not ready yet, manually monitor status..."
		exit 3
	fi
	##check that the final port is up
	while read -r line ; do case "$line" in udp*:${serv_port_a}*) export servstatus='up' ;; esac ; done < <(\netstat -puln 2>/dev/null | \grep ShooterGame)
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
if [[ ${do_update} == true ]] ; then 
## this is slow and times out occasionally
	local upd_timeout=5
	while true ;do
	/usr/games/steamcmd +login anonymous +force_install_dir "${arkdir}" +app_update 376030 public validate +quit | tee ${tmpfile}
## so we must verify it completed
	upd_state="$( \tail -5 ${tmpfile} | \awk -F " " '/.*App.*376030.*/{print $1}' )"
	case $upd_state in
		*[Ss]uccess*) echo "${upd_state} Ark server is up-to-date" ; break ;;
		*ERROR*) echo "${upd_state}...restarting update" ; let upd_timeout=-1 ;;
	esac
	if [[ ${upd_timeout} -eq 0 ]] ;  then
		echo -e "Issue completing update. Check permissions\nand disk space for starters." | mail -s "Ark server update failed" servmana
		rm -f "${tmpfile}"
		exit 2
	fi
	done
else
echo "No update"
rm -f "${tmpfile}"
exit 0
fi
}

fnc_chkupdate () {
##fix for conflicting file that can prevent 
##getting the most recent version
if [[ -e ${HOME}/.steam/steam/appcache/appinfo.vdf ]]; then rm ${HOME}/.steam/steam/appcache/appinfo.vdf ; fi
## See if update is available
new_vers="$( /usr/games/steamcmd +login anonymous  +app_info_update 1 +app_info_print 376030 +quit | grep -A5 "branches" | \awk -F '"' '/buildid/{print $4}' )"
curr_vers="$( \awk -F '"' '/buildid/{print $4}' ${arkdir}/steamapps/appmanifest_376030.acf )"
if [[ ${new_vers} -gt ${curr_vers} ]]; then
do_update=true
else
do_update=false
fi
}

fnc_dosave () {
if [[ ! -d ${savedir} ]] ; then
	echo "\$savedir does not seem to exist."
	exit 6
else
	case "${savedir}" in
	/etc*|/bin*|/cgroup*|/lib*|/misc*|/net*|/proc*|/sbin*|/var*|/boot*|/dev*|/lib64*|/selinux*|/sys*|/usr*) echo "Not wise to save to "${savedir}"" ; exit 6 ;; esac
	cd ${savedir}
fi

save_file=''
case $map in
skiesofnazca)
save_file='SkiesofNazca.ark'
;;
*)
save_file="${map}.ark"
;;
esac
if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${save_file}) )) -lt 180 ]]; then
	echo "World recently saved"
else
	${PYVERS} ${PYRCON} saveworld
	sleep 5
	if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${save_file}) )) -lt 180 ]]; then
	echo "Ran saveworld command"
	else
	echo -e "Unable to verify world was recently saved, exiting..."
	exit 2
	fi
fi
local curr_date="$( \date +%b%d_%H-%M )"
local tar_dir="${map%_P}-${curr_date}"
if [[ ! -d "${tar_dir}" ]] ; then \mkdir -p "${tar_dir}" ; fi
echo "Copying files to ${savedir}/${tar_dir}..."
cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/Game.ini "${tar_dir}"/
cp "${arkdir}"/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini "${tar_dir}"/
cp "${arkdir}"/ShooterGame/Saved/SavedArks/"$map".ark "${tar_dir}"/"$map"_${curr_date}.ark
cp "${arkdir}"/ShooterGame/Saved/SavedArks/"$map"_AntiCorruptionBackup.bak "${tar_dir}"/
cp "${arkdir}"/ShooterGame/Saved/SavedArks/*.arkprofile "${tar_dir}"/
cp "${arkdir}"/ShooterGame/Saved/SavedArks/*.arktribe "${tar_dir}"/
echo "Making tarball..."
\tar -czf ark-"${map}"-"${curr_date}".tar ./"${tar_dir}" && rm -rf ./${tar_dir} || echo "Unable to make tarball..."
cd ${script_dir}
}

checkplayers () {
local chktimeout=12
if [[ $( \echo $(${PYVERS} ${PYRCON} listplayers) ) == 'No Players Connected' ]]; then
	echo 'No Players Connected' 2>1
else
	until [[ $( \echo $(${PYVERS} ${PYRCON} listplayers) ) == 'No Players Connected' ]]; do
		if [[ $chktimeout -eq 0 ]]; then
			echo "Timeout waiting for users to log off" | mail -s "Notice: Ark server"
			exit 2
		fi
		${PYVERS} ${PYRCON} listplayers
		sleep 20
		let chktimeout-=1
	done
fi
}

downserver () {
if [[ $( \pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
	echo 'Server does not seem to be running...please verify.' | mail -s "Notice: Ark server" ${EMAIL}
	exit 4
fi
#echo "Taking server down..."
tmux send-keys C-c -t arkserver
local downcounter=24
until [[ $( \pgrep -x ShooterGameServ 2>/dev/null) == '' ]]; do 
if [[ $downcounter -eq 0 ]]; then
	##clear any existing tmux session
	tmux kill-session -t arkserver
	##forcefully kill process for dedicated server
	echo -e "Forcefully killing server process"
	for i in $( \pgrep -x ShooterGameServ 2>/dev/null); do kill -9 $i; done
	sleep 5
	break
fi
## wait 2 minutes for graceful shutdown
echo "Waiting on server to go down gracefully"
sleep 5
let downcounter-=1
done
if [[ $( \pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
echo 'Successfully exited server' > /dev/null
else
echo 'Server does not seem to have stopped' | mail -s "Notice: Ark server"
exit 5
fi
}

fnc_restart () {
if [[ $( \pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
	echo "Server not running, no restart needed"
	exit 6
else
echo 'Sending broadcast to server'
${PYVERS} ${PYRCON} broadcast Server going down for maintinence in 3 minutes.
fi

checkplayers

##Check if the last save of map is less than 3 min
save_file=''
case $map in
skiesofnazca)
save_file='SkiesofNazca.ark'
;;
*)
save_file="${map}.ark"
;;
esac
if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${save_file}) )) -lt 180 ]]; then
	echo "World recently saved."
	downserver
	upserver
else
	${PYVERS} ${PYRCON} saveworld
	echo -e "Manually ran saveworld command..."
	sleep 5
	if [[ $(( $(\date +%s) - $(\stat -c %Y "${arkdir}"/ShooterGame/Saved/SavedArks/${save_file}) )) -lt 180 ]]; then
		downserver
		upserver
	else
		echo -e "Unable to verify world was recently saved, exiting..."
		exit 2
	fi
fi
}

fnc_cleanup () {
if [[ -d ${arkdir} ]]; then
cd "${arkdir}"/ShooterGame/Content/Mods/
else
echo "Directory appears invalid, exiting for safety..."
exit 7
fi
local active_mods="$(\sed -n 's/ActiveMods=//p' ${arkdir}/ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini | \awk -v FS="," '{OFS=" "; $1=$1; print $0}')"
declare -a mod_list
## find existing mod files
while IFS=  read -r -d $'\0'; do mod_list+=("$REPLY") ; done < <(\find ./ -name '*.mod' -print0 | \sed -e 's|./111111111.mod||' -e 's|./||g' -e 's|.mod||g')
local arr_id=0
for m in $(\echo ${mod_list[@]} ) ; do
## if existing file has match under ActiveMods
## then remove it from array
	if [[ $(\echo ${active_mods} | \grep -o ${m}) == "${m}" ]]; then
		unset mod_list[${arr_id}]
	else
		echo "Marking ${m} for removal" 
	fi
	let arr_id++
done
unset arr_id
if [[ ${#mod_list[@]} -gt 0 ]] ; then
for d in $(\echo ${mod_list[@]}) ; do
	echo "Deleting data for mod: ${d}"
	rm -rf ./${d}
	rm -f ./${d}.mod
done
else
echo "No files to remove/modify"
fi
cd /opt
unset active_mods
unset mod_list
}

#==============#
if [[ $# -gt 1 ]]; then
	USAGE
	exit 1
fi

case $1 in
	start) upserver ; fnc_monitor ;;
	stop) checkplayers ; downserver ;;
	restart) fnc_restart ; fnc_monitor ;;
	monitor) fnc_monitor ;;
	update) fnc_chkupdate ; fnc_update ; fnc_restart ; fnc_monitor ;;
	-uo) fnc_chkupdate ; fnc_update	;;
	cleanup) fnc_cleanup ;;
	-s) fnc_dosave ;;
	-h|help) USAGE ;;
	*) USAGE ; exit 1 ;;
esac

exit 0