procCheck.py
============

You can read the full post here: [Monitor processes with Telegraf/InfluxDB/Kapacitor](http://tech.aabouzaid.com/2016/08/monitoring-processes-with-telegraf-influxdb-kapacitor-python.html).

Intro.
------
Python script checks list of processes based on process name or pattern and print status in InfluxDB format.

This script provides "blackbox" monitoring for processes, and with Telegraf (exec plugin) you can store processes' status in InfluxDB then process that data and get alerts via Kapacitor using dead man's switch (alerts will be sent if no data for any of processes).

I created this script quickly till procstat bug is fixed! It reports wrong PIDs, because it caches the PIDs. (I'd like to fix it but since I don't really "Go" language, I cannot really help).


How doest it work?
------------------
Unlike "procstat" which uses "pgrep", I tried to make this script pure Python. And even I didn't use an external module like "psutil" which totally fits here (but also it doesn't part of default system packages and you need to install it). But since I don't need most of its features and this script will run on Linux systems only, so that's ok for me right now.

You can monitor process based on "name" (i.e exec/bin name) and/or using a pattern! So it will work with Java apps too! In java apps (e.g. ZooKeeper, Kafka, etc), the binary name for all processes is just "java", and the real application shows as argument for that java process.


How to use it.
--------------
In "procList.yml" you will find 2 sections. First one is "byName" for procs name, and second one is "byPattern" in case you want to monitor a process based on its arguments.

```
byName:
  - sshd
  - firefox

byPattern:
  nm: "NetworkManager"
```

Output example:

```
procCheck,host=LinuxRocks,process_name=nm,exe=dnsmasq,pid=7962 host=LinuxRocks,process_name="nm",exe="dnsmasq",pid=7962,pattern="NetworkManager"
procCheck,host=LinuxRocks,process_name=nm,exe=NetworkManager,pid=7608 host=LinuxRocks,process_name="nm",exe="NetworkManager",pid=7608,pattern="NetworkManager"
procCheck,host=LinuxRocks,process_name=nm,exe=dhclient,pid=11079 host=LinuxRocks,process_name="nm",exe="dhclient",pid=11079,pattern="NetworkManager"
procCheck,host=LinuxRocks,process_name=firefox,exe=firefox,pid=4014 host=LinuxRocks,process_name="firefox",exe="firefox",pid=4014,pattern=""
```

Telegraf config.
----------------
Here is a config file to make it works with Telegraf via "exec" plugin.


Kapacitor script.
-----------------
With Kapacitor (which is for time-series data processing, alerting, and anomaly detection) you can get alerts when any process is stopped.

This TICK script uses dead man's switch, so you will get an alert when the monitored process is not there anymore.

It makes a batch queries (I think we don't need "stream" here), and if there is no data for any of monitored processes it will send and alert via "VictorOps".

Of course you can uses whatever you use for altering, just check supported services in alerting. And if it's not there you can consume that data using "HTTPOut".

About.
------
* **By:** Ahmed M. AbouZaid ([tech.aabouzaid.com](http://tech.aabouzaid.com/)).
* **Version:** v0.1 - August 2016.
* **License:**  GPL v2.0 or later.
