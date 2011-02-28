#!/bin/sh
UNIXSOCK=/var/run/powersensordaemon/cmd.sock
TMPFILE=$(mktemp)
echo "sample photo0" | usocket $UNIXSOCK -n > $TMPFILE &
PID=$!
echo "Content-type: text/html"
echo ""
A=0
while [ ! -s $TMPFILE ]; do
	if [ $((A++)) -gt 2000 ]; then
		break
	else
		continue
	fi
done
cat $TMPFILE | cut -d' ' -f 2
rm $TMPFILE
kill $PID
exit 0
