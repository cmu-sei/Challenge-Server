#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import datetime, json, sys
from typing import Any
from flask import current_app, Flask
from app.cmi5 import cmi5_send_answered
from app.extensions import db, globals, record_solves_lock, logger
from app.models import EventTracker, PhaseTracking, QuestionTracking


def initialize_db(app: Flask, conf: dict) -> None:
            # Initialize phases & add to DB
        with app.app_context():
            if conf['grading'].get('phases'):
                globals.phases_enabled = True
                if ( not conf['grading'].get('phase_info') or (len(conf['grading']['phase_info']) == 0)):
                    logger.error("Phases enabled but no phases are configured in 'config.yml. Exiting.")
                    sys.exit(1)
                globals.phases = conf['grading']['phase_info']
                globals.phase_order = sorted(list(globals.phases.keys()),key=str.casefold)
                if 'mini_challenge' in globals.phase_order:
                    tmp = globals.phase_order.pop(0)
                    globals.phase_order.append(tmp)
                try:
                    globals.current_phase = get_current_phase()
                except KeyError as e:
                    globals.current_phase = globals.phase_order[0]

                p_restart = False
                try:
                    p_chk = PhaseTracking.query.all()
                    if len(p_chk) == len(globals.phases):
                        p_restart = True
                except Exception as e:
                    ...
                if not p_restart:
                    try:

                        for ind,phase in enumerate(globals.phase_order):
                            new_phase = PhaseTracking(id=ind, label=phase, tasks=','.join(globals.phases[phase]), solved=False,time_solved="---")
                            db.session.add(new_phase)
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"Unable to add phase {phase} to DB. Exception:{e}.\nExiting.")
                        sys.exit(1)

            ## Add questions to DB for tracking
            globals.question_order = sorted(list(globals.grading_parts.keys()),key=str.casefold)
            q_restart = False
            try:
                q_chk = QuestionTracking.query.all()
                if len(q_chk) == len(globals.grading_parts):
                    q_restart = True
            except Exception as e:
                print(e)
            if not q_restart:
                try:
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
            objs = {
                "Question Solved": QuestionTracking.query.all(),
                "Phase Solved":PhaseTracking.query.all()
            }
            for k,v in objs.items():
                for q in v:
                    if q.solved == True:
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


def update_db(type_q: str, label: str = '', val: str = '') -> Any:
    """Update database with question or phase status.

    Args:
        type_q (str): 'q' for question or 'p' for phase update
        label (str, optional): Database event label. Defaults to ''.
        val (str, optional): Database event value. Defaults to ''.

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
                    user_response, user_answer = val.split('--', 1)
                    cur_question.response = user_response
                if (val and '--' not in val) and (cur_question.response == ''):
                    cur_question.response = "N/A"
                was_solved = cur_question.solved

                part_info = globals.grading_parts.get(label, {})
                question_text = part_info.get('text', '')
                question_mode = part_info.get('mode', '')
                question_opts = {}
                if question_mode == 'mc':
                    question_opts = part_info.get('opts', {})
                user_response = cur_question.response

                if "success" in val.lower():
                    cur_question.solved = True
                    cur_question.time_solved = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    # CMI5: If newly solved, send question-level 'answered' statement with success set to True
                    if not was_solved and globals.cmi5_enabled:
                            cmi5_send_answered(label, question_text, user_answer, question_mode, question_opts, True)
                else:
                    # CMI5: If newly failed, send question-level 'answered' statement with success set to False
                    if not was_solved and globals.cmi5_enabled:
                            cmi5_send_answered(label, question_text, user_answer, question_mode, question_opts, False)
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
        globals.challenge_completed == True
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
            globals.challenge_completed == True
            globals.challenge_completion_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            new_event = EventTracker(data=json.dumps({"challenge":globals.challenge_name, "support_code":globals.support_code, "event_type":"Challenge Completed","recorded_at":globals.challenge_completion_time}))
            db.session.add(new_event)
            db.session.commit()
