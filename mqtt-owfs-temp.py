#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

__author__ = "Kyle Gordon"
__copyright__ = "Copyright (C) Kyle Gordon"
# Modified BY Mike Loebl 

import os
import logging
import signal
import socket
import time
import sys

import paho.mqtt.client as paho
import ConfigParser
import ow
import setproctitle

from datetime import datetime, timedelta

# Read the config file
config = ConfigParser.RawConfigParser()
config.read("/etc/mqtt-owfs-temp/mqtt-owfs-temp.cfg")

# Use ConfigParser to pick out the settings
DEBUG = config.getboolean("global", "debug")
LOGFILE = config.get("global", "logfile")
MQTT_HOST = config.get("global", "mqtt_host")
MQTT_PORT = config.getint("global", "mqtt_port")
MQTT_SUBTOPIC = config.get("global", "MQTT_SUBTOPIC")
MQTT_TOPIC = "/raw/" + socket.getfqdn() + MQTT_SUBTOPIC
MQTT_USERNAME = config.get("global", "MQTT_USERNAME")
MQTT_PASSWORD = config.get("global", "MQTT_PASSWORD")
METRICUNITS = config.get("global", "METRICUNITS")

POLLINTERVAL = config.getint("global", "pollinterval")
DEVICESFILE = config.get("global", "devicesfile")

owserver = "localhost"

APPNAME = "mqtt-owfs-temp"
PRESENCETOPIC = "clients/" + socket.getfqdn() + "/" + APPNAME + "/state"
setproctitle.setproctitle(APPNAME)
client_id = APPNAME + "_%d" % os.getpid()

mqttc = paho.Client()

LOGFORMAT = '%(asctime)-15s %(message)s'

if DEBUG:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.DEBUG,
                        format=LOGFORMAT)
else:
    logging.basicConfig(filename=LOGFILE,
                        level=logging.INFO,
                        format=LOGFORMAT)

logging.info("Starting " + APPNAME)
logging.info("INFO MODE")
logging.debug("DEBUG MODE")

def celsiusCon(farenheit):
   return (farenheit - 32)/(1.8)
def farenheitCon(celsius):
   return ((celsius*(1.8)) + 32)

# All the MQTT callbacks start here


def on_publish(mosq, obj, mid):
    """
    What to do when a message is published
    """
    logging.debug("MID " + str(mid) + " published.")


def on_subscribe(mosq, obj, mid, qos_list):
    """
    What to do in the event of subscribing to a topic"
    """
    logging.debug("Subscribe with mid " + str(mid) + " received.")


def on_unsubscribe(mosq, obj, mid):
    """
    What to do in the event of unsubscribing from a topic
    """
    logging.debug("Unsubscribe with mid " + str(mid) + " received.")


def on_connect(mosq, obj, result_code):
    """
    Handle connections (or failures) to the broker.
    This is called after the client has received a CONNACK message
    from the broker in response to calling connect().
    The parameter rc is an integer giving the return code:

    0: Success
    1: Refused – unacceptable protocol version
    2: Refused – identifier rejected
    3: Refused – server unavailable
    4: Refused – bad user name or password (MQTT v3.1 broker only)
    5: Refused – not authorised (MQTT v3.1 broker only)
    """
    logging.debug("on_connect RC: " + str(result_code))
    if result_code == 0:
        logging.info("Connected to %s:%s", MQTT_HOST, MQTT_PORT)
        # Publish retained LWT as per
        # http://stackoverflow.com/q/97694
        # See also the will_set function in connect() below
        mqttc.publish(PRESENCETOPIC, "1", retain=True)
        process_connection()
    elif result_code == 1:
        logging.info("Connection refused - unacceptable protocol version")
        cleanup()
    elif result_code == 2:
        logging.info("Connection refused - identifier rejected")
        cleanup()
    elif result_code == 3:
        logging.info("Connection refused - server unavailable")
        logging.info("Retrying in 30 seconds")
        time.sleep(30)
    elif result_code == 4:
        logging.info("Connection refused - bad user name or password")
        cleanup()
    elif result_code == 5:
        logging.info("Connection refused - not authorised")
        cleanup()
    else:
        logging.warning("Something went wrong. RC:" + str(result_code))
        cleanup()


def on_disconnect(mosq, obj, result_code):
    """
    Handle disconnections from the broker
    """
    if result_code == 0:
        logging.info("Clean disconnection")
    else:
        logging.info("Unexpected disconnection! Reconnecting in 5 seconds")
        logging.debug("Result code: %s", result_code)
        time.sleep(5)


def on_message(mosq, obj, msg):
    """
    What to do when the client recieves a message from the broker
    """
    logging.debug("Received: " + msg.payload +
                  " received on topic " + msg.topic +
                  " with QoS " + str(msg.qos))
    process_message(msg)


def on_log(mosq, obj, level, string):
    """
    What to do with debug log output from the MQTT library
    """
    logging.debug(string)

# End of MQTT callbacks


def cleanup(signum, frame):
    """
    Signal handler to ensure we disconnect cleanly
    in the event of a SIGTERM or SIGINT.
    """
    logging.info("Disconnecting from broker")
    # Publish a retained message to state that this client is offline
    mqttc.publish(PRESENCETOPIC, "0", retain=True)
    mqttc.disconnect()
    mqttc.loop_stop()
    logging.info("Exiting on signal %d", signum)
    sys.exit(signum)

def connect():
    """
    Connect to the broker, define the callbacks, and subscribe
    This will also set the Last Will and Testament (LWT)
    The LWT will be published in the event of an unclean or
    unexpected disconnection.
    """
    logging.info("Connecting to %s:%s", MQTT_HOST, MQTT_PORT)
    # Set the Last Will and Testament (LWT) *before* connecting
    mqttc.will_set(PRESENCETOPIC, "0", qos=0, retain=True)

    if MQTT_USERNAME:
        logging.info("Found username %s", MQTT_USERNAME)
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        
    result = mqttc.connect(MQTT_HOST, MQTT_PORT, 60)
    if result != 0:
        logging.info("Connection failed with error code %s. Retrying", result)
        time.sleep(10)
        connect()

    # Define the callbacks
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_unsubscribe = on_unsubscribe
    mqttc.on_message = on_message
    if DEBUG:
        mqttc.on_log = on_log

    mqttc.loop_start()

def process_connection():
    """
    What to do when a new connection is established
    """
    logging.debug("Processing connection")


def process_message(mosq, obj, msg):
    """
    What to do with the message that's arrived
    """
    logging.debug("Received: %s", msg.topic)


def find_in_sublists(lst, value):
    for sub_i, sublist in enumerate(lst):
        try:
            return (sub_i, sublist.index(value))
        except ValueError:
            pass

    raise ValueError("%s is not in lists" % value)


class DevicesList():
    """
    Read the list of devices, and expand to include publishing state and current value
    """
    import csv
    datafile = open(DEVICESFILE, "r")
    datareader = csv.reader(datafile)
    data = []
    for row in datareader:
        data.append(row)


def main_loop():
    """
    The main loop in which we stay connected to the broker
    """
    while True:
	logging.debug(("DeviceList.data is : %s") % (str(DevicesList.data)))
	item = 0
	for device in DevicesList.data:
            # Split up list into relevant parts for reuse
            owserver = DevicesList.data[item][0]
            owport = DevicesList.data[item][1]
            owpath = DevicesList.data[item][2]
	    owsensortype =  DevicesList.data[item][3]

	    logging.debug(("Querying %s on %s:%s") % (owpath, owserver, owport))

            # FIXME owserver to come from a list of devices, and their respective servers
            ow.init(owserver + ":" + owport)
            ow.error_level(ow.error_level.fatal)
            ow.error_print(ow.error_print.stderr)
        
            # FIXME This possibly needs done for each 1-wire host
            # Split it off to the connect() function
            # Enable simultaneous temperature conversion
            ow._put("/simultaneous/temperature","1")
            
            try:
	        # Create sensor object
		logging.debug(("Trying sensor %s with type %s on %s:%s") % (owpath, owsensortype, owserver, owport))
        #        sensor = ow.Sensor(owpath)
         	sensordata = ow.owfs_get(owpath + "/" + owsensortype)       
	#	sensordata = getattr(sensor, owsensortype)

		if (owsensortype == 'temperature' and METRICUNITS == '0'):
		    sensordata = (farenheitCon(float(sensordata)))

		if (owsensortype == 'pressure'):
		    if ("B1-R1-A" in owpath):
		    	pressureoffset = ow.owfs_get(owpath + "/gain")
		    sensordata = (float(sensordata) + float(pressureoffset)) * 0.02953
		
		# if (owsensortype == 'illuminance'):                   
                    # if ("S3-R1-A" in owpath):
                    #   solaroffset = ow.owfs_get(owpath + "/gain")
		    #	sensordata = float(solaroffset) + float(sensordata)
			
                #Query sensor state
                logging.debug(("Sensor %s : %s") % (owpath, sensordata))
	        mqttc.publish(MQTT_TOPIC + owpath + "/" + owsensortype, sensordata)
	        item += 1
	    
	    except ow.exUnknownSensor:
	        logging.debug("Threw an unknown sensor exception for device %s. Continuing", owpath)
	        continue

	# We only want to poll the sensors occasionally... not every one second that's the default for mqttc.loop
	time.sleep(POLLINTERVAL)
    
# Use the signal module to handle signals
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# Connect to the broker and enter the main loop
connect()

# Try to start the main loop
try:
    main_loop()
except KeyboardInterrupt:
    logging.info("Interrupted by keypress")
    sys.exit(0)
