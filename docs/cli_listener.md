# MQTT Listener

The MQTT Listener command line tool provides an easy way to subscribe to MQTT topics. 
It subscribes to an MQTT topic, and logs messages to the terminal.

It can be invoked with the following:

```console
kevinbot listen [OPTIONS] TOPIC
```

## Options

| Argument | Type | Description             |
| -------- | ---- | ----------------------- |
| `--qos`  | INT  | MQTT Quality-of-Service |