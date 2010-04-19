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
VALIDIDS="werkzeug stereo labor schreibtisch logo idee deckehinten deckevorne"

if [ "$POWER" == "on" -o "$POWER" == "off" ]; then
  for CHECKID in $VALIDIDS; do
    if [ "$CHECKID" == "$ID" ]; then
      echo "power $POWER $ID" | usocket $UNIXSOCK
    fi
   done
fi

DESC_werkzeug="Werkzeug LEDs"
DESC_stereo="Stereo Anlage"
DESC_labor="Labor Licht"
DESC_schreibtisch="Schreibtisch Licht"
DESC_logo="Logo"
DESC_idee="Idee"
DESC_deckehinten="Decke Hinten"
DESC_deckevorne="Decke Vorne"

echo "Content-type: text/html"
echo ""
echo "<html>"
echo "<head>"
echo "<title>Realraum rf433ctl</title>"
echo "</head>"
echo "<body>"
echo "<h1>Realraum rf433ctl</h1>"
echo "<table cellspacing='0'>"
for DISPID in $VALIDIDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
#  echo " <tr><td>$NAME</td><td><a href=\"switch.cgi?id=$DISPID&power=on\"><button value=\"ON\" /></a></td><td><a href=\"switch.cgi?id=$DISPID&power=off\"><button value=\"OFF\" /></a></td></tr>"
  echo "<tr><td style=\"font-size:11pt; border-top:1px solid black; border-right:1px solid black; border-left:1px solid black;\">$NAME</td></tr><tr><td align='right' style=\"border-bottom:1px solid black; border-right:1px solid black; border-left:1px solid black;\">"
  echo " <input type='submit' name='power' value='on' />"
  echo " <input type='submit' name='power' value='off' />"
  echo "</td></tr><tr><td style=\"height:1ex;\"></td></tr>"
  echo "</form>"
done
echo "</table>"
echo "</body>"
echo "</html>"
