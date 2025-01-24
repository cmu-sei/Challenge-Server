#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import globals
import logging, subprocess, requests
from concurrent.futures import Future
from time import sleep

logger = logging.getLogger("challengeServer")

def do_grade(*args):
    '''
    This method is the actual grading and token reading. 
    The method gets called from the Jinja template rendering (inside { } in the graded.html file)
    '''

    logger.info(f"Calling {globals.grading_script} with arguments: {args}")
    globals.fatal_error = False
    
    # run the grading script and parse output into a dict
    ## The output variable has properties output.stdout  and  output.stderr
    # *args will unpack the list of arguments into individual arguments passed on the command line to the grading script
    try:
        out = subprocess.run([f"{globals.custom_script_dir}/{globals.grading_script}", *args], capture_output=True, check=True)
        logger.info(f"Grading process finished: {out}")
        output = out.stdout.decode('utf-8')
    
    # Something happened if there was a non-zero exit status. Log this and set fatal_error
    except subprocess.CalledProcessError as e:
        logger.error(f"Grading script {globals.grading_script} returned with non-zero exit status {e.returncode}.\tStdout: {e.stdout}\tStderr: {e.stderr}")
        globals.fatal_error = True
        output = ""
    
    results = []
    for sub in output.split('\n'):
        if ':' in sub:
            results.append(map(str.strip, sub.split(':', 1)))

    results = dict(results)

    # ensure all grading parts have a result
    for grading_key in globals.grading_parts.keys():
        if grading_key not in results:
            logger.info(f"Grading script, {globals.grading_script}, did not yield a result for grading part {grading_key}. Assigning value of 'Failed'")
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


def read_token(part_name):
    '''
    Function reads tokens from files. 
    Assumes files are in the standard Kali Iso location and that tokens are only 1 line long

    This method takes a Check name as an argument. Examples can be "Check1", "Check2", etc.
    These names come from your GradingScript (The keys in the json blob)
    '''

    # get the token name for this part
    try:
        value = globals.grading_parts[part_name]['token_name']
    except KeyError:
        logger.error(f"There is no match for {part_name} in the config file. Valid part names from config file are: {globals.grading_parts.keys()}")
        if globals.submission_method == "grader_post":
            globals.fatal_error = True
        return "Unexpected error encountered. Contact an administrator."
    
    # pull tokens from guestinfo if that is the setting
    if globals.token_location == 'guestinfo':
        try: 
            output = subprocess.run(f"vmtoolsd --cmd 'info-get guestinfo.{value}'", shell=True, capture_output=True)
            if 'no value' in output.stderr.decode('utf-8').lower():
                logger.error(f"No value found when querying guestinfo variables for guestinfo.{value}")
                if globals.submission_method == "grader_post":
                    globals.fatal_error = True
                return "Unexpected error encountered. Contact an administrator."
            return output.stdout.decode('utf-8').strip()
        except:
            logger.error("Error when trying to get token from guestinfo vars")
            if globals.submission_method == "grader_post":
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."
    
    # read token from file if guestinfo is not the setting
    else:
        try:
            with open(value, 'r') as f:
                return f.readline()
        except:
            logger.error(f"Error opening file {value} when trying to read token for check {part_name}")
            if globals.submission_method == "grader_post":
                globals.fatal_error = True
            return "Unexpected error encountered. Contact an administrator."


def done_grading(future: Future):
    '''
    Callback function for do_grade. 
    It is meant to check to see if the results need to be PUT to the grading server
    '''
    results, tokens = future.result()
    logger.info(f"Server sees {globals.grading_script} results as: {results}")
    logger.info(f"Server sees tokens as: {tokens}")

    # save results and tokens so they can be accessed globally
    globals.results = results
    globals.tokens = tokens

    if globals.submission_method == 'grader_post':
        post_submission(tokens)


def post_submission(tokens: dict):
    '''
    This method will send a POST to the grader for automatic grading.
    All POST attempts are logged.
    Method will try 4 times (sleep 1 second between each failed attempt).
    After 4 failures, the method will log an error and return. 
    '''
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
        logger.info(f"Attempting {globals.grading_verb} submission to URL: {globals.grader_url}\tHeaders: {headers}\tPayload: {payload}")
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
            if gloabls.grading_verb == "PUT":
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
        logger.info("Trying grader submission again after failure on previous attempt.")


    logger.error(f"All attempts to submit results to grader failed.\tURL: {globals.grader_url}\tVerb: {globals.grading_verb}\tHeaders: {headers}\tPayload: {payload}")
    globals.fatal_error = True
