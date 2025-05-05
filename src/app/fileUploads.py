#!/usr/bin/env python3
#
# Challenge Sever
# Copyright 2024 Carnegie Mellon University.
# NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
# Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
# [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
# DM24-0645
#

import os, zipfile, tempfile, shutil
from werkzeug.utils import secure_filename
from app.extensions import globals, db
from app.models import FileUpload


def construct_file_save_path(file_key: str) -> str:
    """
    Pick the next ZIP filename for this file_key
    (e.g. "fileset1_3.zip") and return its full path.
    This includes incrementing the file index by 1.

    Args:
        file_key (str): Name of the file to save

    Returns:
        str: Full path of where to save the file
    """

    upload_dir = globals.uploaded_file_directory
    os.makedirs(upload_dir, exist_ok=True)

    # increment file name to preserve upload history
    next_idx = get_latest_submission_number(file_key) + 1
    filename = f"{file_key}_{next_idx}.zip"
    return os.path.join(upload_dir, filename)


def get_latest_submission_number(file_key: str) -> int:
    """
    Return the highest submission_number in FileUploads for a given file_key
    (i.e. filename starting with "<file_key>_").
    Returns 0 if none exist.

    Args:
        file_key (str): Name of file to lookup (does not have to include the index)

    Returns:
        int: Index of the latest submitted file matching the name. 0 is default.
    """

    like_pattern = f"{file_key}_%"
    latest = (
        FileUpload.query
        .filter(FileUpload.file_name.like(like_pattern))
        .order_by(FileUpload.submission_number.desc())
        .first()
    )
    return latest.submission_number if latest else 0


def get_most_recent_file(file_key: str, path=False) -> str:
    """
    Get the name or path most recent file with the given file_key.

    Args:
        file_key (str): Name of file to lookup (without index)
        path (bool, optional): Set this to true if you want the full path.
                                Defaults to False, which returns on the file name.

    Returns:
        str: [description]
    """

    latest = (
            FileUpload.query
            .filter(FileUpload.file_name.like(f"{file_key}_%"))
            .order_by(FileUpload.submission_number.desc())
            .first()
        )
    if path:
        return latest.file_path if latest else None
    return latest.file_name if latest else None


def get_most_recent_uploads(file_keys: list[str]) -> dict[str, str]:
    """
    For each logical key, return the timestamp of its latest ZIP upload
    (or None). Queries the FileUploads table.

    Args:
        file_keys (list[str]): List of files to lookup.

    Returns:
        dict[str, str]: A dict of filename:latest timestamp
    """

    uploads = {}
    for key in file_keys:
        latest = (
            FileUpload.query
            .filter(FileUpload.file_name.like(f"{key}_%"))
            .order_by(FileUpload.submission_number.desc())
            .first()
        )
        uploads[key] = (
            latest.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            if latest else None
        )
    return uploads


def save_uploaded_file(file_key: str, uploaded_files: list[str]) -> str:
    """
    Save files that are uploaded to the file system and the database

    Args:
        file_key (str): Name of zip to create
        uploaded_files (list[str]): List of files that are to be included in the zip

    Returns:
        str: Path to the saved zip file
    """

    # update file index
    next_idx = get_latest_submission_number(file_key) + 1

    # Build target path
    upload_dir = globals.uploaded_file_directory
    ext        = globals.grading_uploads.get('format', 'zip')
    os.makedirs(upload_dir, exist_ok=True)

    zip_name = f"{file_key}_{next_idx}.{ext}"
    zip_path = os.path.join(upload_dir, zip_name)

    # Write the ZIP and collect inner filenames
    tmpdir = tempfile.mkdtemp()
    try:
        inner = []
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fs in uploaded_files:
                safe = secure_filename(fs.filename or "")
                if not safe:
                    continue
                inner.append(safe)
                tmp_fp = os.path.join(tmpdir, safe)
                fs.save(tmp_fp)
                zf.write(tmp_fp, arcname=safe)
    finally:
        shutil.rmtree(tmpdir)

    # Record in DB
    new_row = FileUpload(
        file_name          = zip_name,
        file_path          = zip_path,
        submission_number = next_idx,
        contained_files   = inner
    )
    db.session.add(new_row)
    db.session.commit()

    return zip_path
