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

import json, sys

# 'submission' will contain text submitted to the question by the user
def phase1(submission=None):
    results = dict()
    if submission['GradingCheck1'] == 'test1':      # This is just an example that checks if the data passed (if any) passes the required condition to pass the grading check
        results['GradingCheck1'] = "Success"
    else:
        results['GradingCheck1'] = "Failure"
    return results


def phase2(submission=None):
    results = dict()
    if submission['GradingCheck2'] == 'test2':
        results['GradingCheck2'] = "Success"
    else:
        results['GradingCheck2'] = "Failure"
    return results


if __name__ == '__main__':
    # phases variable should contain list of all phases implemented in the challenge & has a function declared above
    phases = ['phase1','phase2']
    args = sys.argv[1:]
    passed_phase = args[-1].strip().lower()
    if passed_phase in phases:
        ## This code will execute IF phases is enabled & current phase was passed to script.
        args.pop(-1)
        submissions = json.loads(args[0]) if args else None
        results = globals()[passed_phase](submissions)
        for key,value in results.items():
            print(key, ' : ', value)
    else:
        print(f"Passed phase ({passed_phase}) does not exist", file=sys.stderr)
        sys.exit(1)
