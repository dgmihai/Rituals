from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, datetime
from time import sleep
from time import time
from wakepy import set_keepawake, unset_keepawake

import json
import logging
import subprocess

HOURGLASS = "C:\Program` Files` `(x86`)\Hourglass\Hourglass.exe"

# ==================================================================================================
# ~DEFINES~
# ==================================================================================================

DAY_HOUR_START = 9
DAY_HOUR_END = 21

FILE_SET_ALARMS = 'set_alarms'
FILE_LOG = 'orchestra_log'

# ==================================================================================================
# ~LOGGING~
# ==================================================================================================

# DO NOT USE print() - Will not output to log file
# To file
#logging.basicConfig(filename=FILE_LOG, encoding='utf-8', level=logging.DEBUG, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%y %I:%M:%S %p %z')

# To stream
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%m/%d/%y %I:%M:%S %p %z')

logging.info("==================== STARTING ====================")

# ==================================================================================================

sched = BackgroundScheduler()
set_keepawake(keep_screen_awake=False)

f = open(FILE_SET_ALARMS, "r")
try:
    set_alarms = json.load(f)
except:
    set_alarms = ["X"]
f.close()
logging.info(set_alarms)

# ==================================================================================================
# ~SETTING & TRACKING HOURGLASS ALARMS~
# ==================================================================================================

def run(cmd):
    completed = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    return completed

def set_hourglass_alarm(arg, d):
    t = apftime(d)
    cmd = arg + " " + get_alarm_title() + " " + t
    try:
        ret = run(HOURGLASS + cmd)
        if ret.returncode != 0:
            logging.error("Failed to set Hourglass alarm: %s", ret.stderr)
        else:
            logging.info("Hourglass alarm set:" + cmd)
            record_set_alarm(d)
    except Exception as ex:
        raise ex

def get_alarm_title():
    return "MEDITATE"

def apftime(d):
    return datetime.strftime(d, '%I:%M %p')

def fdate(d):
    return datetime.strftime(d, '%m/%d/%y')

def cmptftime(d):
    return datetime.strftime(d, '%m/%d/%y %I:%M %p')

def clean_set_alarms(d):
    str_d = fdate(d)
    if set_alarms[0] != str_d:
        logging.info("Clearing set alarms")
        set_alarms.clear()
        set_alarms.append(str_d)

def record_set_alarm(d):
    t = apftime(d)
    set_alarms.append(t)

def was_set_alarm(d):
    for alarm in set_alarms:
        if alarm == apftime(d):
            return True
    return False

def save_set_alarms():
    f = open(FILE_SET_ALARMS, "w")
    json.dump(set_alarms, f)
    f.close()

# ==================================================================================================
# ~MAIN~
# ==================================================================================================

d = datetime.now()
start_hour = max(DAY_HOUR_START, d.hour)
end_hour = DAY_HOUR_END+1
if end_hour < start_hour:
    logging.warn("End hour " + end_hour + "is earlier than start hour " + start_hour)
clean_set_alarms(d)
for hour in range(start_hour+1, DAY_HOUR_END+1):
    d = d.replace(hour=hour, minute=0, second=0, microsecond=0)
    if not was_set_alarm(d):
        set_hourglass_alarm(""
            + " --sound \"Normal beep\""
            + " --prompt-on-exit off"
            + " --always-on-top on"
            + " --title ",
            d)
    else:
        logging.debug("Alarm at " + apftime(d) + " already set.")
    save_set_alarms()
    #
    #sched.add_job(job, 'cron', hour=9,
    #              end_time=17

unset_keepawake()

logging.info("==================== COMPLETE ====================")