from collections import OrderedDict
import copy
import json
from json import JSONDecodeError
from jsonschema import validate
import requests
from requests.structures import CaseInsensitiveDict

import logging

import config as c
import util

todoist = {}
schema = {}

def _read():
    """Reads Todoist data from local file
    """
    if not c.FORCE_SYNC:
        try:
            with open(c.FILE_TODOIST) as f:
                logging.debug("Reading from " + c.FILE_TODOIST)
                _set(json.load(f), r=True)
        except (JSONDecodeError):
            logging.warn("Todoist local data empty")
        except (FileNotFoundError):
            logging.warn("Todoist local data not present")

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
    logging.info("Local sync token: " + todoist['sync_token'])

def _write(data):
    """Writes Todoist data to file

    Args:
    data -- JSON Object to write
    """
    with open(c.FILE_TODOIST, 'w') as f:
        f.write(json.dumps(data, indent=c.INDENT))

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
def _merge_json(base, head):
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
    logging.info("Merging...")
    for table in ["items", "sections", "projects"]:
        if table == "items":
            name = "content"
        else:
            name = "name"
        for base_item in reversed(base[table]):
            for head_item in reversed(head[table]):
                if base_item["id"] == head_item["id"]:
                    head[table].remove(head_item)
                    base[table].remove(base_item)
                    if head_item["is_deleted"]:
                        logging.info(
                            "Deleting from " + table + ": " + base_item[name])
                    else:
                        logging.info(
                            "Overwritting in " + table + ": " + head_item[name])
                        base[table].append(head_item)
                    break
            if len(head[table]) == 0:
                break
        for head_item in head[table]:
            logging.info("Adding to " + table + ": " + head_item[name])
            base[table].append(head_item)
    base['sync_token'] = head['sync_token']
    _set(base)

def extract_field(body, prefix, delim="\n", stripOnlyPrefix=False):
    """Extract a particular field based on a string prefix from a description
    Also cleans up and removes field from the body based on delim
    
    Args:
    body -- String to search through
    prefix -- String of the name of the particular field we are looking for
    delim -- String of delimiter
    
    Returns:
    List of:
        0: String value of located field; empty if none found
        1: String of modified body with only the prefix removed
        2: String of modified body with the entire field removed"""
    ret = [ "", body, body ]
    prefix_idx = body.find(prefix)
    if prefix_idx != -1:
        start = prefix_idx + len(prefix)
        end = body.find(delim, start)
        if end == -1:
            end = len(body)
        # logging.debug("PREFIX, START, END: " + str(prefix_idx) + ", " + str(start) + ", " + str(end))
        ret[0] = body[start:end]
        ret[1] = body.replace(body[prefix_idx: start], "").strip()
        ret[2] = body.replace(body[prefix_idx: end], "").strip()
    return ret

def extract_act(task):
    """Extract and parse an act from a todoist task

    The checked prefixes can be found in rituals.schema.json

    Args:
    task -- Dict of Todoist task

    Returns:
    JSON Object of act"""
    ret = {
        'id':task['id'],
        'order':task['child_order'],
        'pt':task['parent_id'],
        'py':task['priority']
    }
    name = task['content']
    desc = task['description'].replace("'", "")
    # Time
    time_schema = schema['definitions']['time']['properties']
    expected, _, desc = extract_field(desc, time_schema['est']['prefix'])
    reminderActive, _, desc = extract_field(desc, time_schema['r']['prefix'])
    reminderExpired, _, desc = extract_field(desc, time_schema['rx']['prefix'])
    if expected or reminderActive or reminderExpired:
        ret['ti'] = {}
    if expected:
        ret['ti']['est'] = util.to_seconds(expected)
    if reminderActive:
        ret['ti']['r'] = util.to_seconds(reminderActive)
    if reminderExpired:
        ret['ti']['rx'] = util.to_seconds(reminderExpired)
    insert, _, _ = extract_field(name, schema['definitions']['act']['properties']['i']['prefix'], stripOnlyPrefix=True)
    if insert:
        ret['i'] = insert
        ret['ty'] = "hide"
    ret['heading'] = task['section_id']
    if desc != "":
        ret['d'] = desc
    ret['n'] = name
    return ret

def extract_acts():
    """Get the headings, rituals, and acts from local data
    Write it to a local file as well
    We are only checking the RITUALS project

    If an item matches a ritual name, it is the config for that ritual with defaults

    Sets full list of all ritual acts sorted by name as in rituals.schema.json
    """
    data = { 
        'sync':todoist['sync_token'],
        'acts':{},
        'hdgs':{}
    }
    logging.info("Extracting items from todoist file...")
    for project in todoist['projects']:
        if project['name'] == "RITUALS":
            # Populate list of categories from sections
            headings = []
            parents = {} # <id, [ids]>
            for section in todoist['sections']:
                if section['project_id'] == project['id']:
                    logging.debug("Section: " + section['name'])
                    # List of sections inside "RITUALS"
                    heading = {
                        'n':section['name'],
                        'id':section['id'],
                        'rs':[],
                        'order':section['section_order']
                    }
                    for i in range(len(headings)):
                        if heading['order'] < headings[i]['order']:
                            headings.insert(i, heading)
                            break
                    else:
                        headings.append(heading)
            for h in headings:
                del h['order']
                logging.debug("Heading: " + h['n'])
                data['hdgs'][h['id']] = h
                del h['id']
                validate(instance=h, schema=schema['definitions']['heading'])
            # Populate acts & rituals
            acts = data['acts'] # <id, act>
            insertQueue = {} # <name of ritual, actID>
            for item in todoist['items']:
                if item['project_id'] == project['id']:
                    # Item is in the RITUALS project
                    act = extract_act(item);
                    actID = act['id']
                    acts[actID] = act
                    if 'i' in act:
                        if not act['i'] in insertQueue:
                            insertQueue[act['i']] = []
                        insertQueue[act['i']].append(actID);
                    parentID = act['pt']
                    headingID = act['heading']
                    if not parentID:
                        # This ia a root-level ritual
                        del act['pt']
                        act['ty'] = "hide"
                        logging.debug("Ritual: " + act['n'])
                        headingRituals = data['hdgs'][headingID]['rs']
                        for i in range(len(headingRituals)):
                            if act['order'] < acts[headingRituals[i]]['order']:
                                headingRituals.insert(i, actID)
                        else:
                            headingRituals.append(actID)
                        if actID not in parents:
                            parents[actID] = []
                    else:
                        logging.debug("Act: " + act['n'])
                        if parentID not in parents:
                            parents[parentID] = []
                        for i in range(len(parents[parentID])):
                            if act['order'] < acts[parents[parentID][i]]['order']:
                                parents[parentID].insert(i, actID)
                                break
                        else:
                            parents[parentID].append(actID)
                    del act['id']
                    del act['heading']
            for heading in data['hdgs']:
                for ritualID in data['hdgs'][heading]['rs']:
                    for insertName in insertQueue.keys():
                        if acts[ritualID]['n'] == insertName:
                            for actID in insertQueue[insertName]:
                                acts[actID]['i'] = ritualID
                                logging.debug("Inserting " + acts[ritualID]['n'] + " as insert for " + acts[actID]['n'])
                            del insertQueue[insertName]
                            break
            if insertQueue:
                logging.error("Failed to link ritual: " + str(insertQueue))
            for parentID in parents:
                siblings = parents[parentID]
                for i in range(len(siblings)):
                    del acts[siblings[i]]['order']
                    validate(instance=acts[siblings[i]], schema=schema['definitions']['act'])
                    if i != 0:
                        acts[siblings[i-1]]['x'] = siblings[i]
                        logging.debug("Ordering " + acts[siblings[i]]['n'] + " as next after " + acts[siblings[i-1]]['n'])
                    elif i == 0:
                        if parentID in acts:
                            logging.debug("Ordering " + acts[siblings[i]]['n'] + " as first act in " + acts[parentID]['n'])
                            parent = acts[parentID]
                            parent['x'] = siblings[i]
                            if 'order' in parent:
                                del parent['order']
                                validate(instance=parent, schema=schema['definitions']['ritual'])
    validate(instance=data, schema=schema)
    with open(c.FILE_RITUALS, 'w') as f:
        f.write(json.dumps(data, indent=c.INDENT))

def sync():
    """JSON merge Todoist data

    Args:
    base -- the fully synched Todoist data
    head -- incremental changes

    Returns:
    JSON Object of merged data
    """
    _read()
    if not todoist or c.FORCE_SYNC:
        logging.debug('Starting full Todoist sync')
        r = _request('*')
        _set(r.json())
    else:
        logging.debug('Starting incremental Todoist sync: ' + todoist['sync_token'])
        r = _request(todoist['sync_token'])
        _merge_json(todoist, r.json())
    with open(c.FILE_RITUALS_SCHEMA) as f:
        global schema
        schema = json.load(f)
    extract_acts()