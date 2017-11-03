# change powershell execution policy via: 
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy?view=powershell-5.1
# Dependancies:
# 1 - Pscp and plink (both can use key via puttygen)
# 2 - Desired mods subscribed, and Ark launched (places anything downloaded into Mods folder)
# 3 - LinuxGSM (on server) and my restart script
# file naming and user should follow best practice for linux systems
# Change the variables below to match your install/desires


$puttyparent = "G:\INSTALLS\putty"
$local_arkdir = "G:\Active Games\Steam Library\steamapps\common\ARK"
$local_arklog = "C:\Users\admin\Documents\Sync\Documents\ARK\mod-updates-log.txt"
$server_arkdir = "/opt/serverfiles"
$server_ip = "10.0.0.4"
$user = "steam"


$modnames = @{"849985437"="HG Stacking";"719928795"="Platforms Plus";"693416678"="Reusable Plus";"543859212"="Auto Torch";"741338580"="Pet Res";"821530042"="Upgrade Station";"725398419"="Snappy Saddles";"736236773"="Backpack";"793692615"="Antinode";"889745138"="Awesome Teleporter";"731604991"="Structures Plus";"764755314"="CKF Architecture";"655261420"="Homing Pigeon";"812655342"="Automated Ark";"708807240"="Pillars Plus";"506506101"="Better Beacons";"1129514366"="Randi's Halloween Mod";"908221844"="AccessibleTek";"947524058"="Kibble Station";"835113702"="Military Weapons";"1098600119"="GHG Tranq Lite";"859198322"="Craftable Element";"1102050924"="Clear Scuba";"707081776"="Extended Raft";"538827119"="Omnicular"}

set-location ${local_arkdir}\ShooterGame\Content\Mods\

$a = gci -ErrorAction SilentlyContinue -ErrorVariable danger | where {(New-TimeSpan $_.Lastwritetime).days -lt 1 }
if ($danger) {
Write-Host "A few files in your array don't exist."
Get-Date | Out-File -Filepath ${local_arklog} -Append
$danger | Out-File -Filepath ${local_arklog} -Append
} else {
$danger > $Null
}

$global:count = 0
$updates = @{}

foreach ($c in $modnames.KEYS.GetEnumerator() ) {
	foreach ($d in $a) {
		if ($d -notcontains ".mod" -and $c -eq $d) {

$count++

$b = $modnames.$c
$updates.Add("$c", "$b")
Write-Host "$b has updated. Copying items...$c and $c.mod "
Start-Sleep -s 2

# This will need to be adjusted to your local install location and server ip/dns
# See variables
&${puttyparent}\PSCP.EXE -i ${puttyparent}\ubuntu.ppk -r ${local_arkdir}\ShooterGame\Content\Mods\$c ${user}@${server_ip}:${server_arkdir}/ShooterGame/Content/Mods

&${puttyparent}\PSCP.EXE -i ${puttyparent}\ubuntu.ppk ${local_arkdir}\ShooterGame\Content\Mods\$c.mod ${user}@${server_ip}:${server_arkdir}/ShooterGame/Content/Mods
}
}
}

# If updates were done then restart server
if ($count -eq 1) {
Write-Host "One mod updated, will be restarting server."
# Could chose to load a Putty saved session; use -load "<session-name>"
#${puttyparent}\PUTTY.EXE -ssh -t -load "ArkServPriv"
&${puttyparent}\PLINK.EXE -ssh -i ${puttyparent}\ubuntu.ppk ${user}@${server_ip} /home/${user}/arkserv_restart_v3.sh
} elseif ($count -gt 1) {
Write-Host "$count mods updated, will be restarting server."
&${puttyparent}\PLINK.EXE ${puttyparent}\PLINK.EXE -ssh -i ${puttyparent}\ubuntu.ppk ${user}@${server_ip} /home/${user}/arkserv_restart_v3.sh
} else {
Write-Host "No mods updated, NOT restarting server."
}

# Log updates to local file
if ($updates) {
Get-Date | Out-File -Filepath ${local_arklog} -Append
$updates | Out-File -Filepath ${local_arklog} -Append
} else {
[void] ($updates)
}

Read-Host -Prompt "Press Enter to exit"
