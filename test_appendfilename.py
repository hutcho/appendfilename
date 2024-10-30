#!/bin/usr/env python3

# name:    test_appendfilename.py
# author:  nbehrnd@yahoo.com
# license: GPL v3, 2022.
# date:    2022-01-05 (YYYY-MM-DD)
# edit:    2022-01-09 (YYYY-MM-DD)
#
"""Tests for appendfilename using pytest.

Python 3.12.7
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

TEST_DIR = Path("./.tmptestfiles")
TEST_DIR.mkdir(exist_ok=True)

TARGET_PROGRAM = Path("./appendfilename/__init__.py")

@pytest.fixture
def create_test_file(filename):
    """Fixture to create a test file.

    Yields Path objects"""
    test_file_path = TEST_DIR / filename

    # Create the file
    test_file_path.touch()
    # assert test_file_path.is_file()

    # Yield the Path object for use in tests
    yield test_file_path

    # cleanup step (important if test fails, want to remove all remnants)
    # Comment out for now, want to know if any files get left behind
    # test_file_path.unlink(missing_ok=True)


@pytest.mark.default
@pytest.mark.parametrize(
    "filename",
    [
        "test",
        "test.",
        "test.txt",
        "2021-12-31.txt",
        "2021-12-31T18.48.22.txt",
        "20211231.t.x.t",
        "211231 test.longextensiontext",
    ],
)
@pytest.mark.parametrize(
    "append_text", [
        "book",
        "book_shelf",
        "book shelf"
              ]
)
@pytest.mark.parametrize(
    "sep", [
        " ",
        "_",
        "-"
    ]
)
def test_append_sep_notags(create_test_file: Path, append_text: str, sep: str):
    """Check addition just ahead the file extension.

    create_test_file        A fixture to create the files and remove them
    append_text             text to append
    sep                     separator between existing filename and append_text
    """

    original_path = create_test_file

    command = f"{sys.executable} {TARGET_PROGRAM} -t \"{append_text}\" --sep \"{sep}\" \"{original_path}\""
    subprocess.run(command)
    new_filename = f"{original_path.stem}{sep}{append_text}{original_path.suffix}"
    new_path = original_path.parent / new_filename

    assert new_path.is_file()
    new_path.unlink()


@pytest.mark.prepend
@pytest.mark.parametrize("filename", [
    "test.txt",
    "2021-12-31_test.txt",
    "2021-12-31T18.48.22@test.txt",
    "20211231 test.txt",
    "2012-12_test.txt",
    "211231_test.txt"
])
@pytest.mark.parametrize("append_text", ["book", "book_shelf",
                                  ])
@pytest.mark.parametrize("sep", [" ", "!", "@", "#", "$", "%", "_", "+",
                                  "=", "-", "asd"])
def test_prepend_sep_notags(create_test_file, append_text: str, sep: str):
    """Check addition just ahead the file extension.

    create_test_file        A fixture to create the files and remove them
    append_text             text to append (in this case, prepend)
    sep                     separator between existing filename and append_text
    """

    original_path = create_test_file

    command = f"{sys.executable} {TARGET_PROGRAM} -t \"{append_text}\" --sep \"{sep}\" -p \"{original_path}\""
    subprocess.run(command)

    new_filename = f"{append_text}{sep}{original_path.name}"
    new_path = original_path.parent / new_filename

    assert new_path.is_file()
    new_path.unlink()

@pytest.mark.smartprepend
@pytest.mark.parametrize("filename", [
    "test.txt",
    "2021-12-31 test.txt",
    "2021-12-31T18.48.22 test.txt",
    "20211231_test.txt",
    "2021-12_test.txt",
    "211231_test.txt"
    ])
@pytest.mark.parametrize("append_text", [
    "book",
    "book_shelf",
                                  ])
@pytest.mark.parametrize("sep", [
    " " ,
    "#",
    "!",
    "@",
    "#",
    "$",
    "%",
    # "*",
    "_",
    "+",
    "=",
    "-"
                                  ])
def test_smartprepend_sep_notags(create_test_file, append_text, sep):
    """Check that any time stamp stays at the front of the filename.

    create_test_file        A fixture to create the files and remove them
    append_text             text to append (in this case, prepend)
    sep                     separator between existing filename and append_text
    """

    original_path = create_test_file

    command = f"{sys.executable} {TARGET_PROGRAM} -t \"{append_text}\" --sep \"{sep}\" --smart-prepend \"{original_path}\""
    subprocess.run(command)

    # analysis section:
    old_filename = str(original_path.name)

    # test patterns based on date2name vs. other pattern
    RE_DATE2NAME_DEFAULT = r"^\d{4}-[01]\d-[0-3]\d" # date2name default (YYYY-MM-DD)
    RE_DATE2NAME_WITHTIME = RE_DATE2NAME_DEFAULT + r"T[012]\d\.[0-5]\d\.[0-5]\d" # date2name --withtime (YYYY-MM-DDTHH.MM.SS)
    RE_DATE2NAME_COMPACT = r"^\d{4}[01]\d[0-3]\d" # date2name --compact (YYYYMMDD)
    RE_DATE2NAME_MONTH = r"^\d{4}-[01]\d" # date2name --month (YYYY-MM)
    RE_DATE2NAME_SHORT = r"^\d{2}[01]\d[0-3]\d" # date2name --short (YYMMDD)

    if (re.search(RE_DATE2NAME_DEFAULT, old_filename) or
        re.search(RE_DATE2NAME_WITHTIME, old_filename) or
        re.search(RE_DATE2NAME_COMPACT, old_filename) or
        re.search(RE_DATE2NAME_MONTH, old_filename) or
        re.search(RE_DATE2NAME_SHORT, old_filename)
        ):

        if re.search(RE_DATE2NAME_WITHTIME, old_filename):
            # if (running date2name --withtime) then .true.
            time_stamp = old_filename[:19]
            time_stamp_separator = old_filename[19]
            file_extension = old_filename.split(".")[-1]
            old_filename_no_timestamp = old_filename[20:]

        elif re.search(RE_DATE2NAME_DEFAULT, old_filename):
            # if (running date2name in default mode) then .true.
            time_stamp = old_filename[:10]
            time_stamp_separator = old_filename[10]
            file_extension = old_filename.split(".")[-1]
            old_filename_no_timestamp = old_filename[11:]

        elif re.search(RE_DATE2NAME_COMPACT, old_filename):
            # if (running date2name --compact) then .true.
            time_stamp = old_filename[:8]
            time_stamp_separator = old_filename[8]
            file_extension = old_filename.split(".")[-1]
            old_filename_no_timestamp = old_filename[9:]

        elif re.search(RE_DATE2NAME_MONTH, old_filename):
            # if (running date2name --month) then .true.
            time_stamp = old_filename[:7]
            time_stamp_separator = old_filename[7]
            file_extension = old_filename.split(".")[-1]
            old_filename_no_timestamp = old_filename[8:]

        elif re.search(RE_DATE2NAME_SHORT, old_filename):
            # if (running date2name --short) then .true.
            time_stamp = old_filename[:6]
            time_stamp_separator = old_filename[6]
            file_extension = old_filename.split(".")[-1]
            old_filename_no_timestamp = old_filename[7:]

        stem_elements = old_filename_no_timestamp.split(".")[:-1]
        stem = ".".join(stem_elements)

        new_filename = f"{time_stamp}{sep}{append_text}{sep}{stem}.{file_extension}"
        print(f"{time_stamp=}")
        print(f"{sep=}")
        print(f"{append_text=}")
        print("TEST new_filename", new_filename)
        # new_filename = f"{append_text}{sep}{original_path.name}"
        new_path = original_path.parent / new_filename

        print("TEST_NEWPATH!", new_path)

        # assert new_path.is_file()
        # new_path.unlink()
    #     assert os.path.isfile(new_path) is False

    else:
    #     # within the scope set, a file which did not pass date2name earlier
        new_filename = f"{append_text}{sep}{original_path.name}"

        new_path = original_path.parent / new_filename

    assert new_path.is_file()
    new_path.unlink()

# XXX TODO test with tags present e.g. text -- tag1 tag2.txt
# XXX test different exteneions like .jpeg and .tests-etst and .test_sds
# XXX test the regexs hard
