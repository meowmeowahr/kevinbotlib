# Jinja2 template for systemd service that runs in user mode --user
ROBOT_SYSTEMD_USER_SERVICE_TEMPLATE = """
[Unit]
Description=KevinbotLib Robot Service
After=network.target cns-server.service
Requires=cns-server.service

[Service]
Type=simple
WorkingDirectory={{ working_directory }}
ExecStart=/bin/bash -c "{{ exec }}; ret=$?; if [ $ret -eq 0 ] || [ $ret -eq 64 ] || [ $ret -eq 65 ]; then exit 0; else exit $ret; fi"
Restart=on-failure
RestartSec=5
KillSignal=SIGUSR1
Environment='DEPLOY=true'

[Install]
WantedBy=default.target
"""

CNS_SYSTEMD_USER_SERVICE_TEMPLATE = """
[Unit]
Description=KevinbotLib CNS Server Service
After=network.target

[Service]
Type=simple
WorkingDirectory={{ working_directory }}
ExecStart={{ exec }}
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM

[Install]
WantedBy=default.target
"""
