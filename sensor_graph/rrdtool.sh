rrdtool create sensorlight.rrd --step 30 DS:light:GAUGE:300:0:1023 RRA:LAST:0.5:2:2048
rrdtool create sensortemp.rrd --step 30 DS:temp:GAUGE:1800:-20:60 RRA:LAST:0.5:2:2048
rrdtool create sensormovement.rrd --step 30 DS:movement:ABSOLUTE:604800:0:U  RRA:LAST:0.5:2:2048
rrdtool update sensorlight.rrd -t temp N:26.0   
rrdtool update sensortemp.rrd -t light N:200 
rrdtool update sensormovement.rrd -t movement N:0 
