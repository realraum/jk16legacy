#!/bin/sh
UNIXSOCK=/var/run/powersensordaemon/cmd.sock
TMPFILE=$(mktemp)
echo "sample photo0" | usocket $UNIXSOCK -n > $TMPFILE &
PID=$!
echo "Content-type: text/html"
echo ""
while [ ! -s $TMPFILE ]; do 
	continue
done
cat $TMPFILE | cut -d' ' -f 2
rm $TMPFILE
kill $PID
exit 0
