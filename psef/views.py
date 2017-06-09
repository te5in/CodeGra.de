#!/usr/bin/env python3
import os
import tempfile
import uuid
from zipfile import ZipFile

import patoolib
from flask import jsonify, make_response, request
from psef import app
from werkzeug.utils import secure_filename


@app.route("/api/hello")
def say_hello():
    return jsonify({"msg": "Hello this is Flask."})


def random_file_path():
    "Generates a new random file path in the upload directory."
    while True:
        candidate = os.path.join(app.config['UPLOAD_DIR'], str(uuid.uuid4()))
        if os.path.exists(candidate):
            continue
        else:
            break
    return candidate


def is_archive(file):
    return file.filename.endswith(('.zip', '.tar.gz', '.tgz', '.tbz',
                                   '.tar.bz2'))


@app.route("/api/v1/works/<int:work_id>/file", methods=['POST'])
def upload_file(work_id):
    """
    Saves the files on the server if the request is valid.

    For a request to be valid there needs to be:
        - at least one file under key 'file' in the request files
        - all files must be named
    """

    # Check if a valid submission was made
    files = []
    try:
        if len(request.files) == 0:
            raise KeyError
        for key in request.files:
            if not key.startswith('file'):
                raise ValueError(
                    "There was some file in the http request with key {:s}, "
                    "expected file[idx].".format(key))

            file = request.files[key]
            if file.filename == '':
                raise ValueError(
                    "The name of the file with key '{:s}' in the http request "
                    "was an empty string.".format(key))

            files.append(file)
    except KeyError as e:
        return make_response(jsonify({
            "message": "No file in HTTP request.",
            "description": "There was no file in the HTTP request.",
            "code": None
        }), 400)
    except ValueError as e:
        return make_response(jsonify({
            "message": "Invalid file in HTTP request.",
            "description": str(e),
            "code": None
        }), 400)

    # Save files under random name
    # TODO: Add entries to database
    for file in files:
        # Unpack archives
        if is_archive(file):
            tmpmode, tmparchive = tempfile.mkstemp()
            tmpdir = tempfile.mkdtemp()
            file.save(tmparchive)
            patoolib.extract_archive(tmparchive, outdir=tmpdir)

            for root, _, filenames in os.walk(tmpdir):
                rel_path = os.path.relpath(root, start=tmpdir)
                for filename in filenames:
                    os.rename(os.path.join(root, filename), random_file_path())

        else:
            file.save(random_file_path())

    return make_response(jsonify({
        "message": "Files were successfully uploaded",
        "description": "The files were uploaded and are stored in the uploads "
                       "folder",
        "code": None
    }), 200)
