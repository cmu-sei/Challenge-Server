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
from app.extensions import logger, globals, db
from app.models import FileUpload



def construct_file_save_path(file_key: str) -> str:
    """
    Pick the next ZIP filename for this file_key
    (e.g. "fileset1_3.zip") and return its full path.
    """
    upload_dir = globals.uploaded_file_directory
    ext        = globals.grading_uploads.get('format', 'zip')
    os.makedirs(upload_dir, exist_ok=True)

    # increment file name to preserve upload history
    next_idx = get_latest_submission_number(file_key) + 1
    filename = f"{file_key}_{next_idx}.{ext}"
    return os.path.join(upload_dir, filename)


def get_latest_submission_number(file_key: str) -> int:
    """
    Return the highest submission_number in FileUploads for a given file_key
    (i.e. filename starting with "<file_key>_"). Returns 0 if none exist.
    """

    like_pattern = f"{file_key}_%"
    latest = (
        FileUpload.query
        .filter(FileUpload.filename.like(like_pattern))
        .order_by(FileUpload.submission_number.desc())
        .first()
    )
    return latest.submission_number if latest else 0


def get_most_recent_uploads(file_keys: list[str]) -> dict[str, str]:
    """
    For each logical key, return the timestamp of its latest ZIP upload
    (or None). Queries the FileUploads table only.
    """

    uploads = {}
    for key in file_keys:
        latest = (
            FileUpload.query
            .filter(FileUpload.filename.like(f"{key}_%"))
            .order_by(FileUpload.submission_number.desc())
            .first()
        )
        uploads[key] = (
            latest.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            if latest else None
        )
    return uploads


def save_uploaded_file(file_key: str, uploaded_files: list[str]):
    """
    Save files that are uploaded to the file system and the database
    """

    next_idx = get_latest_submission_number(file_key) + 1
    upload_dir = globals.uploaded_file_directory
    ext        = globals.grading_uploads.get('format', 'zip')
    os.makedirs(upload_dir, exist_ok=True)

    zip_name = f"{file_key}_{next_idx}.{ext}"
    zip_path = os.path.join(upload_dir, zip_name)

    # Stream into ZIP and collect inner filenames
    tmpdir = tempfile.mkdtemp()
    inner_files = []
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fs in uploaded_files:
                safe = secure_filename(fs.filename or "")
                if not safe:
                    continue
                inner_files.append(safe)
                tmp_fp = os.path.join(tmpdir, safe)
                fs.save(tmp_fp)
                zf.write(tmp_fp, arcname=safe)
    finally:
        shutil.rmtree(tmpdir)

    logger.info(f"Saving uploaded files ({inner_files}) to zip {zip_path}")

    # DB insert
    new_row = FileUpload(
        filename           = zip_name,
        submission_number  = next_idx,
        contained_files    = inner_files
    )
    db.session.add(new_row)
    db.session.commit()

    return zip_path
