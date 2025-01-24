#!/usr/bin/python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#


import logging
import subprocess
import sys


def grade_challenge():
    '''
    This script can do anything you need to do to grade the grade_challenge.
    This simple example is just a demo
    '''

    results = {}

    out = subprocess.run('hostname', shell=True, capture_output=True)

    if 'challenge' in out.stdout.decode('utf-8'):
        results['GradingCheck1'] = "Success -- this is the expected output"
    else:
        results['GradingCheck1'] = "Failure -- the hostname is not what is expected"
    

    out2 = subprocess.run('ping -c1 google.com', shell=True, capture_output=True)
    print(out2.stdout.decode('utf-8'))

    if 'failure' in out2.stderr.decode('utf-8').lower():
        results['GradingCheck2'] = "Failure -- cannot ping google.com"
    else:
        results['GradingCheck2'] = "Success -- This worked!!"

    for key, value in results.items():
        print(key, ' : ', value)



if __name__ == '__main__':
    grade_challenge()

