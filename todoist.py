from collections import OrderedDict
import json
from json import JSONDecodeError
from jsonschema import validate
import requests
from requests.structures import CaseInsensitiveDict

import logging

import config as c
import util

todoist = {}

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
                        logging.debug(
                            "Deleting from " + table + ": " + base_item[name])
                    else:
                        logging.debug(
                            "Overwritting in " + table + ": " + head_item[name])
                        base[table].append(head_item)
                    break
            if len(head[table]) == 0:
                break
        for head_item in head[table]:
            logging.debug("Adding to " + table + ": " + head_item[name])
            base[table].append(head_item)
    base['sync_token'] = head['sync_token']
    return base

def extract_act(task):
    """Extract and parse an act from a todoist task

    We check the description for the following terms:
    WHEN: See act.schema.json
    HOW LONG: See act.schema.json
    REMINDER: See act.schema.json
    FREQUENCY: See act.schema.json

    Args:
    task -- Dict of Todoist task

    Returns:
    JSON Object of act"""
    ret = {}
    # Step
    name = ""
    task_description = ""
    if 'name' in task:
        # In Todoist, only sections and projects have 'name' fields
        ret['ritual'] = True
        name = task['name']
    elif 'content' in task:
        # In Todoist, only tasks have 'content' fields
        name = task['content']
        task_description = task['description']
        # Next
        next_prefix = "RITUAL: "
        next_prefix_index = name.find(next_prefix)
        if next_prefix_index != -1:
            next_index = next_prefix_index + len(next_prefix)
            next_end = len(name)
            ret['ritual'] = True
            ret['next'] = name[next_index:next_end]
            # name = name.replace(name[next_prefix_index:next_end], "")
        else:
            # When
            when_prefix = "WHEN: "
            when_prefix_index = task_description.find(when_prefix)
            if when_prefix_index != -1:
                when_index = when_prefix_index + len(when_prefix)
                when_end = task_description.find("\n", when_index)
                if when_end == -1:
                    when_end = len(task_description)
                ret['when'] = util.to_seconds(task_description[when_index:when_end])
                task_description = task_description.replace(task_description[when_prefix_index:when_end], "")
            # Duration
            duration_prefix = "HOW LONG: "
            duration_prefix_index = task_description.find(duration_prefix)
            if duration_prefix_index != -1:
                duration_index = duration_prefix_index + len(duration_prefix)
                duration_end = task_description.find("\n", duration_index)
                if duration_end == -1:
                    duration_end = len(task_description)
                ret['time'] = {'expected': util.to_seconds(task_description[duration_index:duration_end])}
                task_description = task_description.replace(task_description[duration_prefix_index:duration_end], "")
            # Reminder
            reminder_prefix = "REMINDER: "
            reminder_prefix_index = task_description.find(reminder_prefix)
            if reminder_prefix_index != -1:
                reminder_index = reminder_prefix_index + len(reminder_prefix)
                reminder_end = task_description.find("\n", reminder_index)
                if reminder_index == -1:
                    reminder_index = len(task_description)
                ret['reminder'] = util.to_seconds(task_description[reminder_index:reminder_end])
                task_description = task_description.replace(task_description[reminder_prefix_index:reminder_end], "")
            # Frequency
            frequency_prefix = "FREQUENCY: "
            frequency_prefix_index = task_description.find(frequency_prefix) # NOT YET IMPLEMENTED
            if frequency_prefix_index != -1:
                frequency_index = frequency_prefix_index + len(frequency_prefix)
                frequency_end = task_description.find("\n", frequency_index)
                if frequency_end == -1:
                    frequency_end = len(task_description)
                # PARSE FREQ
                task_description = task_description.replace(task_description[frequency_prefix_index:frequency_end], "")
    ret['id'] = task['id']
    ret['name'] = name
    if task_description is not "":
        ret['description'] = task_description
    return ret

def extract_rituals():
    """Get the rituals from local data
    Write it to a local file as well
    We are only checking the RITUALS project

    If an item matches a ritual name, it is the config for that ritual with defaults

    Sets full list of all ritual acts sorted by name as in rituals.schema.json
    """

    rituals = {};
    items = todoist['items']
    for project in todoist['projects']:
        if project['name'] == "RITUALS":
            # Populate list of rituals
            for section in todoist['sections']:
                if section['project_id'] == project['id']:
                    # List of sections inside "RITUALS"
                    logging.debug("Extracting ritual: " + section['name'])
                    rituals[section['id']] = extract_act(section)
                    rituals[section['id']]['max_order'] = 0
                    rituals[section['id']]['min_order'] = 0
            # Populate rituals with acts
            for item in items:
                for ritual_id in rituals.keys():
                    if item['section_id'] == ritual_id:
                        # List of items that are in a "RITUALS" section
                        if item['content'] == "INFO":
                            logging.debug("Found INFO for " + rituals[ritual_id]['name'])
                            data = extract_act(item)
                            data['id'] = ritual['id']
                            data['name'] = ritual['name']
                            ritual = data
                        else:
                            if not 'acts_dict' in rituals[ritual_id]:
                                rituals[ritual_id]['acts_dict'] = {}
                            order = int(item['child_order'])
                            if order < rituals[ritual_id]['min_order']:
                                rituals[ritual_id]['min_order'] = order
                            if order > rituals[ritual_id]['max_order']:
                                rituals[ritual_id]['max_order'] = order
                            logging.debug("Adding to ritual " + rituals[ritual_id]['name'] + ": " + item['content'])
                            rituals[ritual_id]['acts_dict'][order] = extract_act(item)
            # Set defaults and link Next's, and sort, and validate
            logging.debug("ORGANIZING RITUALS")
            with open(c.FILE_RITUALS_SCHEMA) as f:
                schema = json.load(f)
            for ritual in rituals.values():
                ritual['acts'] = []
                for x in range(ritual['min_order'], ritual['max_order']+1):
                    if x in ritual['acts_dict']:
                        act = ritual['acts_dict'][x]
                        logging.debug("Act: " + str(act['name']))
                        if 'ritual' not in act:
                            if 'time' in ritual:
                                if 'expected' in ritual['time']:
                                    if 'expected' not in act['time'] or 'time' not in act:
                                        act['time']['expected'] = ritual['time']['expected']
                            if 'reminder' in ritual:
                                if 'reminder' not in act:
                                    act['reminder'] = ritual['reminder']
                            if 'frequency' in ritual:
                                if 'frequency' not in act:
                                    act['frequency'] = ritual['frequency']
                        elif 'next' in act:
                            for y in rituals.values():
                                if act['next'] == y['name']:
                                    act['next'] = y['id']
                        ritual['acts'].append(act)
                del ritual['acts_dict']
                del ritual['min_order']
                del ritual['max_order']
                validate(instance=ritual, schema=schema)
    with open(c.FILE_RITUALS, 'w') as f:
        f.write(json.dumps(rituals))

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
    extract_rituals()