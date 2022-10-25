import argparse
from datetime import date, datetime
import getopt
import json
import subprocess
import sys
from time import sleep, time

from apscheduler.schedulers.background import BackgroundScheduler
import logging
from wakepy import set_keepawake, unset_keepawake

import config as c
import todoist
import alarm

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

# ==================================================================================================
# ~MAIN~
# ==================================================================================================

parser = argparse.ArgumentParser()

parser.add_argument("-T", "--TEST", help = "Testing mode", action="store_true")
parser.add_argument("-a", "--Alarm", help = "Run alarm module", action="store_true")
parser.add_argument("-t", "--Todoist", help = "Run Todoist module", action="store_true")
parser.add_argument("-f", "--ForceSync", help = "Force a hard resync", action="store_true")

args = parser.parse_args()

if args.TEST:
    c.TEST = True
    c.FILE_TODOIST = 'data/todoist_test'
if args.ForceSync:
    c.FORCE_SYNC = True
if args.Alarm:
    alarm.sync()
if args.Todoist:
    todoist.sync()

unset_keepawake()

logging.info("==================== COMPLETE ====================")