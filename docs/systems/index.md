# Systems

## What is a System?

A system is a root component that is used in KevinbotLib. 

In the case of serial communication, KevinbotLib will have to connect to it separately from another system.

When using MQTT communication, you will need to pass in the [Kevinbot system](kevinbot.md) (with a non-Kevinbot system), or spin up an MQTT client (with a Kevinbot system).

A system will contain it's own state management, connection system, and [subsystems](/subsystems).