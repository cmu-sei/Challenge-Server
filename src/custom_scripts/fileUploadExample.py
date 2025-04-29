import json
import os
import sys
from zipfile import ZipFile


def grade_file(filepath):
    file_contents = []
    if os.path.isfile(filepath):
        with ZipFile(filepath) as arc:
            for filename in arc.namelist():
                with arc.open(filename) as f:
                    # Do something with the file
                    # arc.open opens the file in bytes mode, so if we're expecting strings
                    # we'll need to decode to UTF-8 (Python string)
                    file_contents.append(f.read().decode())
        return f"Success - {' | '.join(file_contents)}"
    return "Failure - you didn't submit any files for this part"


def grade(submission=None):
    results = {}

    for check, value in submission.items():
        results[check] = grade_file(value)

    return results


if __name__ == "__main__":
    args = sys.argv[1:]
    submissions = json.loads(args[0]) if args else None
    results = dict()
    results.update(grade(submissions))

    for key, value in results.items():
        print(key, " : ", value)
