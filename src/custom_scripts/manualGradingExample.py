#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

#####
# Please reference `grading_README.md` to understand grading script requirements.
#####

import json
import sys
from typing import Optional, Dict


def grade(submission: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Grade a user's submission by checking specific answers against expected values.

    Args:
        submission (Optional[Dict[str, str]]): A dictionary containing user-submitted answers.

    Returns:
        Dict[str, str]: A dictionary mapping each grading check to 'Success' or 'Failure'.
    """

    results = {}

    # GradingCheck1
    if submission.get('GradingCheck1') == 'b':
        results['GradingCheck1'] = "Success"
    else:
        results['GradingCheck1'] = "Failure"

    # GradingCheck2
    if submission.get('GradingCheck2') == 'test2':
        results['GradingCheck2'] = "Success"
    else:
        results['GradingCheck2'] = "Failure"

    # GradingCheck3
    if submission.get('GradingCheck3') == 'test3':
        results['GradingCheck3'] = "Success"
    else:
        results['GradingCheck3'] = "Failure"

    # GradingCheck4
    if submission.get('GradingCheck4') == 'test4':
        results['GradingCheck4'] = "Success"
    else:
        results['GradingCheck4'] = "Failure"

    return results


if __name__ == '__main__':
    args = sys.argv[1:]
    submissions = json.loads(args[0]) if args else None
    results = grade(submissions)

    for key, value in results.items():
        print(key, ' : ', value)
