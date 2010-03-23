#!/usr/bin/rrdcgi
<HTML>
<BODY>
<RRD::GOODFOR 30>
<RRD::GRAPH ../temp0.png
   --lazy --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --title="Temperatures"
   DEF:cel=/home/sensortemp.rrd:temp:LAST
   LINE2:cel#00a000:"D. Celsius">
</BODY>
</HTML>
