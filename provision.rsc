:local mac [/system identity get mac-address];
:set mac [:pick $mac 0 2].[:pick $mac 2 4].[:pick $mac 4 6].[:pick $mac 6 8].[:pick $mac 8 10].[:pick $mac 10 12];
/tool fetch url=("http://[server-ip]:5000/config/" . $mac . ".rsc") mode=http;
/import file-name=($mac . ".rsc");
