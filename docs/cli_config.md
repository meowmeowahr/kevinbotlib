# Configuration

The set of configuration commands makes it easier to set and retrieve configuration options.

## echo

The `echo` tool will output the raw configuration data in the original YAML format.

It can be invoked with the following:

```console
kevinbot config echo [OPTIONS]
```

### Example Usage

* Outputing user configuration
    ```console
    kevinbot config echo
    ```
* Outputing system configuration
    ```console
    kevinbot config echo --system
    ```

### Options

| Argument           | Type  | Description                                    |
| ------------------ | ----- | ---------------------------------------------- |
| `--config`         | STR   | Manually defined configuration path            |
| `--system`         | FLAG  | Use system configuration path                  |
| `--user`           | FLAG  | Use user configuration path                    |
| `-h` *or* `--help` | FLAG  | Output help information                        |

## get

The `get` tool will return a value or group of values for the configurations. Will return a single value or JSON for a group of values.

It can be invoked with the following:

```console
kevinbot config get [OPTIONS] KEYS
```

### Example Usage

* Retrieving MQTT Port
    ```console
    kevinbot config get mqtt.port
    ```
* Retrieving Full MQTT Config (JSON)
    ```console
    kevinbot config get mqtt
    ```
* Retrieving Entire Config (JSON)
    ```console
    kevinbot config get .
    ```

### Options

| Argument           | Type  | Description                                    |
| ------------------ | ----- | ---------------------------------------------- |
| `--config`         | STR   | Manually defined configuration path            |
| `--system`         | FLAG  | Use system configuration path                  |
| `--user`           | FLAG  | Use user configuration path                    |
| `-h` *or* `--help` | FLAG  | Output help information                        |

## set

The `set` tool will set a single config value.

It can be invoked with the following:

```console
kevinbot config set [OPTIONS] KEYS VALUE
```

### Example Usage

* Setting MQTT Port
    ```console
    kevinbot config set mqtt.port 2883 --int
    ```
* Setting MQTT Host
    ```console
    kevinbot config set mqtt.host "kevinbotv3.local" --str
    ```

### Options

| Argument           | Type  | Description                                    |
| ------------------ | ----- | ---------------------------------------------- |
| `--config`         | STR   | Manually defined configuration path            |
| `--system`         | FLAG  | Use system configuration path                  |
| `--user`           | FLAG  | Use user configuration path                    |
| `--int`            | FLAG  | Set value as an integer                        |
| `--str`            | FLAG  | Set value as a string (default)                |
| `--bool`           | FLAG  | Set value as a boolean                         |
| `--float`          | FLAG  | Set value as a floating-point                  |
| `-h` *or* `--help` | FLAG  | Output help information                        |