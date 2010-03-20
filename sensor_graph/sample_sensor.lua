#!/usr/bin/lua
require('os')
require('string')
require('io')

function parse_value(str)
  last_temp = 0.0
  last_light = 0
  if string.find(str,"temp0: Temp C:") then
    last_temp = tonumber(string.sub(str,15))
    os.execute(string.format("rrdtool update /home/sensortemp.rrd -t temp N:%f", last_temp))
    --print(string.format("t: %f Grad Celsius",last_temp))
  end
  if string.find(str,"photo0: Photo:") then
    last_light = tonumber(string.sub(str,15))
    os.execute(string.format("rrdtool update /home/sensorlight.rrd -t light N:%d", last_light))
    --print(string.format("p: %d",last_light))
  end
end

while 1 do
   local line = io.read("*line")
    if line then 
      parse_value(line) 
    else
      break
    end
end
