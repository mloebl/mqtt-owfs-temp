# mqtt-owfs-temp

This script will read a list of hosts, ports and devices from /etc/mqtt-owfs-temp/devices.csv, query the devices from the relevant owserver instance, and publish the results over MQTT

INSTALL
=================
```
sudo apt-get install git python-ow python-pip

sudo pip install setuptools
sudo pip install setproctitle
sudo pip install paho-mqtt

mkdir /etc/mqtt-owfs-temp/
git clone git://github.com/mloebl/mqtt-owfs-temp.git /usr/local/mqtt-owfs-temp/
cp /usr/local/mqtt-owfs-temp/mqtt-owfs-temp.cfg.example /etc/mqtt-owfs-temp/mqtt-owfs-temp.cfg
cp /usr/local/mqtt-owfs-temp/mqtt-owfs-temp.init /etc/init.d/mqtt-owfs-temp
update-rc.d mqtt-owfs-temp defaults
cp /usr/local/mqtt-owfs-temp/mqtt-owfs-temp.default /etc/default/mqtt-owfs-temp
```

Edit /etc/default/mqtt-owfs-temp and /etc/mqtt-owfs-temp/mqtt-owfs-temp.cfg to suit

`/etc/init.d/mqtt-owfs-temp start`

SERVER
=================

If you are interested in running a 1-wire owserver instance on a Raspberry Pi, the original author has written a short guide here http://lodge.glasgownet.com/2012/11/14/owfs-server-on-the-raspberry-pi/
