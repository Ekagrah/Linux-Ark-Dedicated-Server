
$modnames = @{"849985437"="HG Stacking";"719928795"="Platforms Plus";"693416678"="Reusable Plus";"741338580"="Pet Res";"821530042"="Upgrade Station";"725398419"="Snappy Saddles";"736236773"="Backpack";"793692615"="Antinode";"889745138"="Awesome Teleporter";"731604991"="Structures Plus";"764755314"="CKF Architecture";"655261420"="Homing Pigeon";"812655342"="Automated Ark";"708807240"="Pillars Plus";"506506101"="Better Beacons";"1129514366"="Randi's Halloween Mod";"908221844"="AccessibleTek";"947524058"="Kibble Station";"835113702"="Military Weapons";"1098600119"="GHG Tranq Lite";"859198322"="Craftable Element";"1102050924"="Clear Scuba";"707081776"="Extended Raft";"538827119"="Omnicular"}

# This is the ARK install location for your local machine = gaming rig
set-location 'G:\Active Games\Steam Library\steamapps\common\ARK\ShooterGame\Content\Mods\'

$localfiles = gci -ErrorAction SilentlyContinue | where {(New-TimeSpan $_.Lastwritetime).days -lt 1 }
$global:count = 0
$updates = @{}

foreach ($c in $modnames.KEYS.GetEnumerator() ) {
	foreach ($a in $localfiles) {
		if ($a -notcontains ".mod" -and $c -eq $a) {

$count++

$b = $modnames.$c
Write-Host "$b has updated."
$updates.Add("$c", "$b")
}
}
}

if ($count -eq 1) {"One mod updated, will be restarting server."}
elseif ($count -gt 1) {"$count mods updated, will be restarting server."}
else {"No mods updated, NOT restarting server."}

Read-Host -Prompt "Press Enter to exit"
