#!/bin/bash

DAILY="$(mktemp)"
curr_date="$( \date +%b%d_%H-%M )"
map="$( ps -efH --sort=+ppid | grep "[S]hooterGameServer" | grep -v tmux | awk '{print $9}' | awk -F '?' '{print $1}' )"

echo -e "\nStats as of $(\date '+%F-%R') running map: ${map}" >> ${DAILY}
echo -e "\n" >> ${DAILY}
python3 /opt/bin/rcon_client_v2.py listplayers >> ${DAILY}

\iostat -N -m >> ${DAILY}
echo -e "\n" >> ${DAILY}
\df -h --exclude-type=tmpfs --total >> ${DAILY}
echo -e "\n" >> ${DAILY}
\du -h /opt --max-depth=1 >> ${DAILY}
echo -e "\n" >> ${DAILY}
#top -b -n 1 | awk -f /home/derekk/.awktop.awk >> ${DAILY}
# execute top then press E (shift+e)
# to change unit totals are displayed 
# in, press e to change for tasks. When set as desired press W
# (shift+w) to save in ~/.toprc
top -b -n 1 | awk 'BEGIN {}
FNR <= 7
/ShooterG/{print}
' >> ${DAILY}
#\ps -efH --sort=+ppid | awk '$8 !~ /^\[/||/volume-manager$/' | \grep -v "lightdm" >> ${DAILY}
mail -s "ArkServPriv report as of $(\date '+%F-%R')" servmana < "${DAILY}"

exit 0
