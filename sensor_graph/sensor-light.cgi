#!/usr/bin/rrdcgi
<HTML>
<BODY>
<RRD::GOODFOR 30>
<RRD::GRAPH ../light0.png
   --lazy --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --title="Room Illumination"
   DEF:cel=/home/sensorlight.rrd:light:LAST
   LINE2:cel#00a000:"0 dark to 1023 bright">
</BODY>
</HTML>
