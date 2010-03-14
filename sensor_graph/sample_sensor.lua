require('os')
require('string')

last_temp = 0.0
last_light = 0
last_movement = 0

function save_values()
  os.execute(string.format("rrdtool update /home/sensordata.rrd -t temp:light:movement N:%f:%d:%d", last_temp, last_light, last_movement))
  last_movement=0
end


function parse_value(str)
  if string.find(str,"Temp C:") then
    last_temp = tonumber(string.sub(str,11))
    --print(string.format("t: %f Grad Celsius",last_temp))
  end
  if string.find(str,"Photo:") then
    last_light = tonumber(string.sub(str,10))
    --print(string.format("p: %d",last_light))
  end
  if string.find(str,"movement") then
   last_movement=1
   --print "something moved"
  end
end


local socket = require("socket")

while 1 do
  local client = socket.connect("127.0.0.1",2010)
  --socket.unix = require("socket.unix")
  --local socket = assert(socket.unix())
  --local client = assert(socket:connect("/var/run/power_sensor.socket"))
  if client then
    client:settimeout(30)
    while 1 do
      local line, err = client:receive()
      if not err then 
        parse_value(line) 
      elseif err ~= "timeout" then
        break
      end
      client:send("T")
      line, err = client:receive()
      if not err then 
        parse_value(line)
      elseif err ~= "timeout" then
        break
      end
      client:send("P")
      line, err = client:receive()
      if not err then 
        parse_value(line)
      elseif err ~= "timeout" then
        break
      end
      save_values()
    end
    client:shutdown("both")
  end
  socket.select(nil, nil, 10)
end
