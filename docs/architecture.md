# Architecture

```mermaid
flowchart TD
 subgraph s1["KevinbotLib Server"]
        n5["KevinbotLib<br>Direct Serial"]
        n9["XBee Interface"]
  end
    n3["MQTT API Mode"] <--> n4["MQTT Broker"]
    n4 <--> s1
    n5 --> n6["Kevinbot<br>Hardware"]
    n2["Direct Serial"] --> n6
    n9 <--> n5
    n9 --> n4
    n10["OR"] --> n11["Direct Serial Mode<br>"] & n12["MQTT Mode"]
    n1["KevinbotLib"] --> n10
    n11 --> n2
    n12 --> n3
    n3@{ shape: rect}
    n4@{ shape: rect}
    n6@{ shape: rect}
    n2@{ shape: rect}
    n10@{ shape: diam}
    n11@{ shape: text}
    n1@{ shape: rect}
    n12@{ shape: text}
```