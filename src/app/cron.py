#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import datetime, os, sys, subprocess
from app.databaseHelpers import record_solves
from time import sleep
from app.env import get_clean_env
from app.extensions import globals, logger
from app.grading import post_submission, read_token


def set_cron_vars(conf: dict) -> None:
    """
    Set the value of the cron global vars.
    Try reading values from environment variables. Fall back to config file, then defaults or error.

    Args:
        conf (dict): Configuration dict
    """

    # set cron grading script. Error if script is not defined or not executable
    globals.grading_mode.append('cron')
    globals.cron_grading_script = get_clean_env('CS_CRON_GRADING_SCRIPT') or conf['grading'].get('cron_grading_script')
    if not globals.cron_grading_script:
        logger.error(f"Cron grading not script defined.")
        sys.exit(1)
    logger.info(f"Cron grading script: {globals.custom_script_dir}/{globals.cron_grading_script}")
    try:
        if not os.access(f"{globals.custom_script_dir}/{globals.cron_grading_script}", os.X_OK):
            logger.error(f"Cron grading script {globals.custom_script_dir}/{globals.cron_grading_script} is not executable")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Got exception {e} while checking if grading script {globals.custom_script_dir}/{globals.cron_grading_script} is executable.")
        sys.exit(1)

    globals.cron_interval = int(get_clean_env('CS_CRON_INTERVAL') or conf['grading'].get('cron_interval') or 60)
    logger.info(f"cron_interval: {globals.cron_interval}")

    globals.cron_limit = int(get_clean_env('CS_CRON_LIMIT') or conf['grading'].get('cron_limit') or -1)
    logger.info(f"cron_limit: {globals.cron_limit}")

    globals.cron_delay = int(get_clean_env('CS_CRON_DELAY') or conf['grading'].get('cron_delay') or 0)
    logger.info(f"cron_delay: {globals.cron_delay}")

    globals.cron_at = get_clean_env('CS_CRON_AT') or conf['grading'].get('cron_at') or None
    logger.info(f"cron_at: {globals.cron_at}")

    # calculates the total delay by using the cron_at setting and adding it to the cron_delay
    if globals.cron_at is not None:
        globals.cron_type = "at"
        time = globals.cron_at.split(':')
        current_time = datetime.datetime.now()

        start_time = datetime.datetime(current_time.year, current_time.month, current_time.day, hour=int(time[0]), minute=int(time[1]))
        logger.info(f"Cron style grading should begin at {start_time}")

        time_diff = (start_time - current_time).total_seconds()
    else:
        globals.cron_type = "every"
        time_diff = 0

    globals.cron_delay = globals.cron_delay + time_diff


def do_cron_grade() -> tuple[dict,dict]:
    """
    Grading and token reading for cron style grading.

    Returns:
        tuple[dict,dict]: Grading results
    """

    globals.fatal_error = False

    try:
        out = subprocess.run([f"{globals.custom_script_dir}/{globals.cron_grading_script}"], capture_output=True, check=True)
        logger.info(f"Grading script finished: {out}")
        output = out.stdout.decode('utf-8')

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

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if globals.grading_parts[grading_key]['mode'] != 'cron':
            continue
        if grading_key not in results:
            logger.info(f"Grading script, {globals.cron_grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
            results[grading_key] = "Failed"

    # for each result that is returned, check if success is in the message.
    # If success is in the message, then read and store the token for that check
    end_results = results.copy()
    tokens = {}
    for key, value in results.items():
        if key not in globals.grading_parts.keys():
            logger.info(f"Found key in results that is not a grading part. Removing {key} from results dict. ")
            del end_results[key]
        if "success" in value.lower():
            tokens[key] = read_token(key)
        else:
            tokens[key] = "You did not earn a token for this part"

    logger.info(f"Grading Results: {end_results}")
    logger.info(f"Grading tokens: {tokens}")
    return end_results, tokens


def run_cron_thread() -> None:
    """
    Run do_cron_grade on a timer via a thread (similar to a cron job)
    Post submissions if needed.
    Log grading attempts to the database.
    """

    limit = globals.cron_limit
    logger.info(f"Starting cron thread with interval {globals.cron_interval}. Grading is limited to running {limit} times.")

    cron_attempts = 0
    while globals.cron_limit != 0:
        cron_attempts += 1
        globals.cron_limit = globals.cron_limit - 1
        globals.cron_submit_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        logger.info(f"Starting cron grading attempt number {cron_attempts}")
        globals.cron_results, tokens = do_cron_grade()
        globals.tokens['cron'] = tokens
        if globals.grader_post:
            post_submission(tokens)
        logger.info(f"Results of cron grading attempt number {cron_attempts}: {globals.cron_results}")
        # record solves to the database
        globals.scheduler.add_job(id="Record_Solves",func=record_solves)
        sleep(globals.cron_interval)
    logger.info(f"The number of grading attempts ({limit}) has been exhausted. No more grading will take place.")
