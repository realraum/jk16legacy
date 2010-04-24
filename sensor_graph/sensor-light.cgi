#!/usr/bin/rrdcgi
<HTML>
<BODY>
<RRD::GOODFOR 30>
<RRD::GRAPH ../light0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --color="BACK#d0d0af" --color="CANVAS#ffffff" 
   --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
   --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
   --color="ARROW#761407" --color="GRID#d0d0af"
   --title="Room Illumination" --lazy
   --start=now-36h --end=now --width=490
   --slope-mode --alt-autoscale-max
   DEF:cel=/home/sensorlight.rrd:light:LAST VDEF:lv=cel,LAST
   LINE2:cel#04d532:"0 complete darkness via 450 dark to 1023 quite bright," GPRINT:lv:"Current Value\: %1.0lf">
</BODY>
</HTML>
