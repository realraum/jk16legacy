#!/usr/bin/rrdcgi
<HTML>
<BODY>
<RRD::GOODFOR 30>
<RRD::GRAPH ../temp0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --color="BACK#d0d0af" --color="CANVAS#ffffff" 
   --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
   --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
   --color="ARROW#761407" --color="GRID#d0d0af"
   --title="Room Temperature" --lazy
   --start=now-36h --end=now --width=490
   --slope-mode
   DEF:cel=/home/sensortemp.rrd:temp:LAST VDEF:lv=cel,LAST
   LINE2:cel#e21407:"°C (±0.5)," GPRINT:lv:"Current Temperature\: %1.2lf °C">
</BODY>
</HTML>
