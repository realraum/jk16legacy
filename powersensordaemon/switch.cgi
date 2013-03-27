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
    elif [ "$VALUE" == "mobile" ]; then
      MOBILE='1'
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
VALID_ONOFF_IDS="decke ambientlights lichter all werkzeug labor dart logo spots1 deckehinten deckevorne boiler whiteboard pcblueleds bikewcblue"
VALID_SEND_IDS_CUSTOM_DISPLAY="ymhpoweroff ymhpower ymhvolup ymhvoldown"
VALID_SEND_IDS="ymhpoweron ymhcd ymhwdtv ymhtuner ymhaux ymhsattv ymhvolmute ymhmenu ymhplus ymhminus ymhtest ymhtimelevel ymheffect ymhprgup ymhprgdown ymhtunplus ymhtunminus ymhtunabcde ymhtape ymhvcr ymhextdec ymhsleep ymhp5 panicled blueled moviemode"
#VALID_BANSHEE_IDS="playPause next prev"
#VALID_CAM_MOTOR_IDS="c C w W"

[ "$POWER" == "Off" ] && POWER=off
[ "$POWER" != "off" ] && POWER=on
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

  for CHECKID in $VALID_BANSHEE_IDS; do
    if [ "$CHECKID" == "$ID" ]; then
      echo "$ID/" | nc wuerfel.realraum.at 8484
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

  for CHECKID in $VALID_CAM_MOTOR_IDS; do
    if [ "$CHECKID" == "$ID" ]; then
      echo "$ID" > /dev/ttyACM0
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

DESC_pcblueleds="Blaue Leds PC"
DESC_bikewcblue="Blaue Lichterkette WC"
DESC_weissB="WeissB"
DESC_werkzeug="Werkzeug LEDs"
DESC_stereo="Receiver On/Off"
DESC_ambientlights="Ambient Lichter"
DESC_labor="Labor Licht"
DESC_boiler="Warmwasser WC"
DESC_dart="Dart Scheibe"
DESC_logo="Logo"
DESC_spots1="Spots"
DESC_deckehinten="Decke Hinten"
DESC_deckevorne="Decke Vorne"
DESC_whiteboard="Whiteboard Vorne"
DESC_decke="Deckenlichter"
DESC_lichter="Alle Lichter"
DESC_all="Alles"
DESC_ymhpoweron="Receiver On (off+tgl)"
DESC_ymhpoweroff="Receiver Off"
DESC_ymhpower="Receiver On/Off"
DESC_ymhvolup="VolumeUp"
DESC_ymhvoldown="VolumeDown"
DESC_ymhcd="Input CD"
DESC_ymhwdtv="Input S/PDIF Wuerfel"
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
DESC_w="Cam >"
DESC_W="Cam >>"
DESC_c="Cam <"
DESC_C="Cam <<"

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
echo '<style>'
echo 'div.switchbox {'
echo '    float:left;'
echo '    margin:2px;'
#echo '    max-width:236px;'
echo '    max-width:300px;'
echo '    font-size:10pt;'
echo '    border:1px solid black;'
#echo '    height: 32px;'
echo '    padding:0;'
echo '}'
  
echo 'div.switchnameleft {'
echo '    width:12em; display:inline-block; vertical-align:middle; margin-left:3px;'
echo '}'

echo 'span.alignbuttonsright {'
echo '    top:0px; float:right; display:inline-block; text-align:right; padding:0;'
echo '}'

echo 'div.switchnameright {'
echo '    width:12em; display:inline-block; vertical-align:middle; float:right; display:inline-block; margin-left:1ex; margin-right:3px; margin-top:3px; margin-bottom:3px;'
echo '}'

echo 'span.alignbuttonsleft {'
echo '    float:left; text-align:left; padding:0;'
echo '}'

echo '.onbutton {'
echo '    font-size:11pt;'
echo '    width: 40px;'
echo '    height: 32px;'
echo '    background-color: lime;'
echo '    margin: 0px;'
echo '}'

echo '.offbutton {'
echo '    font-size:11pt;'
echo '    width: 40px;'
echo '    height: 32px;'
echo '    background-color: red;'
echo '    margin: 0px;'
echo '}'

echo '.sendbutton {'
echo '    font-size:11pt;'
echo '    width: 40px;'
echo '    height: 32px;'
#echo '    background-color: grey;'
echo '    margin: 0px;'
echo '}'
echo '</style>'
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
  echo "<div class=\"switchbox\"><div class=\"switchnameleft\">$NAME</div><span class=\"alignbuttonsright\">"
  echo " <input class=\"onbutton\" type='submit' name='power' value='on' />"
  echo " <input class=\"offbutton\" type='submit' name='power' value='off' />"
  echo "</span>"
  echo "</div>"
  echo "</form>"
  
  else
  
  echo "<div class=\"switchbox\">"
  echo "<span class=\"alignbuttonsleft\">"
  echo " <button class=\"onbutton\" onClick='sendButton(\"on\",\"$DISPID\");'>On</button>"
  echo " <button class=\"offbutton\" onClick='sendButton(\"off\",\"$DISPID\");'>Off</button>"
  echo "</span>"
  echo "<div class=\"switchnameright\">$NAME</div>"
  echo "</div>"
  
  fi
  if [ "$MOBILE" == "1" ]; then
    echo "<br/>"
  fi 
done
echo "</div>"
if [ "$MOBILE" != "1" ]; then                                                             
echo "<div style=\"float:left; border:1px solid black; margin-top:5px;\">"

  if [ -z "$AJAX" ]; then

  echo "<div class=\"switchbox\"><div class=\"switchnameleft\">Receiver Power</div><span class=\"alignbuttonsright\">"
  echo "<form action=\"/cgi-bin/switch.cgi\"><input type=\"hidden\" name=\"id\" value=\"ymhpower\" /><input class=\"sendbutton\" type='submit' name='power' value='tgl' /></form>"
  echo "<form action=\"/cgi-bin/switch.cgi\"><input type=\"hidden\" name=\"id\" value=\"ymhpower\" /><input class=\"offbutton\" type='submit' name='power' value='off' /></form>"
  echo "</span></div>"

  echo "<div class=\"switchbox\"><div class=\"switchnameleft\">Receiver Volume</div><span class=\"alignbuttonsright\">"
  echo "<form action=\"/cgi-bin/switch.cgi\"><input type=\"hidden\" name=\"id\" value=\"ymhvolup\" /><input class=\"sendbutton\" type='submit' name='power' value='&uarr;' /></form>"
  echo "<form action=\"/cgi-bin/switch.cgi\"><input type=\"hidden\" name=\"id\" value=\"ymhvoldown\" /><input class=\"sendbutton\" type='submit' name='power' value='&darr;' /></form>"
  echo "</span></div>"

  else
  
  echo "<div class=\"switchbox\">"
  echo "<span class=\"alignbuttonsleft\">"
  echo " <button class=\"sendbutton\" onClick='sendButton(\"on\",\"ymhpower\");'>Tgl</button>"
  echo " <button class=\"offbutton\" onClick='sendButton(\"on\",\"ymhpoweroff\");'>Off</button>"
  echo "</span>"
  echo "<div class=\"switchnameright\">Receiver Power</div>"
  echo "</div>"
    
  echo "<div class=\"switchbox\">"
  echo "<span class=\"alignbuttonsleft\">"
  echo " <button class=\"sendbutton\" onClick='sendButton(\"on\",\"ymhvolup\");'>&uarr;</button>"
  echo " <button class=\"sendbutton\" onClick='sendButton(\"on\",\"ymhvoldown\");'>&darr;</button>"
  echo "</span>"
  echo "<div class=\"switchnameright\">Receiver Volume</div>"
  echo "</div>"    
    
  fi

for DISPID in $VALID_SEND_IDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  if [ -z "$AJAX" ]; then

  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <input class=\"sendbutton\" type='submit' name='power' value='  ' />"
  echo "</span></div>"
  echo "</form>"

  else
  
  echo "<div class=\"switchbox\">"
  echo "<span class=\"alignbuttonsleft\">"
  echo " <button class=\"sendbutton\" onClick='sendButton(\"on\",\"$DISPID\");'> </button>"
  echo "</span>"
  echo "<div class=\"switchnameright\">$NAME</div>"
  echo "</div>"
    
  fi
done
echo "</div>"
echo "<div style=\"float:left; border:1px solid black; margin-top:5px;\">"
for DISPID in $VALID_BANSHEE_IDS $VALID_CAM_MOTOR_IDS; do
  NAME="$(eval echo \$DESC_$DISPID)"
  [ -z "$NAME" ] && NAME=$DISPID
  if [ -z "$AJAX" ]; then

  echo "<form action=\"/cgi-bin/switch.cgi\">"
  echo "<input type=\"hidden\" name=\"id\" value=\"$DISPID\" />"
  echo "<div style=\"float:left; margin:2px; padding:1px; max-width:236px; font-size:10pt; border:1px solid black;\"><div style='width:10em; display:inline-block; vertical-align:middle;'>$NAME</div><span style='float:right; text-align:right;'>"
  echo " <input class=\"sendbutton\" type='submit' name='power' value='  ' />"
  echo "</span></div>"
  echo "</form>"

  else
  
  echo "<div class=\"switchbox\">"
  echo "<span class=\"alignbuttonsleft\">"
  echo " <button class=\"sendbutton\" onClick='sendButton(\"on\",\"$DISPID\");'> </button>"
  echo "</span>"
  echo "<div class=\"switchnameright\">$NAME</div>"
  echo "</div>"
    
  fi
done
echo "</div>"
fi
echo "</body>"
echo "</html>"
