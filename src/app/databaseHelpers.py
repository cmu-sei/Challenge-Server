#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import datetime, json, re, sys
from typing import Any
from flask import current_app, Flask
from app.extensions import db, globals, record_solves_lock, logger
from app.models import EventTracker, PhaseTracking, QuestionTracking


def natural_key(label: str) -> list:
    """
    Sort key that orders embedded numbers numerically.

    Args:
        label (str): Question or phase label

    Returns:
        list: Sort key
    """

    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r'(\d+)', label)]


def is_pass(grader_result: str) -> bool:
    """
    Check if a grading result is a pass. The status is the first word of the result (`status -- optional msg`).

    Args:
        grader_result (str): Result from the grading script

    Returns:
        bool: True if the status is Success
    """

    return re.match(r"\s*success\b", grader_result, re.IGNORECASE) is not None


def initialize_db(app: Flask, conf: dict) -> None:
            # Initialize phases & add to DB
        with app.app_context():
            if conf['grading'].get('phases'):
                globals.phases_enabled = True
                if ( not conf['grading'].get('phase_info') or (len(conf['grading']['phase_info']) == 0)):
                    logger.error("Phases enabled but no phases are configured in 'config.yml. Exiting.")
                    sys.exit(1)
                globals.phases = conf['grading']['phase_info']
                globals.phase_order = sorted(list(globals.phases.keys()),key=natural_key)
                if 'mini_challenge' in globals.phase_order:
                    globals.phase_order.remove('mini_challenge')
                    globals.phase_order.append('mini_challenge')
                try:
                    globals.current_phase = get_current_phase()
                except KeyError as e:
                    globals.current_phase = globals.phase_order[0]

                p_restart = False
                try:
                    p_chk = PhaseTracking.query.all()
                    if {p.label: p.tasks for p in p_chk} == {k: ','.join(v) for k, v in globals.phases.items()}:
                        p_restart = True
                except Exception as e:
                    ...
                if not p_restart:
                    try:
                        PhaseTracking.query.delete()

                        for ind,phase in enumerate(globals.phase_order):
                            new_phase = PhaseTracking(id=ind, label=phase, tasks=','.join(globals.phases[phase]), solved=False,time_solved="---")
                            db.session.add(new_phase)
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"Unable to add phase {phase} to DB. Exception:{e}.\nExiting.")
                        sys.exit(1)

            ## Add questions to DB for tracking
            globals.question_order = sorted(list(globals.grading_parts.keys()),key=natural_key)
            q_restart = False
            try:
                q_chk = QuestionTracking.query.all()
                if {q.label for q in q_chk} == set(globals.grading_parts):
                    q_restart = True
            except Exception as e:
                print(e)
            if not q_restart:
                try:
                    QuestionTracking.query.delete()
                    if globals.phases_enabled:
                        PhaseTracking.query.update({'solved': False, 'time_solved': '---'})
                        globals.current_phase = globals.phase_order[0]
                    for index,key in enumerate(globals.question_order,start=1):
                        new_question = QuestionTracking(id=index,label=key,task=globals.grading_parts[key]['text'],response="",q_type=globals.grading_parts[key]['mode'],solved=False,time_solved="---")
                        db.session.add(new_question)
                        db.session.commit()
                except Exception as e:
                    logger.error(', '.join(globals.question_order))
                    logger.error(f"Unable to add question {key} to DB. Exception:{e}.\nExiting.")
                    sys.exit(1)


def record_solves() -> None:
    """
    Record completed question data to the database.
    """

    with record_solves_lock:
        with globals.scheduler.app.app_context():
            recorded = [json.loads(e.data) for e in EventTracker.query.all()]
            objs = {
                "Question Solved": QuestionTracking.query.all(),
                "Phase Solved":PhaseTracking.query.all()
            }
            for k,v in objs.items():
                for q in v:
                    if q.solved == True and not any(r.get('event_type') == k and r.get(k) == q.label for r in recorded):
                        cur_data = {
                            "challenge":globals.challenge_name,
                            "support_code":globals.support_code,
                            "event_type":k,
                            k: q.label,
                            "solved_at": q.time_solved,
                            "recorded_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        new_event = EventTracker(data=json.dumps(cur_data))
                        db.session.add(new_event)
            db.session.commit()


def check_db(label: str) -> bool:
    """
    Check if the question has been solved.

    Args:
        label (str): Question label

    Returns:
        bool: Solved status.
    """

    with current_app.app_context():
        cur_question = QuestionTracking.query.filter_by(label=label).first()
        if cur_question == None:
            logger.error("Check Database: No entry found in DB while attempting to mark question completed. Exiting")
            sys.exit(1)
        return cur_question.solved


def update_db(type_q: str, label: str = '', val: str = '', user_answer: str = '', send_failure: bool = False) -> Any:
    """Update database with question or phase status.

    Args:
        type_q (str): 'q' for question or 'p' for phase update
        label (str, optional): Database event label. Defaults to ''.
        val (str, optional): Database event value. Defaults to ''.
        user_answer (str, optional): The user's answer, sent as the xAPI response. Defaults to ''.
        send_failure (bool, optional): Send an xAPI statement if the question is not solved. Defaults to False.

    Returns:
        Any
    """

    with current_app.app_context():
        if type_q == 'q':
            try:
                cur_question = QuestionTracking.query.filter_by(label=label).first()
                if cur_question == None:
                    logger.error("Update Database: No entry found in DB while attempting to mark question completed. Exiting")
                    sys.exit(1)
                if '--' in val:
                    cur_question.response = val.split('--', 1)[1].strip()
                elif val:
                    cur_question.response = "N/A"
                was_solved = cur_question.solved

                part_info = globals.grading_parts.get(label, {})
                question_text = part_info.get('text', '')
                question_mode = part_info.get('mode', '')
                question_opts = {}
                if question_mode == 'mc':
                    question_opts = part_info.get('opts', {})
                user_response = cur_question.response

                if is_pass(val):
                    cur_question.solved = True
                    cur_question.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    # xAPI: If newly solved, send statement with success set to True
                    if not was_solved and globals.xapi_enabled:
                        from app.xapi import send_xapi_statement
                        question_config = globals.grading_parts.get(label, {})
                        send_xapi_statement(label, question_config, user_answer, True)
                else:
                    # xAPI: If newly failed and answered, send statement with success set to False
                    if not was_solved and send_failure and globals.xapi_enabled:
                        from app.xapi import send_xapi_statement
                        question_config = globals.grading_parts.get(label, {})
                        send_xapi_statement(label, question_config, user_answer, False)
                db.session.commit()
            except Exception as e:
                logger.error(f"Exception updating DB with completed question. Exception: {e}. Exiting.")
                sys.exit(1)

        else:
            for p in globals.phase_order:
                phase = PhaseTracking.query.filter_by(label=p).first()
                if phase == None:
                    logger.error("No entry found in DB while attempting to find current phase during DB update. Exiting")
                    sys.exit(1)
                if phase.solved == False:
                    q_list = phase.tasks.split(',')
                    num_q = len(q_list)
                    for q in q_list:
                        cur_q = QuestionTracking.query.filter_by(label=q).first()
                        if cur_q == None:
                            logger.error("No entry found in DB while attempting to update phase DB. Exiting")
                            sys.exit(1)
                        if cur_q.solved == True:
                            num_q -= 1
                    if num_q == 0:
                        phase.solved = True
                        phase.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        db.session.commit()
                    else:
                        globals.current_phase = phase.label
                        return


def get_current_phase() -> str:
    """Get the currently active phase.

    Raises:
        KeyError: If PhaseTracking database table is empty or the current phase key does not exist.

    Returns:
        str: The current phase or "completed"
    """

    with current_app.app_context():
        if not PhaseTracking.query.filter_by().all():
            logger.info(f"PhaseTracking table is empty.")
            raise KeyError
        for phase in globals.phase_order:
            cur_phase = PhaseTracking.query.filter_by(label=phase).first()
            if cur_phase == None:
                logger.error(f"Queried for phase key that does not exist. key: {phase}.")
                raise KeyError
            if cur_phase.solved == False:
                globals.current_phase = cur_phase.label
                return cur_phase.label
        globals.challenge_completed = True
        globals.challenge_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        return "completed"


def check_questions() -> None:
    """
    Check all questions in the database to determine if the challenge is completed.
    """

    with current_app.app_context():
        solved_tracker = 0
        questions = QuestionTracking.query.all()
        expected = len(questions)
        for q in questions:
            if q.solved == True:
                solved_tracker+= 1
        if solved_tracker == expected:
            globals.challenge_completed = True
            # record the completion once, including across restarts
            if not any(json.loads(e.data).get('event_type') == "Challenge Completed" for e in EventTracker.query.all()):
                globals.challenge_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                new_event = EventTracker(data=json.dumps({"challenge":globals.challenge_name, "support_code":globals.support_code, "event_type":"Challenge Completed","recorded_at":globals.challenge_completion_time}))
                db.session.add(new_event)
                db.session.commit()
