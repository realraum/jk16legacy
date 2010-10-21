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
    elif [ "$VALUE" == "ajax" ]; then
      AJAX='?'
    elif [ "$AJAX" == "?" ]; then
      AJAX=$VALUE
    fi
    i=$i+1
  done
done

UNIXSOCK=/var/run/powersensordaemon/cmd.sock
VALID_ONOFF_IDS="decke ambientlights lichter all werkzeug labor dart logo idee deckehinten deckevorne"
VALID_SEND_IDS="ymhpoweron ymhpoweroff ymhpower ymhvolup ymhvoldown ymhcd ymhwdtv ymhtuner ymhaux ymhsattv ymhvolmute ymhmenu ymhplus ymhminus ymhtest ymhtimelevel ymheffect ymhprgup ymhprgdown ymhtunplus ymhtunminus ymhtunabcde ymhtape ymhvcr ymhextdec ymhsleep ymhp5 panicled blueled moviemode"


[ "$POWER" == "send" ] && POWER=on
if [ "$POWER" == "on" -o "$POWER" == "off" ]; then
  for CHECKID in $VALID_ONOFF_IDS $VALID_SEND_IDS; do 
    if [ "$CHECKID" == "$ID" ]; then
      echo "power $POWER $ID" | usocket $UNIXSOCK
      echo "Content-type: text/html"
      echo ""
      echo "<html>"
      echo "<head>"
      echo "<title>Realraum rf433ctl</title>"
      echo '<script type="text/javascript">window.location="http://slug.realraum.at/cgi-bin/switch.cgi";</script>'
      echo "</head></html>"
      exit 0
    fi
  done
fi

DESC_werkzeug="Werkzeug LEDs"
DESC_stereo="Receiver On/Off"
DESC_ambientlights="Ambient Lichter"
DESC_labor="Labor Licht"
DESC_dart="Dart Scheibe"
DESC_logo="Logo"
DESC_idee="Idee"
DESC_deckehinten="Decke Hinten"
DESC_deckevorne="Decke Vorne"
DESC_decke="Deckenlichter"
DESC_lichter="Alle Lichter"
DESC_all="Alles"
DESC_ymhpoweron="Receiver On"
DESC_ymhpoweroff="Receiver Off"
DESC_ymhpower="Receiver On/Off"
DESC_ymhvolup="VolumeUp"
DESC_ymhvoldown="VolumeDown"
DESC_ymhcd="Input CD"
DESC_ymhwdtv="Input WDlxTV"
DESC_ymhtuner="Input Tuner"
DESC_ymhvolmute="Mute"
DESC_ymhmenu="Menu"
DESC_ymhplus="+"
DESC_ymhminus="-"
DESC_ymhtest="Test"
DESC_ymhtimelevel="Time/Levels"
DESC_ymheffect="DSP Effect Toggle"
DESC_ymhprgup="DSP Up"
DESC_ymhprgdown="DSP Down"
DESC_ymhtunplus="Tuner +"
DESC_ymhtunminus="Tuner -"
DESC_ymhtunabcde="Tuner ABCDE"
DESC_ymhtape="Tape"
DESC_ymhvcr="VCR"
DESC_ymhextdec="ExtDec Toggle"
DESC_seep="Sleep Modus"
DESC_panicled="HAL9000 says hi"
DESC_blueled="Blue Led"
DESC_moviemode="Movie Mode"
echo "Content-type: text/html"
echo ""
echo "<html>"
echo "<head>"
echo "<title>Realraum rf433ctl</title>"
echo '<script type="text/javascript">'
echo 'function sendButton( onoff, btn )'
echo '{'
echo ' var req = new XMLHttpRequest();'
echo ' url = "http://slug.realraum.at/cgi-bin/switch.cgi?power="+onoff+"&id="+btn;'
echo ' req.open("GET", url ,false);'
echo ' //google chrome workaround'
echo ' req.setRequestHeader("googlechromefix","");'
echo ' req.send(null);'
echo '}'
echo '</script>'
echo "</head>"
echo "<body>"
#echo "<h1>Realraum rf433ctl</h1>"
echo "<div style=\"float:left; border:1px solid black;\">"
for DISPID in $VALID_ONOFF_IDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  if [ -z "$AJAX" ]; then

  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <input type='submit' name='power' value='on' />"
  echo " <input type='submit' name='power' value='off' />"
  echo "</span></div>"
  echo "</form>"
  
  else
  
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <button onClick='sendButton(\"on\",\"$DISPID\");'>On</button>"
  echo " <button onClick='sendButton(\"off\",\"$DISPID\");'>Off</button>"
  echo "</span></div>"
  
  fi
done
echo "</div>"
echo "<div style=\"float:left; border:1px solid black;\">"
for DISPID in $VALID_SEND_IDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  if [ -z "$AJAX" ]; then

  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <input type='submit' name='power' value='send' />"
  echo "</span></div>"
  echo "</form>"

  else
  
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <button onClick='sendButton(\"on\",\"$DISPID\");'>Send</button>"
  echo "</span></div>"
  
  fi
done
echo "</div>"
echo "</body>"
echo "</html>"
