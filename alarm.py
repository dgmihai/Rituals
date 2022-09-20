from datetime import date, datetime
import getopt
import json
import subprocess
import sys
from time import sleep, time

import logging

import config as c

# ==================================================================================================
# ~SETTING & TRACKING HOURGLASS ALARMS~
# ==================================================================================================

def apftime(d):
    return datetime.strftime(d, '%I:%M %p')

def fdate(d):
    return datetime.strftime(d, '%m/%d/%y')

def cmptftime(d):
    return datetime.strftime(d, '%m/%d/%y %I:%M %p')

def _read():
    with open(c.FILE_SET_ALARMS) as f:
        try:
            set_alarms = json.load(f)
        except:
            set_alarms = ["X"]
    logging.debug(set_alarms)

def _run(cmd):
    completed = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    return completed

def _set_hourglass_alarm(arg, d):
    t = apftime(d)
    cmd = arg + " " + get_alarm_title() + " " + t
    try:
        ret = run(c.PATH_HOURGLASS + cmd)
        if ret.returncode != 0:
            logging.error("Failed to set Hourglass alarm: %s", ret.stderr)
        else:
            logging.info("Hourglass alarm set:" + cmd)
            _record_set_alarm(d)
    except Exception as ex:
        raise ex

def _get_alarm_title():
    return "MEDITATE"

def _clean_set_alarms(d):
    str_d = fdate(d)
    if set_alarms[0] != str_d:
        logging.info("Clearing set alarms")
        set_alarms.clear()
        set_alarms.append(str_d)

def _record_set_alarm(d):
    t = apftime(d)
    set_alarms.append(t)

def _was_set_alarm(d):
    for alarm in set_alarms:
        if alarm == apftime(d):
            return True
    return False

def _save_set_alarms():
    f = open(FILE_SET_ALARMS, "w")
    json.dump(set_alarms, f)
    f.close()

def sync():
    d = datetime.now()
    start_hour = max(c.DAY_HOUR_START, d.hour)
    end_hour = c.DAY_HOUR_END+1
    if end_hour < start_hour:
        logging.warn("End hour " + end_hour + "is earlier than start hour " + start_hour)
    clean_set_alarms(d)
    for hour in range(start_hour+1, c.DAY_HOUR_END+1):
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