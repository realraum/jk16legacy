#!/bin/sh
echo -e "listen sensor\nlisten movement\n" | usocket /var/run/powersensordaemon/cmd.sock -n | ./sample_sensor3.lua &>/dev/null &
