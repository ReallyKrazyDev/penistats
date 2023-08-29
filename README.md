# penistats
Penguin Statistics

This software is dedicated to retrieve some system data (CPU temp and fequency, available memory, ...) and send them to local/remote host(s)

Currently only MQTT is accepted as host

It is tested on a Raspberry Pi 3B running Raspberry Pi OS, and data are sent in homeassistant format

It should work on regular Debian-based Linux (with some limitations) and with some changes on any Linux

## Settings file

If no settings file is provided then penistats.conf will be used.
Use --set to provide path to your own settings file path

If no settings file is found then penistats will run once and display the values.

Settings file may contain 3 parts : "device", "schedule", "mqtts"

### "device"

Describes the device.
On Raspberry PI it is optional.

```
"device": {
  "group" : group containing the device, 'penistats' if missing, will be used to create MQTT topic
  "serial" : serial of the device, must be unique accross group's devices, will be used to create MQTT topic
  "model" : model of the device
  "manufacturer" : manufacturer of the device
  "version" : software version of the device
}
```

### schedule

Scheduler, if missing then it will run only once

```
"schedule": {
  "every": {
    "minutes" : read and send values every X minutes
  }
}
```

### "mqtts"

Array of MQTT destination(s)

For each MQTT we have :
```
"mqtts": [
  {
    "hostname": hostname of the broker,
    "port": port of the broker,
    "username": username (if needed),
    "password": password (if needed),
    "caCerts": path to broker's CA certificates (if needed),
    "isHA": if true then use Home Assistant format
  }
]
```

### Full content
```
{
  "device": {
    "group": "...",
    "serial": "...",
    "model": "...",
    "manufacturer": "...",
    "version": "..."
  },
  "schedule": {
    "every": {
      "minutes": 10
    }
  },
  "mqtts": [
    {
      "hostname": "...",
      "port": 1883,
      "username": "...",
      "password": "...",
      "caCerts": "...",
      "isHA": true
    }
  ]
}
```

## Suggestion to run on boot

### Debian-based

Let's assume penistats is located in /opt/penistats

1) run ```sudo crontab -e```
2) add ```@reboot         /usr/bin/python3 /opt/pistats/pistats.py --set /opt/pistats/pistats.conf```
3) save and reboot 
