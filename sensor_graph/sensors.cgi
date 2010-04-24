#!/usr/bin/rrdcgi
<HTML>
<HEAD><TITLE>RealRaum Sensor Data</TITLE></HEAD>
<BODY>
<H1>RealRaum Sensor Data</H1>
<RRD::GOODFOR 30>
<P>
<RRD::GRAPH ../light0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --color="BACK#d0d0af" --color="CANVAS#ffffff" 
   --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
   --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
   --color="ARROW#761407" --color="GRID#d0d0af"
   --title="Room Illumination"
   --start=now-36h --end=now --width=490
   --slope-mode
   DEF:cel=/home/sensorlight.rrd:light:LAST VDEF:lv=cel,LAST
   LINE2:cel#04d532:"0 dark to 1023 bright," GPRINT:lv:"Current Value\: %1.0lf">
</P>
Current Light Value: <RRD::INCLUDE /home/sensorlight.txt>
<P>
<RRD::GRAPH ../temp0.png
   --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
   --color="BACK#d0d0af" --color="CANVAS#ffffff" 
   --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
   --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
   --color="ARROW#761407" --color="GRID#d0d0af"
   --title="Room Temperature"
   --start=now-36h --end=now --width=490
   --slope-mode
   DEF:cel=/home/sensortemp.rrd:temp:LAST VDEF:lv=cel,LAST
   LINE2:cel#e21407:"°C (±0.5)," GPRINT:lv:"Current Temperature\: %1.2lf °C">
</P>
Current Temperature: <RRD::INCLUDE /home/sensortemp.txt> Â°C
<P>
<RRD::GRAPH ../movement.png
  --imginfo '<IMG SRC="/%s" WIDTH="%lu" HEIGHT="%lu" >'
  --color="BACK#d0d0af" --color="CANVAS#ffffff" 
  --color="SHADEA#dfdfdf" --color="SHADEB#525252" 
  --color="AXIS#761407" --color="FONT#272727" --color="MGRID#b65447"
  --color="ARROW#761407" --color="GRID#d0d0af"
  --title="Movement Sensor"
  --start=now-36h --end=now --width=490
  DEF:cel=/home/sensormovement.rrd:movement:LAST
  LINE2:cel#1407e2:"Movements / Minute">
</P>
Page generated: <RRD::TIME::NOW "%Y-%m-%d %H:%M">
</BODY>
</HTML>
