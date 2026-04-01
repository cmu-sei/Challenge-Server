#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import json
import sys
from typing import Optional, Dict

def phase1(submission: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Grade logic for phase 1. Checks whether the submitted answer for GradingCheck1 is correct.

    Args:
        submission (Optional[Dict[str, str]]): A dictionary containing user submissions.

    Returns:
        Dict[str, str]: A dictionary with the result for GradingCheck1.
    """

    results = {}
    if submission and submission.get('GradingCheck1') == 'test1':
        results['GradingCheck1'] = "Success"
    else:
        results['GradingCheck1'] = "Failure"
    return results


def phase2(submission: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Grade logic for phase 2. Checks whether the submitted answer for GradingCheck2 is correct.

    Args:
        submission (Optional[Dict[str, str]]): A dictionary containing user submissions.

    Returns:
        Dict[str, str]: A dictionary with the result for GradingCheck2.
    """

    results = {}
    if submission and submission.get('GradingCheck2') == 'test2':
        results['GradingCheck2'] = "Success"
    else:
        results['GradingCheck2'] = "Failure"
    return results


if __name__ == '__main__':
    # List of all supported phases
    phases = ['phase1', 'phase2']
    args = sys.argv[1:]
    passed_phase = args[-1].strip().lower()

    if passed_phase in phases:
        # Remove phase name argument, parse the submission, and run the corresponding function
        args.pop(-1)
        submissions = json.loads(args[0]) if args else None
        results = globals()[passed_phase](submissions)
        for key, value in results.items():
            print(key, ' : ', value)
    else:
        print(f"Passed phase ({passed_phase}) does not exist", file=sys.stderr)
        sys.exit(1)
