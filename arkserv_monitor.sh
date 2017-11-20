#!/bin/bash

if [[ $( pgrep -x ShooterGameServ 2>/dev/null) -eq '' ]]; then
	echo 'Server does not seem to be running...'
else
	if [[ $( ps -ef | grep -i ShooterGameServ 2>/dev/null | wc -l) -ge 2 ]]; then
		echo -e "\e[35mServer is running.\e[00;39m"
	fi
fi 

#==============#
ckservup='false'
servstatus='down'
upcounter=12
until [[ "${ckservup}" == 'true' ]]; do
	if [[ $upcounter -eq 0 ]]; then
		echo "Server not ready yet, manually monitor status..."
		exit 3
	fi
	while read -r line ; do case "$line" in udp*:7778*) export servstatus='up' ;; esac ; done < <(\netstat -puln 2>/dev/null | grep ShooterGame)
	if [[ "${servstatus}" == 'up' ]]; then echo -e "\e[35mServer is ready.\e[00;39m" ; ckservup='true'; break ; fi
	echo "Waiting on server..."
	sleep 20
	let upcounter-=1
done

exit 0
