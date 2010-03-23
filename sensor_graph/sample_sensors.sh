#!/bin/sh
sleep 2
echo -e "listen sensor\n" | usocket /var/run/powersensordaemon/cmd.sock -n | ./sample_sensor.lua &>/dev/null &
PID1=$!
echo -e "listen movement\n" | usocket /var/run/powersensordaemon/cmd.sock -n >> /tmp/movement.tmp &
PID2=$!
trap "kill $PID1 $PID2" 0 INT QUIT
while sleep 30; do
  L=$(wc -l /tmp/movement.tmp | sed 's/[^0-9]*//g')
  echo -n > /tmp/movement.tmp
  rrdtool update /home/sensormovement.rrd -t movement N:$L
done
