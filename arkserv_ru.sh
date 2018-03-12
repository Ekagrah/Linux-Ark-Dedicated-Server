#!/bin/bash
# this reports on ark server resource usage
# this uses sar from the sysstat ubuntu package

CUTOP=$(top -b -n 1 | awk '/ShooterG/')
ARKCPU=$( echo ${CUTOP} | awk '{print $9}')
ARKMEM=$( echo ${CUTOP} | awk '{print $10}')
CPU_V=$( sar -P ALL 10 3 | awk '/Average.*all/{print $8}' )
TMP_MAIL="$(mktemp)"

if [[ ! -n $CUTOP ]]; then exit 1 ; fi

if [[ $( echo ${ARKCPU%.*}) -gt 95 ]] ; then
logger "Ark server process high CPU usage, greater than 95%"
elif [[ $( echo ${ARKCPU%.*}) -gt 95 && $( echo ${CPU_V%.*}) -lt 20 ]]; then                                                                                                                                           
logger "Ark server high CPU usage, less than 20% idle"
#sar -f /var/log/sysstat/sa25 -P ALL -s 18:00:00 -e 23:59:00 
#sar -f /var/log/sysstat/sa25 -r -s 18:00:00 -e 23:59:00 
sar -P ALL 10 3 | awk 'BEGIN {}
/CPU/{print}
/all/{print}
' > ${TMP_MAIL}
uptime | cut -d " " -f 12-16 >> ${TMP_MAIL}
mail -s "Ark Server high CPU usage, greater than 95%" servmana < ${TMP_MAIL}
elif [[ $( echo ${ARKMEM%.*}) -gt 90 ]]; then
logger "Ark Server high Memory usage, greater than 90"
mail -s "Ark Server high Memory usage, greater than 90%" servmana < /dev/null  2>/dev/null
elif [[ $( echo ${ARKMEM%.*}) -ge 90 ]]; then
logger "Ark Server Memory usage 90% or more"
mail -s "Ark Server Memory usage 90% or more" servmana < ${CUTOP}  2>/dev/null
else
logger "Ark Server looking nominal"
fi

rm "${TMP_MAIL}"
exit 0
