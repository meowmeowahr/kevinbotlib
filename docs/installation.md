# Installation

!!! info
    KevinbotLib requires Python 3.10 or newer.

## System Dependencies

If you want to use the TTS (Text-to-Speech) extra on Linux, you must install PortAudio

* Debian/Ubuntu/RpiOS

```console
sudo apt install portaudio19-dev
```

## Install with pip

Run the following in a virtual environment for the base version.
```console
pip install kevinbotlib
```

Run the following if you want to install the TTS (Text-to-Speech) extra.
```console
pip install kevinbotlib[tts]
```

## Install with pipx

!!! tip
    pipx installation will only install command-line tools and the KevinbotLib Server.
    Use the regular pip installation if you want any development tools.

1. Install pipx [here](https://pipx.pypa.io/latest/installation/)
2. Install KevinbotLib

    Run the follwoing:
    ```console
    pipx install kevinbotlib
    ```
