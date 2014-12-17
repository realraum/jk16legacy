#!/usr/bin/rrdcgi
<HTML>
<BODY>
<RRD::GOODFOR 30>
<RRD::GRAPH ../movement.png
  --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
  --color="BACK#d0d0af" --color="CANVAS#ffffff" 
  --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
  --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
  --color="ARROW#761407" --color="GRID#d0d0af"
  --title="Movement Sensor" --lazy
  --start=now-36h --end=now --width=490
  DEF:cel=/home/sensormovement.rrd:movement:LAST
  LINE2:cel#1407e2:"Movements / Minute">

</BODY>
</HTML>

