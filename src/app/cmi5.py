#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import json, requests, datetime, isodate, uuid, copy
from app.extensions import logger, globals
from app.env import get_clean_env

def cmi5_read_variables(env_key, config_section, config_key):
    env_value = get_clean_env(env_key)
    if env_value:
        logger.info(f"CMI5 {config_key}: {env_value}")
        return env_value

    config_value = (config_section or {}).get(config_key)
    if config_value:
        logger.info(f"CMI5 {config_key}: {config_value}")
        return config_value

    logger.error(f"[cmi5] Missing required variable '{config_key}'. Please set it as an environment variable or in the config.")
    return ''

def cmi5_load_variables(conf):
    """
    Loads CMI5 values into globals.
    """

    cmi5_conf = conf.get('cmi5') or {}

    globals.cmi5_endpoint     = cmi5_read_variables('CS_CMI5_ENDPOINT', cmi5_conf, 'endpoint')
    if globals.cmi5_endpoint.endswith('/'):
        globals.cmi5_endpoint = globals.cmi5_endpoint.rstrip('/')

    globals.cmi5_registration = cmi5_read_variables('CS_CMI5_REGISTRATION', cmi5_conf, 'registration')
    globals.cmi5_sessionid    = cmi5_read_variables('CS_CMI5_SESSIONID', cmi5_conf, 'sessionid')
    globals.cmi5_activityid   = cmi5_read_variables('CS_CMI5_ACTIVITYID', cmi5_conf, 'activityid')
    globals.cmi5_auth_token   = cmi5_read_variables('CS_CMI5_AUTH', cmi5_conf, 'auth-token')

    # JSON values
    actor_value = cmi5_read_variables('CS_CMI5_ACTOR', cmi5_conf, 'actor') or '{}'
    try:
        globals.cmi5_actor = json.loads(actor_value)
        if not globals.cmi5_actor:
            logger.error("[cmi5] Missing or empty cmi5 actor")
    except Exception as e:
        logger.error(f"[cmi5] Failed to decode cmi5 actor JSON: {e}")
        globals.cmi5_actor = {}

    context_value = cmi5_read_variables('CS_CMI5_CONTEXTTEMPLATE', cmi5_conf, 'contextTemplate') or '{}'
    try:
        context = json.loads(context_value)
        if not context:
            logger.error("[cmi5] Missing or empty cmi5 context")
        context["registration"] = globals.cmi5_registration
    except Exception as e:
        logger.error(f"[cmi5] Failed to decode cmi5 context JSON: {e}")
        context = {"registration": globals.cmi5_registration}

    globals.cmi5_context = context

def send_cmi5_statement(statement: dict, statement_id: str):
    """
    Sends a single xAPI statement
    """
    
    # Uses the same UUID generated in the statement
    statement["id"] = statement_id

    endpoint = f"{globals.cmi5_endpoint}/statements?statementId={statement_id}"
    if not endpoint:
        logger.error(f"[cmi5] No value found for key: {endpoint}")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "X-Experience-API-Version": "1.0.3",
        "Authorization": f"{globals.cmi5_auth_token}"
    }

    try:
        resp = requests.put(endpoint, json=statement, headers=headers, timeout=5)
        if resp.status_code not in (204,):
            logger.error(f"[cmi5] Failed to send PUT statement: {resp.status_code} {resp.text}")
        else:
            verb_id = statement.get("verb", {}).get("id", "")
            logger.info(f"[cmi5] Successfully sent CMI5 statement (verb={verb_id}, id={statement_id}).")
    except Exception as e:
        logger.error(f"[cmi5] Exception sending statement: {e}")

def cmi5_send_completed():
    """
    Send a "cmi5 defined" 'completed' statement at the AU level.
    """
    if not globals.cmi5_enabled:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    statement_id = str(uuid.uuid4())
    au_id = f"{globals.cmi5_activity_id}"

    session_start = globals.cmi5_au_start_time
    if isinstance(session_start, str):
        session_start = datetime.datetime.fromisoformat(session_start)

    duration_seconds = (now - session_start).total_seconds()
    duration = datetime.timedelta(seconds=duration_seconds)
    iso_duration = isodate.duration_isoformat(duration)

    statement = {
        "id": statement_id,
        "actor": globals.cmi5_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {"en-US": "completed"}
        },
        "object": {
            "id": au_id,
            "objectType": "Activity",
            "definition": {
                "name": {"en-US": globals.challenge_name},
                "description": {"en-US": "All questions solved"},
                "type": "http://adlnet.gov/expapi/activities/lesson"
            }
        },
        "result": {
            "completion": True,
            "duration": iso_duration
        },
        "context": cmi5_get_defined_context([
            "https://w3id.org/xapi/cmi5/context/categories/cmi5",
            "https://w3id.org/xapi/cmi5/context/categories/moveon"
        ]),
        "timestamp": now.isoformat()
    }
    send_cmi5_statement(statement, statement_id)
    cmi5_send_terminated()


def cmi5_send_terminated():
    """
    Send a "cmi5 defined" 'terminated' statement at the AU level when session ends.
    """
    if not globals.cmi5_enabled:
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    statement_id = str(uuid.uuid4())
    au_id = f"{globals.cmi5_activityid}"

    session_start = globals.cmi5_au_start_time
    if isinstance(session_start, str):
        session_start = datetime.datetime.fromisoformat(session_start)

    duration_seconds = (now - session_start).total_seconds()
    duration = datetime.timedelta(seconds=duration_seconds)
    iso_duration = isodate.duration_isoformat(duration)

    statement = {
        "id": statement_id,
        "actor": globals.cmi5_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/terminated",
            "display": {"en-US": "terminated"}
        },
        "object": {
            "id": au_id,
            "objectType": "Activity",
            "definition": {
                "name": {"en-US": globals.challenge_name},
                "type": "http://adlnet.gov/expapi/activities/lesson"
            }
        },
        "result": {
            "duration": iso_duration
        },
        "context": cmi5_get_defined_context([
            "https://w3id.org/xapi/cmi5/context/categories/cmi5"
        ]),
        "timestamp": now.isoformat()
    }
    send_cmi5_statement(statement, statement_id)

def cmi5_send_answered(question_label: str, question_text: str, user_answer: str, question_mode: str, question_opts: dict, success: bool):
    """
    Send a "cmi5 allowed" question-level 'answered' statement with result.
    """
    if not globals.cmi5_enabled:
        return

    statement_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)
    au_id = f"{globals.cmi5_activityid}"

    definition = {
        "name": {"en-US": question_label},
        "description": {"en-US": question_text}
    }

    if question_mode == "mc" and isinstance(question_opts, dict):
        definition["interactionType"] = "choice"
        definition["type"] = "http://adlnet.gov/expapi/activities/cmi.interaction"
        definition["choices"] = [
            {
                "id": key,
                "description": {
                    "en-US": value
                }
            }
            for key, value in question_opts.items()
        ]
    
    elif question_mode == "text":
        definition["interactionType"] = "fill-in"
        definition["type"] = "http://adlnet.gov/expapi/activities/cmi.interaction"
    
    else:
        definition["interactionType"] = "performance"
        definition["type"] = "http://adlnet.gov/expapi/activities/cmi.interaction"

    statement = {
        "id": statement_id,
        "actor": globals.cmi5_actor,
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/answered",
            "display": {"en-US": "answered"}
        },
        "object": {
            "objectType": "Activity",
            "id": au_id,
            "definition": definition
        },
        "result": {
            "success": success,
            "response": user_answer
        },
        "context": globals.cmi5_context,
        "timestamp": now.isoformat()
    }

    send_cmi5_statement(statement, statement_id)


def cmi5_get_defined_context(categories=None):
    """
    Appends CMI5-required categories activities to the context (All cmi5 defined statements MUST include all properties and values defined in the contextActivities of the contextTemplate)
    """
    context = copy.deepcopy(globals.cmi5_context)

    if categories is None:
        categories = []

    if "contextActivities" not in context:
        context["contextActivities"] = {}

    existing_category = context["contextActivities"].get("category", [])
    existing_ids = {act.get("id") for act in existing_category}

    for category_id in categories:
        if category_id not in existing_ids:
            existing_category.append({
                "id": category_id,
                "objectType": "Activity"
            })

    context["contextActivities"]["category"] = existing_category
    return context
 