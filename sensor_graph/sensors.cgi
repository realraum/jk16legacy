#!/usr/bin/rrdcgi
<HTML>
<HEAD><TITLE>RealRaum Sensor Data</TITLE></HEAD>
<BODY>
<H1>RealRaum Sensor Data</H1>
<RRD::GOODFOR 30>
<P>
<RRD::GRAPH ../light0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --lazy --title="Room Illumination"
   DEF:cel=/home/sensordata.rrd:light:LAST
   LINE2:cel#00a000:"0 dark to 1024 bright">
</P>
<P>
<RRD::GRAPH ../temp0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --lazy --title="Temperatures"
   DEF:cel=/home/sensordata.rrd:temp:LAST
   LINE2:cel#00a000:"D. Celsius">
</P>
<RRD::GRAPH ../movement.png
  --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
  --lazy --title="Graph of Movement Sensor"
  DEF:cel=/home/sensordata.rrd:movement:LAST
  LINE2:cel#00a000:"1 Movement, 0 No Movement">
</P>                                 
</BODY>
</HTML>
