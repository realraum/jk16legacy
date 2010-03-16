rrdtool create sensordata.rrd --step 30 DS:temp:GAUGE:1800:-20:60 DS:light:GAUGE:300:0:1023 DS:movement:ABSOLUTE:604800:0:U  RRA:LAST:0.5:2:2048
rrdtool update sensordata.rrd -t temp N:26.0   
rrdtool update sensordata.rrd -t light N:200 
rrdtool update sensordata.rrd -t movement N:0 
