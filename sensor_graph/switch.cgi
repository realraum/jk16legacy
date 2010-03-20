#!/bin/sh

for QUERY in `echo $QUERY_STRING | tr '&' ' '`; do
  for VALUE in `echo $QUERY | tr '=' ' '`; do
    if [ "$VALUE" == "id" ]; then
      ID='?'
    elif [ "$ID" == "?" ]; then
      ID=$VALUE
    elif [ "$VALUE" == "power" ]; then
      POWER='?'
    elif [ "$POWER" == "?" ]; then
      POWER=$VALUE
    fi
    i=$i+1
  done
done

UNIXSOCK=/var/run/powersensordaemon/cmd.sock
VALIDIDS="werkzeug stereo labor schreibtisch logo idee"

if [ "$POWER" == "on" -o "$POWER" == "off" ]; then
  for CHECKID in $VALIDIDS; do
    if [ "$CHECKID" == "$ID" ]; then
      echo "power $POWER $ID" | usocket $UNIXSOCK
    fi
   done
fi

DESC_werkzeug="Beleuchtung Werkzeug"
DESC_stereo="Stereo Anlage"
DESC_labor="Labor Licht"
DESC_schreibtisch="Schreibtisch Licht"
DESC_logo="Logo"
DESC_idee="Idee"

echo "Content-type: text/html"
echo ""
echo "<html>"
echo "<head>"
echo "<title>Realraum rf433ctl</title>"
echo "</head>"
echo "<body>"
echo "<h1>Realraum rf433ctl</h1>"
echo "<table>"
echo " <tr><th>Device</th><th>ON</th><th>OFF</th></tr>"
for DISPID in $VALIDIDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  echo " <tr><td>$NAME</td><td><a href=\"switch.cgi?id=$DISPID&power=on\">ON</a></td><td><a href=\"switch.cgi?id=$DISPID&power=off\">OFF</a></td></tr>"
done
echo "</table>"
echo "</body>"
echo "</html>"
