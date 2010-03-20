#!/bin/sh
echo -e "listen sensor\n" | usocket /var/run/powersensordaemon/cmd.sock -n | ./sample_sensor.lua &>/dev/null &
echo -e "listen movement\n" | usocket /var/run/powersensordaemon/cmd.sock -n > /tmp/movement.tmp &
while sleep 30; do
  L=$(wc -l /tmp/movement.tmp | cut -d' ' -f1)
  echo -n > /tmp/movement.tmp
  rrdtool update /home/sensormovement.rrd -t movement N:$L
done
