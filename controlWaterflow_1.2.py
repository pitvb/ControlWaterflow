# Ensuring that the water softener is setting back to "no waterflow" after backwash
# if water does flow for a too long period the application will switch "off" power and
# switch it "on" again for a restart.
# The relais does work with "reverse logic" meaning "relais on = power off" and vice versa to ensure that
# there is a high probability that the power is on if the application fails.
# V 1.0 Initial Version
# V 1.1 7.9.2020 - Minor updates for message sending
# V 1.2 16.10.2020 - Information about application status (alive) added
# 
# Peter Bosch 6.9.2020
#
# Credits to my son Dominic Bosch, he did help with a lot of great input (e.g. use pushover for messages)
# and code review

import RPi.GPIO as GPIO;
import time;
import datetime;
import mariadb;
import sys;
import http.client, urllib;
import atexit;
import socket;

from myconfig import *;

#Getting the Hostname for reporting
sHostname = socket.gethostname();

#Relais Output GPIO Port
iRelaisOut = 23;

#Switch Input GPIO Port
iSwitchIn = 24;

# Maximal amount of time a backwash takes (in seconds)
backWash = 180;
#backWash = 20; # for testing purposes

# Minimum time a  backwash needs
minBackWash = 60;

# Amount of time we monitor if water does flow
waitTime = 20;
#waitTime = 5; # for testing purposes

# Minimal amount of time water has to flow within defined waitTime
minTime = 5;
#minTime = 2; # for testing purposes

# Number of reset before appliction ends
maxReset = 2;   
#maxReset = 1; # for testing purposes

# I would like to get a "application still running" every night
iOldHour = 0;
iHour = 0;
iReportHour = 4;

bIsReported = False;

class ExitHooks(object):
    def __init__(self):
        self.exit_code = None;
        self.exception = None;

    def hook(self):
        self._orig_exit = sys.exit;
        sys.exit = self.exit;
        sys.excepthook = self.exc_handler;

    def exit(self, code=0):
        self.exit_code = code;
        self._orig_exit(code);

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc;

hooks = ExitHooks();
hooks.hook();

def properExit():
    GPIO.cleanup();
    if hooks.exit_code is not None:
        strComment = "Application ended by sys.exit(" + str(hooks.exit_code) + ")";
        sendPush(strComment);
        print(strComment);
    elif hooks.exception is not None:
        strComment = "Application ended by exception (e.g. ctrl-C)";
        sendPush(strComment);
        print(strComment);
    else:
        strComment = "Application ended"
        sendPush(strComment);
        print(strComment);

atexit.register(properExit);

# Measuring if water is flowing for a minimum time within a given timeframe
def waterFlow(gpio_Port):
    startTime = time.process_time();
    flowTime = 0;
    intTime = time.process_time();
    while time.process_time() < (startTime + waitTime):
 # if GPIO.input(gpio_Port) =! 0: Changed locig from closed switch to open switch
        if GPIO.input(gpio_Port) == 0:
            flowTime = flowTime + (time.process_time() - intTime);
            intTime = time.process_time();
    if flowTime > 0:
        strComment = "Waterflow for " + str(flowTime) + " seconds";
        print(strComment);
    if flowTime > minTime:
        return True;
    else:
        return False;

# we will write some information to the Synology Maria db for documentation reason
def writeRecord(s_status, c_text):
    
 #   return True;    # FOR TESTING !
 
    # Connect to MariaDB Platform
    try:
        conn = mariadb.connect(
            user=mdbUser,
            password=mdbPassword,
            host=mdbHost,
            port=3307,
            database=mdbDatabase
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}");
        return False;
    # Get Cursor
    cur = conn.cursor();
    # insert information
    try:
        cur.execute("INSERT INTO waterflow (switch_status,comment) VALUES (?, ?)", (s_status,c_text)) 
    except mariadb.Error as e:
        print("Error: mariadb");
    conn.commit();
#    print(f"Last Inserted ID: {cur.lastrowid}");
    # Close Connection
    conn.close();
    return True;

# using PusOver to send status messages to NATEL ;-)
def sendPush(s_text):
    
#    return True; # FOR TESTING !
    
    conn = http.client.HTTPSConnection("api.pushover.net:443");
    conn.request("POST", "/1/messages.json",
      urllib.parse.urlencode({
        "token": puoToken,
        "user": puoUser,
        "message": s_text,
      }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()
    return True;

def sendInfo(s_text):
	s_text = "From " + sHostname + " -> " + s_text;
	sendPush(s_text);
	writeRecord(0, s_text);
	print(s_text);

####################### APPLICATION START

now=datetime.datetime.today();
strDate = now.strftime('%Y-%m-%d');
strTime = now.strftime('%H:%M');
sendInfo("Application control waterflow started at " + strTime + " on " + strDate);

# Select GPIOs by GPIO Number (not Pin)
GPIO.setmode(GPIO.BCM);
GPIO.setwarnings(False);

GPIO.setup(iRelaisOut, GPIO.OUT);
GPIO.setup(iSwitchIn, GPIO.IN);

while True:
# At iReportHour, send a push note that the application is still running
    iHour = datetime.datetime.now().hour;
    if iOldHour != iHour:
        iOldHour = iHour;
        if bIsReported == False:
            if iHour == iReportHour:
                now=datetime.datetime.today();
                strDate = now.strftime('%Y-%m-%d');
                strTime = now.strftime('%H:%M');
                sendInfo("Application controlWaterflow still alive at " + strTime + " on " + strDate);
                bIsReported = True;
        else:
            if iHour != iReportHour:
                bIsReported = False;

# See if water is flowing
# all the checks about how long water was flowing is because sometimes a small amount of water is running through the tube
    flowStart = time.time();
    backWashStarted = False;
    while waterFlow(24) == True:
        backWashStarted = True;
        now=datetime.datetime.today();
        strDate = now.strftime('%Y-%m-%d');
        strTime = now.strftime('%H:%M');
        strComment = "\n" + strDate + " : " + strTime;
        print(strComment);
        strComment = "Calculating Waterflow : " + str(time.time()-flowStart) + "\n"; 
        print(strComment);
        writeRecord("0", strComment);
        if time.time()-flowStart > backWash:
            resetCounter = 0;
            while resetCounter != -1:
                sendInfo("Restarting device after : " + str(time.time()-flowStart));
                GPIO.output(23, GPIO.HIGH);
                print("Switch relais to -> On == Power off");
                time.sleep(10);
                GPIO.output(23, GPIO.LOW);
                print("Switch relais to -> Off == Power on");
                time.sleep(backWash);           #Wait until machine has restarted
                now=datetime.datetime.today();
                strDate = now.strftime('%Y-%m-%d');
                strTime = now.strftime('%H:%M');
                if waterFlow(24) == True:       #Still not ok
                    if resetCounter <= (maxReset -1):   # Counter does start with 0
                        sendInfo("Restart number " + str(resetCounter + 1) + " not successful at : " + strTime + " on : " + strDate);
                        resetCounter = resetCounter +1;
                    else:
                        sendInfo("Maximum number of restarts reached at : " + strTime + " on : " + strDate + " -> APPLICATON HALTS !");
                        sys.exit(1);
                else:
                    sendInfo("Restart successful at : " + strTime + " on : " + strDate);
                    resetCounter = -1;
    if backWashStarted == True and (time.time() - flowStart) >= minBackWash:     # backwash finished in time
        now=datetime.datetime.today();
        strDate = now.strftime('%Y-%m-%d');
        strTime = now.strftime('%H:%M');
        sendInfo("Backwash for " + str(int(time.time() - flowStart)) + " seconds successful at : " + strTime + " on : " + strDate);
