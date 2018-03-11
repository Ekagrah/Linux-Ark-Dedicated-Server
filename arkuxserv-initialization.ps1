# This script is to allow me to copy over desired mod content when initializing a new server. 
# It does not check when the mod content was modified on my machine like my other scripts.
$puttyparent = "G:\INSTALLS\putty"
$local_arkdir = "G:\Active Games\Steam Library\steamapps\common\ARK"
$server_arkdir = "/opt/serverfiles"
$server_ip = "serverip or dns"
$user = "admin"

$modnames = @{"720200839"="Skies of Nazca";"923607638"="More Stack";"754885087"="More Tranq + Narcotic"}

set-location ${local_arkdir}\ShooterGame\Content\Mods\

foreach ($c in $modnames.KEYS.GetEnumerator() ) {
$b = $modnames.$c
Write-Host "$b - Copying items...$c and $c.mod "
Start-Sleep -s 2

&${puttyparent}\PSCP.EXE -i ${puttyparent}\ubuntu.ppk -r ${local_arkdir}\ShooterGame\Content\Mods\$c ${user}@${server_ip}:${server_arkdir}/ShooterGame/Content/Mods

&${puttyparent}\PSCP.EXE -i ${puttyparent}\ubuntu.ppk ${local_arkdir}\ShooterGame\Content\Mods\$c.mod ${user}@${server_ip}:${server_arkdir}/ShooterGame/Content/Mods
}

Read-Host -Prompt "Press Enter to exit"
