# change powershell execution policy via: 
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy?view=powershell-5.1
# Dependancies:
# 2 - Desired mods subscribed, and Ark launched (places anything downloaded into Mods folder)
# Change the variables below to match your install/desires


$local_arkdir = "G:\Active Games\Steam Library\steamapps\common\ARK"
$local_arklog = "C:\Users\admin\Documents\Sync\Documents\ARK\mod-updates-log.txt"
$server_arkdir = "C:\"
$server_ip = "10.0.0.4"
$user = "steam"


$modnames = @{"923607638"="More Stack";"719928795"="Platforms Plus";"821530042"="Upgrade Station";"725398419"="Snappy Saddles";"736236773"="Backpack";"793692615"="Antinode";"889745138"="Awesome Teleporter";"731604991"="Structures Plus";"764755314"="CKF Architecture";"655261420"="Homing Pigeon";"812655342"="Automated Ark";"708807240"="Pillars Plus";"506506101"="Better Beacons";"1098600119"="GHG Tranq Lite";"859198322"="Craftable Element";"1102050924"="Clear Scuba";"707081776"="Extended Raft";"899250777"="Utilities Plus";"1146018267"="Deinonychus";"856249802"="Tekgrams4u"}

set-location ${local_arkdir}\ShooterGame\Content\Mods\

$localfiles = gci -ErrorAction SilentlyContinue -ErrorVariable danger | where {(New-TimeSpan $_.Lastwritetime).days -lt 1 }
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
	foreach ($a in $localfiles) {
		if ($a -notcontains ".mod" -and $c -eq $a) {

$count++

$b = $modnames.$c
$updates.Add("$c", "$b")
Write-Host "$b has updated. Copying items...$c and $c.mod "
Start-Sleep -s 2

# This will need to be adjusted to your local install location and server ip/dns
# See variables
&robocopy.exe "${local_arkdir}\ShooterGame\Content\Mods\" "\\${server_ip}\\${server_arkdir}\ShooterGame\Content\Mods\" $c /E /ETA /is /LOG+:"${local_arklog}"

&robocopy.exe "${local_arkdir}\ShooterGame\Content\Mods\" "\\${server_ip}\\${server_arkdir}\ShooterGame\Content\Mods\" $c.mod /ETA /is /LOG+:"${local_arklog}"
}
}
}

# If updates were done then restart server
if ($count -eq 1) {
Write-Host "One mod updated, will be restarting server."
# see https://ss64.com/ps/invoke-command.html
# Going to want to have the user account on your local machine too
# see 
Invoke-Command -ComputerName ${server_ip} -ScriptBlock {﻿Stop-Process -Name ShooterGame*} -credential $user
Start-Sleep -s 2
Invoke-Command -ComputerName ${server_ip} -ScriptBlock {﻿Invoke-Item $server_arkdir\ShooterGame\Binaries\Win64\ShooterGameServer.exe} -credential $user
} elseif ($count -gt 1) {
Write-Host "$count mods updated, will be restarting server."
Invoke-Command -ComputerName ${server_ip} -ScriptBlock {﻿Stop-Process -Name ShooterGame*} -credential $user
Start-Sleep -s 2
Invoke-Command -ComputerName ${server_ip} -ScriptBlock {﻿Invoke-Item $server_arkdir\ShooterGame\Binaries\Win64\ShooterGameServer.exe} -credential $user
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