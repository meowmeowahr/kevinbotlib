# MQTT Publisher

The MQTT Publisher command line tool provides an easy way to publish to MQTT topics. 
It can publish messages once, or at a set interval and count.

It can be invoked with the following:

```console
kevinbot pub [OPTIONS] TOPIC MESSAGE
```

## Options

| Argument         | Type  | Description                                    |
| ---------------- | ----- | ---------------------------------------------- |
| `--count`        | INT   | Number of times to publish message             |
| `--interval`     | FLOAT | Interval between publishing messages (seconds) |
| `--qos`          | INT   | MQTT Quality-of-Service                        |
| `--retain`       | FLAG  | MQTT Retain Message                            |
| `-h` or `--help` | FLAG  | Output help information                        |