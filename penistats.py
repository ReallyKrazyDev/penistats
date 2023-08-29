#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# MIT License
#
# Copyright 2023 KrzDvt
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.#!/usr/bin/env python


import os
import json
import uuid
import time
import socket
import argparse
import schedule

from json import JSONEncoder
from paho.mqtt import client as MqttClient


#
# Tools
#

def isStringEmpty(string:str) -> bool:
  return string is None or len(string.strip()) <= 0

def buildBaseId(group:str, serial:str) -> str:
  return '{0}_{1}'.format(group, serial)

def buildValuesTopic(group:str, serial:str) -> str:
  return '{0}/{1}'.format(group, serial)


#
# Classes
#

class PeniJsonEncoder(JSONEncoder):
  def default(self, o):
    try:
      return o.toDict()
    except:
      return o.__dict__

class Values:
  def __init__(self, ):
    self.cpuTempC:float = None
    self.cpuFreqGHz:float = None
    self.memTotalKB:int = None
    self.memFreeKB:int = None
    self.memAvailKB:int = None
    self.swapTotalKB:int = None
    self.swapFreeKB:int = None

class DeviceSettings:
  def __init__(self, settingsDict:dict=None):
    self.group:str = None
    self.serial:str = None
    self.manufacturer:str = None
    self.model:str = None
    self.version:str = None
    self.name:str = None

    if settingsDict is not None:
      if 'group' in settingsDict:
        self.group = settingsDict['group']
      if 'serial' in settingsDict:
        self.serial = settingsDict['serial']
      if 'manufacturer' in settingsDict:
        self.manufacturer = settingsDict['manufacturer']
      if 'model' in settingsDict:
        self.serial = settingsDict['model']
      if 'version' in settingsDict:
        self.version = settingsDict['version']
      if 'name' in settingsDict:
        self.name = settingsDict['name']

  def isSet(self) -> bool:
    return ( \
      not isStringEmpty(self.group) and \
      not isStringEmpty(self.serial) and \
      not isStringEmpty(self.model) and \
      not isStringEmpty(self.name) \
    )

  def toDict(self) -> dict:
    res:dict = {}
    if not isStringEmpty(self.group):
      res['group'] = self.group
    if not isStringEmpty(self.serial):
      res['serial'] = self.serial
    if not isStringEmpty(self.manufacturer):
      res['manufacturer'] = self.manufacturer
    if not isStringEmpty(self.model):
      res['model'] = self.model
    if not isStringEmpty(self.version):
      res['version'] = self.version
    if not isStringEmpty(self.name):
      res['name'] = self.name
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

class MqttSettings:
  def __init__(self, settingsDict:dict=None):
    self.hostname:str = None;
    self.port:int = None
    self.topic:str = None
    self.clientId:str = None
    self.username:str = None
    self.password:str = None
    self.caCertsPath:str = None
    self.isHA:bool = None

    if settingsDict is not None:
      if 'hostname' in settingsDict:
        self.hostname = settingsDict['hostname']
      if 'port' in settingsDict:
        self.port = int(settingsDict['port'])
      if 'topic' in settingsDict:
        self.topic = settingsDict['topic']
      if 'clientId' in settingsDict:
        self.clientId = settingsDict['clientId']
      if 'username' in settingsDict:
        self.username = settingsDict['username']
      if 'password' in settingsDict:
        self.password = settingsDict['password']
      if 'caCertsPath' in settingsDict:
        self.caCertsPath = settingsDict['caCertsPath']
      if 'isHA' in settingsDict:
        self.isHA = bool(settingsDict['isHA'])

    if isStringEmpty(self.clientId):
      self.clientId = str(uuid.uuid4())

  def isSet(self) -> bool:
    return ( self.hostname is not None and self.port is not None )

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

class DeclareValue:
  def __init__(self, name:str, unit:str, tag:str):
    self.name = name.strip() if name is not None else None
    self.unit = unit.strip() if unit is not None else None
    self.tag = tag.strip() if tag is not None else None

  def toDict(self) -> dict:
    res:dict = {}
    if not isStringEmpty(self.name):
      res['name'] = self.name
    if not isStringEmpty(self.unit):
      res['unit'] = self.unit
    if not isStringEmpty(self.tag):
      res['tag'] = self.tag
    return res

class DeclareHADevice:
  def __init__(self, deviceSettings:DeviceSettings):
    self.identifiers:[str] = [buildBaseId(deviceSettings.group, deviceSettings.serial)]
    self.manufacturer:str = deviceSettings.manufacturer
    self.model:str = deviceSettings.model
    self.name:str = deviceSettings.name
    self.sw_version:str = deviceSettings.version

  def toDict(self) -> dict:
    res:dict = {}
    if self.identifiers is not None:
      res['identifiers'] = self.identifiers
    if not isStringEmpty(self.manufacturer):
      res['manufacturer'] = self.manufacturer
    if not isStringEmpty(self.model):
      res['model'] = self.model
    if not isStringEmpty(self.name):
      res['name'] = self.name
    if not isStringEmpty(self.sw_version):
      res['sw_version'] = self.sw_version
    return res

class DeclareHAValue:
  def __init__(self, deviceSettings:DeviceSettings, declareValue:DeclareValue):
    topic:str = buildValuesTopic(deviceSettings.group, deviceSettings.serial)
    id:str = buildBaseId(deviceSettings.group, deviceSettings.serial)

    icon:str = None
    if declareValue.unit == '°C' or declareValue.unit == '°F':
      icon = 'mdi:thermometer'
    elif declareValue.unit == 'kB':
      icon = 'mdi:memory'
    else:
      icon = 'mdi:eye'

    self.device:DeclareHADevice = DeclareHADevice(deviceSettings)
    self.enabled_by_default:bool = True
    self.entity_category:str = 'diagnostic'
    self.icon:str = icon
    self.json_attributes_topic = topic
    self.name = declareValue.name
    self.state_class = 'measurement'
    self.state_topic = topic
    self.unique_id = id + '_' + declareValue.tag
    self.unit_of_measurement = declareValue.unit
    self.value_template = '{{ ' + 'value_json.{0}'.format(declareValue.tag) + ' }}'

  def toDict(self) -> dict:
    res:dict = {}
    if self.device is not None:
      res['device'] = self.device.toDict()
    if self.enabled_by_default is not None:
      res['enabled_by_default'] = self.enabled_by_default
    if not isStringEmpty(self.entity_category):
      res['entity_category'] = self.entity_category
    if not isStringEmpty(self.icon):
      res['icon'] = self.icon
    if not isStringEmpty(self.json_attributes_topic):
      res['json_attributes_topic'] = self.json_attributes_topic
    if not isStringEmpty(self.name):
      res['name'] = self.name
    if not isStringEmpty(self.state_class):
      res['state_class'] = self.state_class
    if not isStringEmpty(self.state_topic):
      res['state_topic'] = self.state_topic
    if not isStringEmpty(self.unique_id):
      res['unique_id'] = self.unique_id
    if not isStringEmpty(self.unit_of_measurement):
      res['unit_of_measurement'] = self.unit_of_measurement
    if not isStringEmpty(self.value_template):
      res['value_template'] = self.value_template
    return res


#
#  Process methods
#

def buildMqttClient(settings:MqttSettings) -> MqttClient.Client :
  client = MqttClient.Client(settings.clientId)
  if settings.username is not None and len(settings.username.strip()) > 0:
    client.username_pw_set(settings.username, settings.password)
  if settings.caCertsPath is not None and len(settings.caCertsPath.strip()) > 0:
    client.tls_set(ca_certs=settings.caCertsPath)
  return client

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
  except:
    pass

  return values

def dispValues(values:Values):
  print('cpu temp={0:3.2f}°C freq={1:0.1f}MHz'.format(values.cpuTempC, values.cpuFreqGHz))
  print('mem total={0}KB free={1}KB avail={2}KB'.format(values.memTotalKB, values.memFreeKB, values.memAvailKB))
  print('swap total={0}KB free={1}KB'.format(values.swapTotalKB, values.swapFreeKB))

def declareValues2HAMqtt(client:MqttClient.Client, deviceSettings:DeviceSettings, declareValues:[DeclareValue]):
  topic:str = None
  payload:str = None
  declareHAValue:DeclareHAValue = None
  for declareValue in declareValues:
    topic = 'homeassistant/sensor/{0}/{1}/config'.format(deviceSettings.serial, declareValue.tag)
    declareHAValue = DeclareHAValue(deviceSettings, declareValue)
    payload = json.dumps(declareHAValue, cls=PeniJsonEncoder)
    client.publish(topic, payload, qos=0, retain=True)

def declareValues2DefaultMqtt(client:MqttClient.Client, deviceSettings:DeviceSettings, declareValues:[DeclareValue]):
  topic:str = buildValuesTopic(deviceSettings.group, deviceSettings.serial)
  payload:str = None

  payload = json.dumps(deviceSettings, cls=PeniJsonEncoder)
  client.publish('declare/{0}/device'.format(topic), payload, qos=0, retain=True)

  for declareValue in declareValues:
    payload = json.dumps(declareValue, cls=PeniJsonEncoder)
    client.publish('declare/{0}/value/{1}'.format(topic, declareValue.tag), payload, qos=0, retain=True)

def declareValues2Mqtt(deviceSettings:DeviceSettings, mqttSettings:MqttSettings, declareValues:[DeclareValue]) -> bool:
  def onDeclareMqttConnect(client, userdata, flags, rc):
    if rc == 0:
      try:
        if mqttSettings.isHA:
          declareValues2HAMqtt(client, deviceSettings, declareValues)
        else:
          declareValues2DefaultMqtt(client, deviceSettings, declareValues)
      except Exception as excp:
        print('Failed to send declare : ' + str(excp))
      try:
        client.loop_stop()
        client.disconnect()
      except:
        pass
    else:
      print('Failed to connect for declare, return code {0}'.format(rc))
  client = buildMqttClient(mqttSettings)
  client.on_connect = onDeclareMqttConnect
  client.loop_start()
  client.connect(mqttSettings.hostname, mqttSettings.port)
  return True

def declareValues(settings:Settings) -> bool:
  global declareTstamp

  if settings.device is None or not settings.device.isSet():
    return False

  if declareTstamp is not None and ( time.time() - declareTstamp ) <= 12*3600:
    return False

  declareValues:[DeclareValue] = []
  declareValues.append(DeclareValue('cpu temperature', '°C', 'cpuTempC'))
  declareValues.append(DeclareValue('cpu frequency', 'GHz', 'cpuFreqGHz'))
  declareValues.append(DeclareValue('memory total', 'kB', 'memTotalKB'))
  declareValues.append(DeclareValue('memory free', 'kB', 'memFreeKB'))
  declareValues.append(DeclareValue('memory available', 'kB', 'memAvailKB'))
  declareValues.append(DeclareValue('swap total', 'kB', 'swapTotalKB'))
  declareValues.append(DeclareValue('swap free', 'kB', 'swapFreeKB'))

  wait:bool = False
  for mqtt in settings.mqtts:
    if declareValues2Mqtt(settings.device, mqtt, declareValues):
      wait = True

  declareTstamp = time.time()
  if wait:
    time.sleep(5)

  return True

def sendValues2Mqtt(values:Values, deviceSettings:DeviceSettings, mqttSettings:MqttSettings) -> bool:
  if not settings.isSet():
    return False
  def onValuesMqttConnect(client, userdata, flags, rc):
    if rc == 0:
      try:
        client.publish(buildValuesTopic(deviceSettings.group, deviceSettings.serial), json.dumps(values, cls=PeniJsonEncoder))
      except Exception as excp:
        print('Failed to send values : ' + str(excp))
      try:
        client.loop_stop()
        client.disconnect()
      except:
        pass
    else:
      print('Failed to connect for send, return code {0}'.format(rc))
  client = buildMqttClient(mqttSettings)
  client.on_connect = onValuesMqttConnect
  client.loop_start()
  client.connect(mqttSettings.hostname, mqttSettings.port)
  return True

def sendValues(values:Values, settings:Settings) -> bool:
  if settings.mqtts and len(settings.mqtts) > 0:
    wait:bool = False
    for mqtt in settings.mqtts:
      if sendValues2Mqtt(values, settings.device, mqtt):
        wait = True

    if wait:
      time.sleep(5)
  else:
    dispValues(values)

  return True

def readAndSendValues():
  global settings
  values:Values = readValues()
  declareValues(settings)
  sendValues(values, settings)


#
# Main (sort of)
#

argParser = argparse.ArgumentParser(prog='penistats', description='Penguin Stats')
argParser.add_argument('--set', default='penistats.conf', help='settings file path')
args = argParser.parse_args()

declareTstamp:int = None

settings:Settings = readSettings(args.set if args.set is not None else 'penistats.conf')
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
