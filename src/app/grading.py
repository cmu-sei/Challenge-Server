#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

from concurrent.futures import Future
import datetime, json, os, subprocess, sys, requests
from time import sleep
from typing import Any
from app.databaseHelpers import check_db, get_current_phase, record_solves, update_db
from app.env import get_clean_env
from app.extensions import db, globals, logger
from app.fileUploads import get_most_recent_file
from app.models import EventTracker
from flask import current_app


def do_grade(args: dict) -> tuple[dict,dict]:
    """
    Grading and token reading for all manual questions

    Args:
        args (dict): Arguments to the grading script (passed via JSON on the command line when grading script is called).

    Returns:
        tuple[dict,dict]: Grading results
    """

    globals.fatal_error = False
    manual_grading_list = list()
    for ques,ans in args.items():
        if (ques not in globals.grading_parts.keys()) or (globals.grading_parts[ques]['mode'] not in globals.VALID_CONFIG_MODES):
            logger.debug(f"The key {ques} is not a a grading key/mode. Skipping")
            continue
        index = int(ques[-1])
        if (globals.grading_parts[ques]['mode'] in globals.MANUAL_MODE) and (globals.grading_parts[ques]['mode'] not in ("button", "upload")):
            manual_grading_list.insert(index,{ques:ans})
        elif globals.grading_parts[ques]['mode'] == "upload":
            file_key = globals.grading_parts[ques]['upload_key']
            saved_archive = get_most_recent_file(file_key, path=True)
            manual_grading_list.insert(index,{ques:saved_archive})


    script_path = os.path.join(globals.custom_script_dir, globals.manual_grading_script)
    _, ext = os.path.splitext(script_path)
    # Start building the command
    if ext == ".py":
        grade_cmd = [sys.executable, script_path]  # Use venv's Python if python script
    else:
        grade_cmd = [script_path]

    # Add JSON-encoded arguments if present
    grade_args = {}
    if manual_grading_list:
        for entry in manual_grading_list:
            grade_args[list(entry.keys())[0]] = list(entry.values())[0]
        grade_cmd.append(json.dumps(grade_args))

    # Handle phase logic
    if globals.phases_enabled:
        current_phase = get_current_phase()
        if current_phase != 'completed':
            grade_cmd.append(current_phase)
        else:
            tmp = [f'{grade_key} : Success' for grade_key in globals.grading_parts.keys()]
            results = dict(tmp)
            return get_results(results)

    try:
        logger.debug(f"Grading command is: {grade_cmd}")
        out = subprocess.run(grade_cmd, capture_output=True, check=True)
        logger.info(f"Grading script finished: {out}")
        output = out.stdout.decode('utf-8')
        if (output == "") or (output == None):
            logger.error("Grading script finished without returning any output.")
            globals.fatal_error = True
    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        logger.error(f"Grading script {globals.manual_grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""

    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))
    results = dict(results)

    with current_app.app_context():
        event_data = {
            "challenge":globals.challenge_name,
            "support_code":globals.support_code,
            "event_type":"Grading Result",
            "output":results,
            "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        new_event = EventTracker(data=json.dumps(event_data))
        db.session.add(new_event)
        db.session.commit()

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] not in globals.MANUAL_MODE:
            continue
        if not globals.phases_enabled:
            if grading_key not in results:
                logger.info(f"Grading script, {globals.manual_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
                results[grading_key] = "Failed"

    for k, v in results.items():
        user_input = grade_args.get(k, "")
        update_db('q', k, f"{v}--{user_input}")

    return get_results(results)


def get_results(results: dict) -> tuple[dict,dict]:
    """
    Parse grading results to determine if any contain "success".

    Args:
        results (dict): Results from grading script.

    Returns:
        tuple[dict,dict]: Success/failure message for each grading check.
    """

    # for each result that is returned, check if success is in the message.
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            logger.debug(f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
        elif check_db(key):             ### check DB to see if failed question was passed previously & update results accordingly
            results[key] = "Success"
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"
    if globals.phases_enabled == True:
        update_db('p')
    return end_results, tokens


def post_submission(tokens: dict) -> Any:
    """
    Send a POST to the grader for automatic grading.
    Method will try 4 times (sleep 1 second between each failed attempt).
    After 4 failures, the method will log an error and return.

    Args:
        tokens (dict): GradingCheck:token to submit
    """

    token_values = tokens.values()

    # build the request headers and payload to send to the grader
    headers = {
        "accept": "text/plain",
        "Content-Type": "application/json",
        "x-api-key": f"{globals.grader_key}"
    }
    payload = f'{{"id":"{globals.challenge_id}","sectionIndex":0,"questions":['
    for token in token_values:
        payload = payload + f'{{"answer":"{token}"}},'
    payload = payload[:-1] + "]}"


    # Try to POST results to the grader 4 times
    ## return immediately on success
    ## log error if still failure after 4 tries
    attempts = 0
    while attempts < 4:
        logger.debug(f"Attempting {globals.grading_verb} submission to URL: {globals.grader_url}\tHeaders: {headers}\tPayload: {payload}")
        attempts = attempts + 1
        try:
            if globals.grading_verb == "POST":
                r = requests.post(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    logger.info(f"Got 200 from {globals.grader_url} after POST")
                    globals.fatal_error = False
                    return
                elif r.status_code == 405:
                    logger.info(f"Got 405 from {globals.grader_url} after POST. Changing to PUT.")
                    globals.grading_verb = "POST"
                else:
                    logger.error(f"Got {r.status_code} from {globals.grader_url} attempting to POST. Message: {r.content}")
            if globals.grading_verb == "PUT":
                r = requests.put(globals.grader_url, data=payload, headers=headers)
                if r.status_code == 200:
                    logger.info(f"Got 200 from {globals.grader_url} after PUT")
                    globals.fatal_error = False
                    return
                else:
                    logger.error(f"Got {r.status_code} from {globals.grader_url} attempting to PUT. Message: {r.content}")
        except Exception as e:
            logger.error(f"Got exception {e} while trying to PUT/POST data to {globals.grader_url}")

        sleep(1)
        logger.debug("Trying grader submission again after failure on previous attempt.")


    logger.error(f"All attempts to submit results to grader failed.\tURL: {globals.grader_url}\tVerb: {globals.grading_verb}\tHeaders: {headers}\tPayload: {payload}")
    globals.fatal_error = True


def done_grading(future: Future) -> None:
    """
    Callback function for do_grade.
    Checks to see if the results need to be PUT to the grading server
    Saves solves to the database

    Args:
        future (Future): Grading results future (populated when grading is finished)
    """

    results, tokens = future.result()
    logger.debug(f"Server sees {globals.manual_grading_script} results as: {results}")
    logger.debug(f"Server sees tokens as: {tokens}")

    # save results and tokens so they can be accessed globally
    globals.manual_results = results
    globals.tokens['manual'] = tokens

    # record solves to the database
    globals.scheduler.add_job(id="Record_Solves",func=record_solves)

    if globals.grader_post:
        post_submission(tokens)


def read_token(part_name: str) -> str:
    """
    Read the token for the named grading check.

    Args:
        part_name (str): Name of the grading check

    Returns:
        str: Token value
    """

    # get the token name for this part
    try:
        value = globals.grading_parts[part_name]['token_name']
    except KeyError:
        logger.error(f"There is no match for {part_name} in the config file. Valid part names from config file are: {globals.grading_parts.keys()}")
        if globals.grader_post:
            globals.fatal_error = True
        return "Unexpected error encountered. Contact an administrator."

    # read tokens from env var
    if globals.token_location == 'env':
        token = get_clean_env(value)
        if not token:
            logger.error(f"Environment variable for token {value} is empty.")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."
        else:
            return token

    # read tokens from guestinfo
    elif globals.token_location == 'guestinfo':
        try:
            output = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.{value}'", shell=True, capture_output=True)
            if 'no value' in output.stderr.decode('utf-8').lower():
                logger.error(f"No value found when querying guestinfo variables for guestinfo.{value}")
                if globals.grader_post:
                    globals.fatal_error = True
                return "Unexpected error encountered. Contact an administrator."
            return output.stdout.decode('utf-8').strip()
        except:
            logger.error("Error when trying to get token from guestinfo vars")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."

    # read token from file
    elif globals.token_location == 'file':
        try:
            with open(f"{globals.basedir}/app/tokens/{value}", 'r') as f:
                return f.readline()
        except:
            logger.error(f"Error opening file {value} when trying to read token for check {part_name}")
            if globals.grader_post:
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."
