import json
from json import JSONDecodeError
from jsonschema import validate
import requests
from requests.structures import CaseInsensitiveDict

from jsonmerge import Merger
import logging

import config as c

checklists = []
todoist = ""

def _read():
    """Reads Todoist data from local file
    """
    with open(c.FILE_TODOIST) as f:
        try:
            logging.debug("Reading from " + c.FILE_TODOIST)
            _set(json.load(f), r=True)
        except (JSONDecodeError):
            logging.debug('Todoist local data empty')

def _set(data, r=False):
    """Overwrites Todoist data locally and writes to file

    Args:
    data -- JSON Object to overwrite with
    r -- If this comes from read, to avoid unnecessary I/O
    """
    global todoist
    todoist = data
    if not r:
        _write(data)
    logging.debug("Sync token: " + todoist['sync_token'])

def _write(data):
    """Writes Todoist data to file

    Args:
    data -- JSON Object to write
    """
    with open(c.FILE_TODOIST, 'w') as f:
        f.write(json.dumps(data))

def _request(sync_token):
    """Pulls data from Todoist

    Args:
    sync_token -- either * for a full pull, or a sync_token to get incremental
        changes since last token

    Returns:
    Response object
    """
    headers = CaseInsensitiveDict()
    headers["Authorization"] = "Bearer " + c.TODOIST_API_TOKEN
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    data = 'sync_token=' \
        + sync_token \
        + '&resource_types=[' \
            + '"projects", ' \
            + '"items", ' \
            + '"sections"]'

    r = requests.post(c.TODOIST_API, headers=headers, data=data)
    if r.status_code != 200:
        logging.error("Error on Todoist sync!")
        logging.error(headers)
        logging.error(data)
        logging.error(r.text)
        r.raise_for_status()
    return r

# Returns merged
def _merged_json(base, head):
    """JSON merge Todoist data

    Args:
    base -- the fully synched Todoist data
    head -- incremental changes

    Returns:
    JSON Object of merged data
    """
    with open(c.FILE_TODOIST_SCHEMA) as f:
        schema = json.load(f)
    validate(instance=base, schema=schema)
    validate(instance=head, schema=schema)
    logging.debug("Merging...")
    for table in ["items", "sections", "projects"]:
        for base_item in reversed(base[table]):
            for head_item in reversed(head[table]):
                if base_item["id"] == head_item["id"]:
                    head[table].remove(head_item)
                    base[table].remove(base_item)
                    if head_item["is_deleted"]:
                        logging.debug(
                            "Deleting from " + table + ": " + base_item["content"])
                    else:
                        logging.debug(
                            "Overwritting in " + table + ": " + head_item["content"])
                        base[table].append(head_item)
                    break
            if len(head[table]) == 0:
                break
        for head_item in head[table]:
            logging.debug("Adding to " + table + ": " + head_item["content"])
            base[table].append(head_item)
    if not c.TEST:
        # Don't update the sync token if we are testing
        base['sync_token'] = head['sync_token']
    return base

def _get_checklists():
    # Set active tracked checklists
    f = open(c.FILE_CHECKLISTS, "r")
    for line in f:
        checklists.append(line)
    f.close()

def sync():
    """JSON merge Todoist data

    Args:
    base -- the fully synched Todoist data
    head -- incremental changes

    Returns:
    JSON Object of merged data
    """
    _read()
    if todoist == None or todoist == "" or c.FORCE_SYNC:
        logging.debug('Starting full Todoist sync')
        r = _request('*')
        _write(r.json())
    else:
        logging.debug('Starting incremental Todoist sync: ' + todoist['sync_token'])
        r = _request(todoist['sync_token'])
        _set(_merged_json(todoist, r.json()))