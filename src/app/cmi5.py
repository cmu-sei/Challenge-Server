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


def send_cmi5_statement(statement: dict, statement_id: str) -> bool:
    """
    Sends a CMI5 statement

    Args:
        statement (dict): Statement to send
        statement_id (str): Statement ID to send

    Returns:
        bool: True on success, False on failure
    """

    # Uses the same UUID generated in the statement
    statement["id"] = statement_id

    endpoint = f"{globals.cmi5_endpoint}/statements?statementId={statement_id}"
    if not endpoint:
        logger.error(f"[cmi5] No value found for key: {endpoint}")
        return False

    headers = {
        "Content-Type": "application/json",
        "X-Experience-API-Version": "1.0.3",
        "Authorization": f"{globals.cmi5_auth_token}"
    }

    try:
        resp = requests.put(endpoint, json=statement, headers=headers, timeout=5)
        if resp.status_code not in (204,):
            logger.error(f"[cmi5] Failed to send PUT statement: {resp.status_code} {resp.text}")
            return False
        else:
            verb_id = statement.get("verb", {}).get("id", "")
            logger.info(f"[cmi5] Successfully sent CMI5 statement (verb={verb_id}, id={statement_id}).")
            return True
    except Exception as e:
        logger.error(f"[cmi5] Exception sending statement: {e}")
        return False

def cmi5_send_answered(question_label: str, question_text: str, user_answer: str,
                       question_mode: str, question_opts: dict, success: bool) -> bool:
    """
    Send a "cmi5 allowed" question-level 'answered' statement with result.

    Args:
        question_label (str): question label
        question_text (str): question text
        user_answer (str): answer from the user
        question_mode (str): question mode
        question_opts (dict): question options (if multiple choice)
        success (bool): was the question answered correctly?

    Returns:
        bool: True on success, False on failure
    """

    if not globals.cmi5_enabled:
        return True

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

    if not send_cmi5_statement(statement, statement_id):
        return False
    return True


def cmi5_get_defined_context(categories: list = None) -> dict:
    """
    Appends CMI5-required categories activities to the context (All cmi5 defined
    statements MUST include all properties and values defined in the contextActivities of the
    contextTemplate)

    Args:
        categories (list, optional): list of categories. Defaults to None.

    Returns:
        dict: CMI5 context dict
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
