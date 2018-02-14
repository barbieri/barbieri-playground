#!/usr/bin/lua
-- Disconnect WiFi STA (clients) based on their signal levels.
--
-- This is designed to work with openwrt's libiwinfo-lua, libuci-lua
-- and ubus services: network.wireless and hostapd.

local ubus = require("ubus")
local nixio = require("nixio")
local iwinfo = require("iwinfo")
local uci = require("uci")

local remember_gone = 60 -- remember gone STA for this amount of seconds

local openlog_args = {"wifi-disconnect-low-signal"}
local loglevel = 0
local loglevels = {"info", "debug"}
local loglevel_enabled = {}

-- cmdline arguments:
--  * --stderr: print log to stderr as well as syslog
--  * -v --verbose: increase verbosity
for i, a in ipairs(arg) do
   if i > 0 then
      if a == "--stderr" then
         openlog_args[#openlog_args + 1] = "perror"
      elseif a == "-v" or a == "--verbose" then
         loglevel = loglevel + 1
      end
   end
end

for i, level in ipairs(loglevels) do
   loglevel_enabled[level] = i <= loglevel
end

nixio.openlog(unpack(openlog_args))

function dbg(fmt, ...)
   if not loglevel_enabled["debug"] then return end
   local message = fmt:format(unpack(arg))
   nixio.syslog("debug", message)
end

function inf(fmt, ...)
   if not loglevel_enabled["info"] then return end
   local message = fmt:format(unpack(arg))
   nixio.syslog("info", message)
end

function crit(fmt, ...)
   local message = fmt:format(unpack(arg))
   nixio.syslog("crit", message)
end

function gettime()
   local sec, usec
   sec, usec = nixio.gettimeofday()
   return sec
end

local cursor = uci.cursor()
if not cursor then
   crit("Failed to open UCI cursor")
   os.exit(1)
end

local conn = ubus.connect()
if not conn then
   crit("Failed to connect to ubus")
   os.exit(1)
end

local STA = {}
STA.__index = STA

function STA.new(addr)
   local self = setmetatable({}, STA)
   self.addr = addr
   self.subject = addr:gsub(":", ""):upper()
   self.signal = 0
   self.noise = 0
   self.strikes = strikes or 0
   self.is_new = true
   self.disconnected_at = nil
   self.gone_at = nil
   return self
end

function STA:__tostring()
   local now = gettime()
   local disconnected, gone
   if self.disconnected_at == nil then
      disconnected = ""
   else
      disconnected = string.format(
         ", disconnected=%ds", now - self.disconnected_at)
   end
   if self.gone_at == nil then
      gone = ""
   else
      gone = string.format(
         ", gone=%ds", now - self.gone_at)
   end
   return string.format(
      "%s {" ..
         "signal=%ddBm, " ..
         "noise=%ddBm, " ..
         "snr=%ddBm, " ..
         "strikes=%d, "..
         "is_new=%s"..
         "%s%s}",
      self.addr,
      self.signal,
      self.noise,
      self.snr,
      self.strikes,
      tostring(self.is_new),
      disconnected,
      gone)
end

function STA:update(info)
   self.signal = info.signal
   self.noise = info.noise
   self.snr = self.signal - self.noise
end

function STA:matches(matcher)
   local len = matcher.max_len
   while len >= matcher.min_len do
      local subject = self.subject:sub(1, len)
      if matcher[subject] then
         return true
      end
      len = len - 1
   end
   return false
end

-- creates a table with [prefix] = true and sets the prefix length
-- range as max_len and min_len. Then the matcher should use
-- string.sub(1, len) for len in closed range min_len to max_len,
-- checking if the prefix exists in the matcher.
function prefix_list_matcher(str)
   if str == nil or str == "" then
      return nil
   end

   local matcher = {}
   local max_len = 0
   local min_len = 12
   for p in str:gmatch("([^,]+)") do
      if p ~= "" then
         matcher[p] = true

         local plen = p:len()
         if max_len < plen then
            max_len = plen
         end
         if min_len > plen then
            min_len = plen
         end
      end
   end
   if max_len < 1 then
      return nil
   end

   matcher.max_len = max_len
   matcher.min_len = min_len

   return matcher
end

-- defines an uci config option given its name, how to convert it to
-- native type and the default value
function DeviceOpt(name, type, default)
   return { name = name, type = type, default = default }
end

local Device = {}
Device.__index = Device
Device.conf_options = {
   signal_connect = DeviceOpt("signal_connect", tonumber, -128),
   signal_stay = DeviceOpt("signal_stay", tonumber, -128),
   snr_connect = DeviceOpt("signal_snr_connect", tonumber, 0),
   snr_stay = DeviceOpt("signal_snr_stay", tonumber, 0),
   poll_time = DeviceOpt("signal_poll_time", tonumber, 3),
   strikes = DeviceOpt("signal_strikes", tonumber, 3),
   drop_reason = DeviceOpt("signal_drop_reason", tonumber, 3),
   whitelist = DeviceOpt("signal_whitelist", prefix_list_matcher, nil),
   blacklist = DeviceOpt("signal_blacklist", prefix_list_matcher, nil),
}

function Device.new(ifname, conf_section)
   local self = setmetatable({}, Device)
   self.ifname = ifname
   local api = iwinfo.type(self.ifname)
   self.iw = iwinfo[api]

   for key, opt in pairs(Device.conf_options) do
      local conf = cursor:get("wireless", conf_section, opt.name)
      self[key] = opt.type(conf) or opt.default
   end

   self.stas = {} -- addr -> STA
   self.updated_at = nil
   return self
end

function Device:__tostring()
   local connect, stay

   if self.snr_connect > 0 then
      connect = string.format("snr_connect=%ddBm", self.snr_connect)
   else
      connect = string.format("signal_connect=%ddBm", self.signal_connect)
   end
   if self.snr_stay > 0 then
      stay = string.format("snr_stay=%ddBm", self.snr_stay)
   else
      stay = string.format("signal_stay=%ddBm", self.signal_stay)
   end

   return string.format(
      "%s {" ..
         "%s, " ..
         "%s, " ..
         "poll_time=%ds, " ..
         "strikes=%d, " ..
         "drop_reason=%d}",
      self.ifname,
      connect,
      stay,
      self.poll_time,
      self.strikes,
      self.drop_reason)
end

function Device:get_sta(addr)
   local sta = self.stas[addr]

   if sta == nil then
      sta = STA.new(addr)

      if self.whitelist ~= nil and not sta:matches(self.whitelist) then
         dbg("%s: ignored %s (whitelist)", self.ifname, addr)
         return nil
      end

      if self.blacklist ~= nil and sta:matches(self.blacklist) then
         dbg("%s: ignored %s (blacklist)", self.ifname, addr)
         return nil
      end

      self.stas[addr] = sta
   elseif sta.is_new then
      sta.is_new = false
   end

   return sta
end

function Device:next_poll()
   return self.updated_at + self.poll_time
end

function Device:update_stas(now)
   if self.updated_at ~= nil and now - self.updated_at < self.poll_time then
      return nil
   end

   local stas = {
      connected = {},
      disconnected = {},
   }
   self.updated_at = now

   local assoclist = self.iw.assoclist(self.ifname)
   if not assoclist or next(assoclist) == nil then
      dbg("%s: no associated STAs", self.ifname)
      self:cleanup_stas(stas.connected)
      return stas
   end

   for addr, info in pairs(assoclist) do
      local sta = self:get_sta(addr)
      if sta ~= nil and sta.disconnected_at == nil then
         sta:update(info)

         if self:should_disconnect_sta(sta) then
            self:disconnect_sta(sta)
            sta.disconnected_at = now
            sta.gone_at = now
            stas.disconnected[#stas.disconnected + 1] = sta
            stas.disconnected[addr] = sta
         else
            sta.gone_at = nil
            stas.connected[#stas.connected + 1] = sta
            stas.connected[addr] = sta
         end
      end
   end

   dbg("%s: signal poll: %i STAs, %i disconnected",
       self.ifname, #stas.connected + #stas.disconnected,
       #stas.disconnected)

   self:cleanup_stas(stas.connected)
   return stas
end

function Device:cleanup_stas(connected)
   local to_remove = {}
   local now = self.updated_at
   for addr, sta in pairs(self.stas) do
      if connected[addr] == nil then
         if sta.gone_at == nil then
            dbg("%s: %s is gone", self.ifname, addr)
            sta.gone_at = now
         elseif now - sta.gone_at > remember_gone then
            to_remove[#to_remove + 1] = addr
         end
      end
   end
   for _, addr in ipairs(to_remove) do
      dbg("%s: forget %s", self.ifname, addr)
      self.stas[addr] = nil
   end
end

function Device:should_disconnect_sta(sta)
   local label, ref_strikes, value
   if sta.is_new then
      if self.snr_connect > 0 then
         label = "snr_connect"
      else
         label = "signal_connect"
      end
      ref_strikes = 0
   else
      if self.snr_stay > 0 then
         label = "snr_stay"
      else
         label = "signal_stay"
      end
      ref_strikes = self.strikes
   end

   local ref = self[label]
   local value = sta[label:gsub("_%a+$", "")]

   function msg(status)
      dbg("%s: %s signal=%ddBm snr=%ddBm strikes=%d " ..
             "(threshold: %s=%d strikes=%d): %s",
          self.ifname, sta.addr, sta.signal, sta.snr, sta.strikes,
          label, ref, ref_strikes, status)
   end

   if ref <= value then
      msg("good signal")
      sta.strikes = 0
      return false
   end

   sta.strikes = sta.strikes + 1
   if ref_strikes > sta.strikes then
      msg("bad signal")
      return false
   end

   msg("should disconnect")
   return true
end

function Device:disconnect_sta(sta)
   local endpoint = "hostapd." .. self.ifname
   conn:call(endpoint, "del_client", {
                addr = sta.addr,
                reason = self.drop_reason,
                deauth = false,
                ban_time = 0,
   })
   inf("%s: disconnected %s", self.ifname, tostring(sta))
end

-- returns an array of all enabled devices as instances of Device.
function get_wifi_devices()
   local wireless_status = conn:call("network.wireless", "status", {})
   local devices = {}
   for name, radio in pairs(wireless_status) do
      if radio.disabled then
         dbg("%s: disabled by config file", name)
      else
         for _, iface in ipairs(radio.interfaces) do
            local dev = Device.new(iface.ifname, iface.section)
            if dev ~= nil then
               devices[#devices + 1] = dev
               dbg("%s: %s", name, tostring(dev))
            end
         end
      end
   end
   return devices
end

function update_devices_and_sleep(devices)
   local now = gettime()
   local next_poll_time = now + 60
   for _, dev in ipairs(devices) do
      dev:update_stas(now)
      local dev_next_poll_time = dev:next_poll()
      if next_poll_time > dev_next_poll_time then
         next_poll_time = dev_next_poll_time
      end
   end

   local seconds = next_poll_time - now
   if seconds > 0 then
      nixio.nanosleep(seconds)
   end
end

nixio.signal(3, "dfl")
nixio.signal(15, "dfl")

local devices = {}
while #devices == 0 do
   devices = get_wifi_devices()
   dbg("found %d enabled WiFi devices", #devices)
end

while true do
   local _, err = pcall(function () update_devices_and_sleep(devices) end)
   if err ~= nil then
      dbg("quit: %s", tostring(err))
      break
   end
end

nixio.closelog()
conn:close()
