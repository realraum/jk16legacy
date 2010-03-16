#!/usr/bin/lua
require('os')
require('string')
require('socket')

last_movement = 0

function save_values()
  os.execute(string.format("rrdtool update /home/sensordata.rrd -t temp:light:movement N:%f:%d:%d", last_temp, last_light, last_movement))
  last_movement=0
end


function parse_value(str)
  last_temp = 0.0
  last_light = 0
  if string.find(str,"Sensor T: Temp C:") then
    last_temp = tonumber(string.sub(str,18))
    os.execute(string.format("rrdtool update /home/sensordata.rrd -t temp N:%f", last_temp))
    print(string.format("t: %f Grad Celsius",last_temp))
  end
  if string.find(str,"Sensor P: Photo:") then
    last_light = tonumber(string.sub(str,17))
    os.execute(string.format("rrdtool update /home/sensordata.rrd -t light N:%d", last_light))
    print(string.format("p: %d",last_light))
  end
  if string.find(str,"movement") then
    --last_movement=1
    os.execute(string.format("rrdtool update /home/sensordata.rrd -t movement N:%d", 1))
  end
end


local socket_factory = require("socket.unix");
local socket = socket_factory()


while 1 do
  local client = socket.connect("/var/run/powersensordaemon/cmd.sock")
  if client then
    client:send("listen sensor\n")
    --client:settimeout(30)
    while 1 do
      local line, err = client:receive()
      if not err then 
        parse_value(line) 
      elseif err ~= "timeout" then
        break
      end
    end
    client:shutdown("both")
  end
  --wait 10 seconds
  socket.select(nil, nil, 10)
end
