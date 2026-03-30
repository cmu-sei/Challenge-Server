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

import os
import sys
import json
from typing import Optional, Dict
from zipfile import ZipFile


def grade_archive(archive_path: str) -> str:
    """
    Process a zip archive, read and decode the contents of each file, and return a formatted string.

    Args:
        archive_path (str): Path to the submitted archive file.

    Returns:
        str: A success message with concatenated decoded file contents if valid;
             otherwise, a failure message.
    """

    file_contents = []
    if os.path.isfile(archive_path):
        with ZipFile(archive_path) as arc:
            for filename in arc.namelist():
                with arc.open(filename) as f:
                    # Decode bytes to UTF-8 strings and collect content
                    file_contents.append(f.read().decode())
        return f"Success - {' | '.join(file_contents)}"
    return "Failure - you didn't submit any files for this part"


def grade(submission: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Grade a dictionary of submission parts by processing each archive.

    Args:
        submission (Optional[Dict[str, str]]): A dictionary mapping check names to archive file paths.

    Returns:
        Dict[str, str]: A dictionary mapping each check to its grading result.
    """

    results = {}
    if submission:
        for check, value in submission.items():
            results[check] = grade_archive(value)
    return results


if __name__ == "__main__":
    args = sys.argv[1:]
    submissions = json.loads(args[0]) if args else None
    results = grade(submissions)

    for key, value in results.items():
        print(f"{key} : {value}")
