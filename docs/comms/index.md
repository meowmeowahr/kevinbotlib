# KevinbotLib Communication System

The KevinbotLib Communication System is a powerful and flexible robot communication system using a Redis server.

Set/Get and Pub/Sub modes are supported by KevinbotLib.

Data is encoded and decoded into "Sendables," which contain the value alongside some metadata such as an expiration timeout.
Data is sent to a "topic," a `/`-separated path, where data can be retrieved or listened at.

## Set/Get

The set/get protocol uses the Redis database to allow for data retrieval at any time. 
The disadvantage is that subscribing or listening to data is not supported.

## Pub/Sub

The pub/sub protocol is designed for live listening and subscribing to topics. 
The disadvantage is that data cannot be retrieved at any time and must be listened for.

## Sendables

KevinbotLib includes Sendables for the built-in Python primitives, as well as Vision and Coord sendables.
Learn more about sendables [here](sendables.md)