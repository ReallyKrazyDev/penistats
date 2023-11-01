#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# MIT License
#
# Copyright 2023 KrzDvt
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.#!/usr/bin/env python

#
# Dependencies
#
# pip install schedule
# + pyhelp's dependencies


import sys
sys.path.insert(1, '../pyhelp/')


import os
import json
import time
import socket
import argparse
import schedule

from misc import *
from mqtt import *


#
# Classes
#

class Values:
  TAG_CPU_TEMP_C = 'cpuTempC'
  TAG_CPU_FREQ_GHZ = 'cpuFreqGHz'
  TAG_CPU_LOAD_AVG_1MN_PCT = 'cpuLoadAvg1MnPct'
  TAG_CPU_LOAD_AVG_5MN_PCT = 'cpuLoadAvg5MnPct'
  TAG_CPU_LOAD_AVG_10MN_PCT = 'cpuLoadAvg10MnPct'
  TAG_MEM_TOTAL_KB = 'memTotalKB'
  TAG_MEM_FREE_KB = 'memFreeKB'
  TAG_MEM_FREE_PCT = 'memFreePct'
  TAG_MEM_AVAIL_KB = 'memAvailKB'
  TAG_SWAP_TOTAL_KB = 'swapTotalKB'
  TAG_SWAP_FREE_KB = 'swapFreeKB'
  TAG_SWAP_FREE_PCT = 'swapFreePct'

  def __init__(self, ):
    self.cpuTempC:float = None
    self.cpuFreqGHz:float = None
    self.cpuLoadAvg1MnPct:int = None
    self.cpuLoadAvg5MnPct:int = None
    self.cpuLoadAvg10MnPct:int = None
    self.memTotalKB:int = None
    self.memFreeKB:int = None
    self.memFreePct:int = None
    self.memAvailKB:int = None
    self.swapTotalKB:int = None
    self.swapFreeKB:int = None
    self.swapFreePct:int = None

  def toDict(self):
    res:dict = {}
    if self.cpuTempC is not None:
      res[Values.TAG_CPU_TEMP_C] = self.cpuTempC
    if self.cpuFreqGHz is not None:
      res[Values.TAG_CPU_FREQ_GHZ] = self.cpuFreqGHz
    if self.cpuLoadAvg1MnPct is not None:
      res[Values.TAG_CPU_LOAD_AVG_1MN_PCT] = self.cpuLoadAvg1MnPct
    if self.cpuLoadAvg5MnPct is not None:
      res[Values.TAG_CPU_LOAD_AVG_5MN_PCT] = self.cpuLoadAvg5MnPct
    if self.cpuLoadAvg10MnPct is not None:
      res[Values.TAG_CPU_LOAD_AVG_10MN_PCT] = self.cpuLoadAvg10MnPct
    if self.memTotalKB is not None:
      res[Values.TAG_MEM_TOTAL_KB] = self.memTotalKB
    if self.memFreeKB is not None:
      res[Values.TAG_MEM_FREE_KB] = self.memFreeKB
    if self.memFreePct is not None:
      res[Values.TAG_MEM_FREE_PCT] = self.memFreePct
    if self.memAvailKB is not None:
      res[Values.TAG_MEM_AVAIL_KB] = self.memAvailKB
    if self.swapTotalKB is not None:
      res[Values.TAG_SWAP_TOTAL_KB] = self.swapTotalKB
    if self.swapFreeKB is not None:
      res[Values.TAG_SWAP_FREE_KB] = self.swapFreeKB
    if self.swapFreePct is not None:
      res[Values.TAG_SWAP_FREE_PCT] = self.swapFreePct
    return res

class ScheduleEverySettings:
  def __init__(self, settingsDict:dict=None):
    self.minutes = None

    if settingsDict is not None:
      if 'minutes' in settingsDict:
        self.minutes = settingsDict['minutes']

  def isSet(self) -> bool:
    return ( self.minutes is not None )

class ScheduleSettings:
  def __init__(self, settingsDict:dict=None):
    self.every:ScheduleEverySettings = None

    if settingsDict is not None:
      if 'every' in settingsDict:
        self.every = ScheduleEverySettings(settingsDict['every'])

  def isSet(self) -> bool:
    return ( self.every is not None and self.every.isSet() )

class Settings:
  def __init__(self, settingsDict:dict=None):
    self.device:DeviceSettings = None
    self.schedule:ScheduleSettings = None
    self.mqtts:list[MqttSettings] = []

    if settingsDict is not None:
      if 'device' in settingsDict:
        self.device = DeviceSettings(settingsDict['device'])
      if 'schedule' in settingsDict:
        self.schedule = ScheduleSettings(settingsDict['schedule'])
      if 'mqtts' in settingsDict:
        for mqttDict in settingsDict['mqtts']:
          self.mqtts.append(MqttSettings(mqttDict))

  def isSet(self) -> bool:
    # device is mandatory
    if self.device is None or not self.device.isSet():
      print('settings : device not set')
      return False

    # schedule is optional

    # mqtts is optional
    if self.mqtts is not None and len(self.mqtts) > 0:
      for mqtt in self.mqtts:
        if not mqtt.isSet():
          print('settings : mqtt not set')
          return False

    return True


#
#  Process methods
#

def readSettings(filePath:str) -> Settings:
  try:
    file = None
    fileDict = None
    with open(filePath, 'r') as file:
      fileDict = json.load(file)
    return Settings(fileDict)
  except Exception as excp:
    print('Failed reading settings file : ' + str(excp))
    return None

def fixDeviceSettings(settings:DeviceSettings):
  file = None
  lcLine:str = None

  if not isStringEmpty(settings.group):
    settings.group = ''.join(e for e in settings.group if e.isalnum())
  if isStringEmpty(settings.group):
    settings.group = "penistats"

  look4Serial:bool = isStringEmpty(settings.serial)
  look4Model:bool = isStringEmpty(settings.model)
  if look4Serial or look4Model:
    try:
      with open('/proc/cpuinfo', 'r') as file:
        for line in file:
          line = line.strip()
          lcLine = line.lower()
          if look4Serial and  lcLine.startswith('serial'):
            settings.serial = line[line.index(':')+1:].strip()
          if look4Model and lcLine.startswith('model'):
            settings.model = line[line.index(':')+1:].strip()
    except:
      pass

  if isStringEmpty(settings.version):
    try:
      with open('/proc/version', 'r') as file:
        settings.version = file.read()
    except:
      pass

  if isStringEmpty(settings.name):
    deviceName:str = os.uname().nodename
    if isStringEmpty(deviceName):
      deviceName = socket.gethostname()
      if not deviceName.find('.')>=0:
        deviceName = socket.gethostbyaddr(deviceName)[0]
    settings.name = deviceName

  if settings.serial is not None :
    settings.serial = ''.join(e for e in settings.serial if e.isalnum())

  if isStringEmpty(settings.manufacturer) and settings.model is not None and 'raspberry' in settings.model.lower():
    settings.manufacturer = 'Raspberry Pi Foundation'

  if settings.version is not None:
    settings.version = settings.version.strip()

def fixSettings(settings:Settings) -> Settings:
  if settings is None:
    return None
  if settings.device is None:
    settings.device = DeviceSettings()
  fixDeviceSettings(settings.device)
  return settings

def dispSettings(settings:Settings):
  if settings.device is not None:
    print('  device')
    print('    group={0}'.format(settings.device.group))
    print('    serial={0}'.format(settings.device.serial))
    print('    manufacturer={0}'.format(settings.device.manufacturer))
    print('    model={0}'.format(settings.device.model))
    print('    version={0}'.format(settings.device.version))
    print('    name={0}'.format(settings.device.name))

  if settings.schedule is not None:
    print('  schedule')
    if settings.schedule.every is not None:
      print('    every')
      print('      minutes={0}'.format(settings.schedule.every.minutes))

  if settings.mqtts is not None:
    print('  mqtts')
    for mqtt in settings.mqtts:
      print('    mqtt')
      print('      hostname={0}'.format(mqtt.hostname))
      print('      port={0}'.format(mqtt.port))
      print('      clientId={0}'.format(mqtt.clientId))
      print('      username={0}'.format(mqtt.username))
      print('      password={0}'.format('***' if mqtt.password is not None and len(mqtt.password.strip()) > 0 else ''))
      print('      isHA={0}'.format(mqtt.isHA))

def readValues() -> Values:
  file = None
  idx:int = None
  line:str = None
  lcline:str = None
  values:Values = Values()

  try:
    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
      values.cpuTempC = int(file.read()) / 1000.0
  except:
    pass

  try:
    with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as file:
      values.cpuFreqGHz = int(file.read()) / 1000000.0
  except:
    pass

  try:
    avgs = None
    with open('/proc/loadavg', 'r') as file:
      line = file.read().strip()
      avgs = line.split(' ')
      if len(avgs) >= 3:
        values.cpuLoadAvg1MnPct = int(float(avgs[0]) * 100)
        if values.cpuLoadAvg1MnPct < 0 or values.cpuLoadAvg1MnPct > 100:
          values.cpuLoadAvg1MnPct = None
        values.cpuLoadAvg5MnPct = int(float(avgs[1]) * 100)
        if values.cpuLoadAvg5MnPct < 0 or values.cpuLoadAvg5MnPct > 100:
          values.cpuLoadAvg5MnPct = None
        values.cpuLoadAvg10MnPct = int(float(avgs[2]) * 100)
        if values.cpuLoadAvg10MnPct < 0 or values.cpuLoadAvg10MnPct > 100:
          values.cpuLoadAvg10MnPct = None
  except:
    pass

  try:
    with open('/proc/meminfo', 'r') as file:
      for line in file:
        line = line.strip()
        idx = line.index(':')
        if idx >= 0:
          lcline = line.lower()
          value = ''.join(c for c in line[idx+1:] if (c.isdigit() or c =='.'))
          if lcline.startswith('memtotal'):
            values.memTotalKB = int(value)
          elif lcline.startswith('memfree'):
            values.memFreeKB = int(value)
          elif lcline.startswith('memavailable'):
            values.memAvailKB = int(value)
          elif lcline.startswith('swaptotal'):
            values.swapTotalKB = int(value)
          elif lcline.startswith('swapfree'):
            values.swapFreeKB = int(value)
    if values.memTotalKB is not None and values.memTotalKB > 0:
      if values.memFreeKB is not None:
        values.memFreePct = int(values.memFreeKB*100/values.memTotalKB)
    if values.swapTotalKB is not None and values.swapTotalKB > 0:
      if values.swapFreeKB is not None:
        values.swapFreePct = int(values.swapFreeKB*100/values.swapTotalKB)
  except:
    pass

  return values

def dispValues(values:Values):
  print('cpu temp={0:3.2f}°C freq={1:0.1f}MHz load={2}%/{3}%/{4}%'.format( \
    values.cpuTempC if values.cpuTempC is not None else -1, \
    values.cpuFreqGHz if values.cpuFreqGHz is not None else -1, \
    values.cpuLoadAvg1MnPct if values.cpuLoadAvg1MnPct is not None else -1, \
    values.cpuLoadAvg5MnPct if values.cpuLoadAvg5MnPct is not None else -1, \
    values.cpuLoadAvg10MnPct if values.cpuLoadAvg10MnPct is not None else -1))
  print('mem total={0}KB free={1}KB/{2}% avail={3}KB'.format( \
    values.memTotalKB if values.memTotalKB is not None else -1, \
    values.memFreeKB if values.memFreeKB is not None else -1, \
    values.memFreePct if values.memFreePct is not None else -1, \
    values.memAvailKB if values.memAvailKB is not None else -1))
  print('swap total={0}KB free={1}KB/{2}%'.format( \
    values.swapTotalKB if values.swapTotalKB is not None else -1, \
    values.swapFreeKB if values.swapFreeKB is not None else -1, \
    values.swapFreePct if values.swapFreePct is not None else -1))

def declareValues(settings:Settings) -> bool:
  global declareTstamp

  if settings.device is None or not settings.device.isSet():
    return False

  if declareTstamp is not None and ( time.time() - declareTstamp ) <= 12*3600:
    return False

  wait:bool = False

  if settings.mqtts is not None and len(settings.mqtts) <=0:
    declareValues:[DeclareValue] = []
    declareValues.append(DeclareValue('cpu temperature', '°C', Values.TAG_CPU_TEMP_C))
    declareValues.append(DeclareValue('cpu frequency', 'GHz', Values.TAG_CPU_FREQ_GHZ))
    declareValues.append(DeclareValue('cpu load average 1mn', '%', Values.TAG_CPU_LOAD_AVG_1MN_PCT))
    declareValues.append(DeclareValue('cpu load average 5mn', '%', Values.TAG_CPU_LOAD_AVG_5MN_PCT))
    declareValues.append(DeclareValue('cpu load average 10mn', '%', Values.TAG_CPU_LOAD_AVG_10MN_PCT))
    declareValues.append(DeclareValue('memory total', 'kB', Values.TAG_MEM_TOTAL_KB))
    declareValues.append(DeclareValue('memory free', 'kB', Values.TAG_MEM_FREE_KB))
    declareValues.append(DeclareValue('memory free (%)', '%', Values.TAG_MEM_FREE_PCT))
    declareValues.append(DeclareValue('memory available', 'kB', Values.TAG_MEM_AVAIL_KB))
    declareValues.append(DeclareValue('swap total', 'kB', Values.TAG_SWAP_TOTAL_KB))
    declareValues.append(DeclareValue('swap free', 'kB', Values.TAG_SWAP_FREE_KB))
    declareValues.append(DeclareValue('swap free (%)', '%', Values.TAG_SWAP_FREE_PCT))

    for mqtt in settings.mqtts:
      if declareValues2Mqtt(settings.device, mqtt, declareValues):
        wait = True

  declareTstamp = time.time()
  if wait:
    time.sleep(5)

  return True

def sendValues(values:Values, settings:Settings) -> int:
  sentCount:int = 0
  if settings.mqtts and len(settings.mqtts) > 0:
    for mqtt in settings.mqtts:
      if sendValues2Mqtt(values, settings.device, mqtt):
        sentCount += 1
    if sentCount > 0:
      time.sleep(5)
    sentCount = sentCount * 100 / len(settings.mqtts)
  else:
    sentCount = 100
  return sentCount

def readAndSendValues():
  global settings
  values:Values = readValues()
  declareValues(settings)
  sentPct:int = sendValues(values, settings)
  if sentPct < 100:
    print('Values sent to only {0}% of destination(s)'.format(sentPct))


#
# Main (sort of)
#

argParser = argparse.ArgumentParser(prog='penistats', description='Penguin Stats')
argParser.add_argument('-s', '--set', default='penistats.conf', help='settings file path')
args = argParser.parse_args()

declareTstamp:int = None

settings:Settings = readSettings(args.set if not isStringEmpty(args.set) else 'penistats.conf')
fixSettings(settings)

if settings is not None and settings.isSet():
  if settings.schedule is not None and settings.schedule.isSet():
    if settings.schedule.every is not None and settings.schedule.every.isSet():
      if settings.schedule.every.minutes is not None and settings.schedule.every.minutes > 0:
        schedule.every(settings.schedule.every.minutes).minutes.do(readAndSendValues)

    print('Loop with settings')
    dispSettings(settings)
    while True:
      schedule.run_pending()
      time.sleep(30)
  else:
    print('Single shot with settings')
    dispSettings(settings)
    values:Values = readValues()
    dispValues(values)
    declareValues(settings)
    sendValues(values, settings)
else:
  print('Single shot without settings')
  values:Values = readValues()
  dispValues(values)
