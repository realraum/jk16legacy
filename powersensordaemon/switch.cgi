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
VALIDIDS="werkzeug stereo labor schreibtisch logo idee deckehinten deckevorne decke lichter all"



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
DESC_decke="Deckenlichter"
DESC_lichter="Alle Lichter"
DESC_all="Alles"

echo "Content-type: text/html"
echo ""
echo "<html>"
echo "<head>"
echo "<title>Realraum rf433ctl</title>"
echo "</head>"
echo "<body>"
#echo "<h1>Realraum rf433ctl</h1>"
for DISPID in $VALIDIDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <input type='submit' name='power' value='on' />"
  echo " <input type='submit' name='power' value='off' />"
  echo "</span></div>"
  echo "</form>"
done
echo "</body>"
echo "</html>"
