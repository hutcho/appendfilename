#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import sys

# if not sys.warnoptions:
#     import os, warnings
#     warnings.simplefilter("default") # Change the filter in this process
#     os.environ["PYTHONWARNINGS"] = "default" # Also affect subprocesses

import argparse
import logging
import os
import re
from pathlib import Path
import readline  # for raw_input() reading from stdin
import sys
import time
from optparse import OptionParser
from textwrap import dedent

PROG_VERSION = u"Time-stamp: <2022-01-07 17:10:27 vk>"
PROG_VERSION_DATE = PROG_VERSION[13:23]
INVOCATION_TIME = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
FILENAME_TAG_SEPARATOR = " -- "  # between file name and (optional) list of tags
# BETWEEN_TAG_SEPARATOR = " "  # between tags (not that relevant in this tool)
DEFAULT_TEXT_SEPARATOR = " "  # between old file name and inserted text
RENAME_SYMLINK_ORIGINALS_WHEN_RENAMING_SYMLINKS = True  # if current file is a symlink with the same name, also rename source file
RE_YYMMDD = r"(\d{6})"
RE_YYYYdashMM = r"([12]\d{3}-[01]\d)"
RE_YYYYMMDD = r"([12]\d{7})"
RE_TIME_PORTION = r"(([T :_-])([012]\d)([:.-])([012345]\d)(([:.-])([012345]\d))?)"
# use double braced {{ }} to escape the braces for the regex pattern since f-strings interpret single braces for variable interpolation
WITHTIME_AND_SECONDS_PATTERN  = re.compile(
    fr"^(([12]\d{{3}}-[01]\d-[0123]\d{RE_TIME_PORTION}?)|{RE_YYYYMMDD}|{RE_YYYYdashMM}|{RE_YYMMDD})(?P<timestamp_filename_seperator>[- _.])(.+)"
    )

USAGE = dedent(f"""

    appendfilename [<options>] <list of files>

    This tool inserts text between the old file name and optional tags or file extension.

    Text within file names is placed between the actual file name and
    the file extension or (if found) between the actual file namd and
    a set of tags separated with {FILENAME_TAG_SEPARATOR}.

    e.g.
        Update for the Boss{DEFAULT_TEXT_SEPARATOR}<NEW TEXT HERE>.pptx
        2013-05-16T15.31.42 Error message{DEFAULT_TEXT_SEPARATOR}<NEW TEXT HERE>{FILENAME_TAG_SEPARATOR}screenshot projectB.png

    When renaming a symbolic link whose source file has a matching file
    name, the source file gets renamed as well.

    Example usage:

        > appendfilename --text="of projectA" "the presentation.pptx"
        > "the presentation{DEFAULT_TEXT_SEPARATOR}of projectA.pptx"

        > appendfilename "2013-05-09T16.17_img_00042 -- fun.jpeg"
          Please enter text: Peter
        > "2013-05-09T16.17_img_00042{DEFAULT_TEXT_SEPARATOR}Peter -- fun.jpeg"


    :copyright: (c) 2013 or later by Karl Voit <tools@Karl-Voit.at>
    :license: GPL v3 or any later version
    :URL: https://github.com/novoid/appendfilename
    :bugreports: via github or <tools@Karl-Voit.at>
    :version: {PROG_VERSION_DATE}
    """)

# file names containing optional tags matches following regular expression
FILE_WITH_EXTENSION_REGEX = re.compile(r"(.*?)(( -- .*)?(\.\w+?)?)$")
FILE_WITH_EXTENSION_BASENAME_INDEX = 1
FILE_WITH_EXTENSION_TAGS_AND_EXT_INDEX = 2


# RegEx which defines "what is a file name component" for tab completion:
FILENAME_COMPONENT_REGEX = re.compile("[a-zA-Z]+")

# blacklist of lowercase strings that are being ignored for tab completion
FILENAME_COMPONENT_LOWERCASE_BLACKLIST = ['img', 'eine', 'einem', 'eines', 'fuer', 'haben',
                                          'machen', 'macht', 'mein', 'meine', 'meinem',
                                          'meinen', 'meines', 'neuem', 'neuer', 'neuen', 'vkvlc']

# initial CV with strings that are provided for tab completion in any case (whitelist)
INITIAL_CONTROLLED_VOCABULARY = ['Karl', 'Graz', 'LaTeX', 'specialL', 'specialP']



def handle_logging(args):
    """Log handling and configuration"""
    if args.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    elif args.quiet:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.ERROR, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)
    #input('Press <Enter> to finish with return value %i ...' % errorcode).strip()
    sys.exit(errorcode)


class SimpleCompleter(object):
    # happily stolen from http://pymotw.com/2/readline/

    def __init__(self, options):
        self.options = sorted(options)
        return

    def complete(self, text, state):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s
                                for s in self.options
                                if s and s.startswith(text)]
                logging.debug('%s matches: %s', repr(text), self.matches)
            else:
                self.matches = self.options[:]
                logging.debug('(empty input) matches: %s', self.matches)

        # Return the state'th item from the match list,
        # if we have that many.
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        logging.debug('complete(%s, %s) => %s',
                      repr(text), state, repr(response))
        return response


def locate_and_parse_controlled_vocabulary():
    """This method is looking for filenames in the current directory
    and parses them. This results in a list of words which are used for tab completion.

    @param return: either False or a list of found words (strings)

    """

    cv = INITIAL_CONTROLLED_VOCABULARY
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files:
        # extract all words from the file name that don't contain numbers
        new_items = FILENAME_COMPONENT_REGEX.findall(os.path.splitext(os.path.basename(f))[0])
        # remove words that are too small
        new_items = [item for item in new_items if len(item) > 3]
        # remove words that are listed in the blacklist
        new_items = [item for item in new_items if item.lower() not in FILENAME_COMPONENT_LOWERCASE_BLACKLIST]
        # remove words that are already in the controlled vocabulary
        new_items = [item for item in new_items if item not in cv]
        # append newly found words to the controlled vocabulary
        cv.extend(new_items)

    if len(cv) > 0:
        return cv
    else:
        return False


def is_broken_link(name):
    """
    This function determines if the given name points to a file that is a broken link.
    It returns False for any other cases such as non existing files and so forth.

    @param name: an unicode string containing a file name
    @param return: boolean
    """

    if os.path.isfile(name) or os.path.isdir(name):
        return False

    try:
        return not os.path.exists(os.readlink(name))
    except FileNotFoundError:
        return False


def is_nonbroken_symlink_file(filename):
    """
    Returns true if the filename is a non-broken symbolic link and not just an ordinary file. False, for any other case like no file at all.

    @param filename: an unicode string containing a file name
    @param return: bookean
    """

    if os.path.isfile(filename):
        if os.path.islink(filename):
            return True
    else:
        return False


def get_link_source_file(filename):
    """
    Return a string representing the path to which the symbolic link points.

    @param filename: an unicode string containing a file name
    @param return: file path string
    """

    assert(os.path.islink(filename))
    return os.readlink(filename)


def handle_file_and_symlink_source_if_found(filepath: Path, text, sep, dryrun, prepend, smartprepend):
    """
    Wraps handle_file() so that if the current filename is a symbolic link,
    modify the source file and re-link its new name before handling the
    current filename.

    @param filename: string containing one file name
    @param text: string that shall be added to file name(s)
    @param dryrun: boolean which defines if files should be changed (False) or not (True)
    @param return: number of errors and optional new filename
    """

    num_errors = 0

    # if filename is a symbolic link and has same basename, tag the source file as well:
    if RENAME_SYMLINK_ORIGINALS_WHEN_RENAMING_SYMLINKS and is_nonbroken_symlink_file(filepath):
        old_sourcefilename = get_link_source_file(filename)

        if os.path.basename(old_sourcefilename) == os.path.basename(filename):

            new_errors, new_sourcefilename = handle_file(old_sourcefilename, text, dryrun)
            num_errors += new_errors

            if old_sourcefilename != new_sourcefilename:
                logging.info('Renaming the symlink-destination file of "' + filename + '" ("' +
                             old_sourcefilename + '") as well …')
                if args.dryrun:
                    logging.debug('I would re-link the old sourcefilename "' + old_sourcefilename +
                                  '" to the new one "' + new_sourcefilename + '"')
                else:
                    logging.debug('re-linking symlink "' + filename + '" from the old sourcefilename "' +
                                  old_sourcefilename + '" to the new one "' + new_sourcefilename + '"')
                    os.remove(filename)
                    os.symlink(new_sourcefilename, filename)
            else:
                logging.debug('The old sourcefilename "' + old_sourcefilename + '" did not change. So therefore I don\'t re-link.')
        else:
            logging.debug('The file "' + os.path.basename(filename) + '" is a symlink to "' + old_sourcefilename +
                          '" but they two do have different basenames. Therefore I ignore the original file.')

    # after handling potential symlink originals, I now handle the file we were talking about in the first place:
    return handle_file(filepath, text, dryrun, sep, prepend, smartprepend)


def handle_file(path: Path, text: str, dryrun: bool, sep, prepend: bool, smartprepend: bool):
    """
    @param filename: a single Path object (expected to point at a file, but could be a directory)
    @param text: string that shall be added to file name(s)
    @param dryrun: boolean which defines if files should be changed (False) or not (True)
    @param return: number of errors and optional new filename
    """

    num_errors = 0
    new_filename = ''

    if path.is_dir():
        logging.warning("Skipping '{}', because it is a directory.".format(path))
        num_errors += 1
        return num_errors, False
    elif not path.is_file():
        logging.error("Skipping '{}', because it isn't a file.".format(path))
        num_errors += 1
        return num_errors, False

    components = re.match(FILE_WITH_EXTENSION_REGEX, path.name)
    if components:
        old_basename = components.group(FILE_WITH_EXTENSION_BASENAME_INDEX)
        tags_with_extension = components.group(FILE_WITH_EXTENSION_TAGS_AND_EXT_INDEX)
    else:
        logging.error("Could not extract file name components of '{}'. Please raise a bug report to the author.".format(path))
        num_errors += 1
        return num_errors, False

    # print("@def handle_file")

    if prepend:
        # print("@@@ PREPEND")

        # logging.debug('args.prepend is set with |' + str(path.parent) + '|' +
        #                 str(text) + '|' + str(sep) + '|' + str(old_basename) + '|' + str(tags_with_extension))
        # print('args.prepend is set with |' + str(path.parent) + '|' +
        #                 str(text) + '|' + str(sep) + '|' + str(old_basename) + '|' + str(tags_with_extension))
        newpath = path.parent / f"{text}{sep}{old_basename}{tags_with_extension}"

    elif smartprepend:
        # print("@@@ SMART PREPEND")
        match = re.match(WITHTIME_AND_SECONDS_PATTERN, path.name)
        # print("MATCH", match, bool(match))
        # logging.debug(f"args.smartprepend is set with | {path.parent} | {text} |" + str(sep) + '|' + str(old_basename) + '|' + str(tags_with_extension))
        # logging.debug('args.smartprepend is set with |' + str(type(os.path.dirname(filename))) + '|' +
        #                 str(type(text)) + '|' + str(type(sep)) + '|' + str(type(old_basename)) + '|' + str(type(tags_with_extension)))
        if match:
            # print("INSIDE MATHC FUNC")
            logging.debug('date/time-stamp found, insert text between date/time-stamp and the rest')
            logging.debug(f'args.smartprepend is set with |{path.parent}|{str(match.group(1))}|{str(match.group(len(match.groups())))}|')
            # logging.debug('args.smartprepend is set with |' + str(type(os.path.dirname(filename))) + '|' +
                            # str(type(match.group(1))) + '|' + str(type(match.group(len(match.groups())))) + '|')
            # print("MATCHGROUPS = ", match.groups())
            # newpath = path.parent / f"{match.group(1)}{match.group("timestamp_filename_seperator")}{text}{sep}{match.groups()[-1]}"
            newpath = path.parent / f"{match.group(1)}{sep}{text}{sep}{match.groups()[-1]}"
            logging.debug('new_filename=%s', newpath)
            # print("NEWPATHINSITE", newpath)
        else:
            # falling back to 'not smart' --prepend
            # logging.debug("can't find a date/time-stamp, falling back to do a normal prepend instead (not smartprepend)")
            newpath = path.parent / f"{text}{sep}{old_basename}{tags_with_extension}"



    else:
        # Append
        # print("@@@HERERHERHERHERH")
        # print("-", path)
        newpath = path.parent / f"{old_basename}{sep}{text}{tags_with_extension}"
        # print("+", newpath)
    # except:
    #     logging.error("Error while trying to build new filename: " + str(sys.exc_info()[0]))
    #     num_errors += 1
    #     return num_errors, False
    assert(isinstance(newpath, Path))

    if dryrun:
        logging.info(" ")
        logging.info(" renaming \"%s\"" % path)
        logging.info("      ⤷   \"%s\"" % (newpath))
    else:
        logging.debug(" renaming \"%s\"" % path)
        logging.debug("      ⤷   \"%s\"" % (newpath))
        # try:
        newpath_created = path.rename(newpath)
        # except:
        #     logging.error("Error while trying to rename file: " + str(sys.exc_info()))
        #     num_errors += 1
        #     return num_errors, False

    return num_errors, newpath_created


def separator():
    """returns the separator between the previous file name and the new text"""
    if args.separator:
        ## XXX the user-provided separator is not cleaned or preprocessed at all: need to add some checks like removing '\n' and similar.
        return args.separator
    else:
        return DEFAULT_TEXT_SEPARATOR


def main():
    parser = argparse.ArgumentParser(
        prog="appendfilename",
        # usage=USAGE,
        )
    parser.add_argument("-t", "--text", help="the text to add to the file name")
    parser.add_argument("-p", "--prepend", action="store_true",
                        help="do the opposite: instead of appending the text, prepend the text")
    parser.add_argument("--smart-prepend", dest="smartprepend", action="store_true",
                        help="Similar to '--prepend' but leaves any date/time-stamps at the start and appends directly after them. e.g. 'YYYY-MM-DD(Thh.mm(.ss))' + smartprepend + the rest")
    parser.add_argument("-s", "--sep", dest="sep", default=" ",
                        help=f"override the default text separator which is '{DEFAULT_TEXT_SEPARATOR}'")
    parser.add_argument("-d", "--dryrun", action="store_true",
                        help="enable dryrun mode: just simulate what would happen, do not modify file(s)")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose mode")
    parser.add_argument("-q", "--quiet", action="store_true", help="enable quiet mode")
    parser.add_argument("files", nargs="+", help="files to rename")
    parser.add_argument("--version", action="version", version=f"{PROG_VERSION_DATE}")
    args = parser.parse_args()

    # print(args)
    # args.verbose = True

    handle_logging(args)

    if args.verbose and args.quiet:
        error_exit(1, "Options \"--verbose\" and \"--quiet\" found. Only 1 can be given, not both.")

    if args.prepend and args.smartprepend:
        error_exit(3, "Options \"--prepend\" and \"--smart-prepend\" found. Only 1 can be given, not both.")

    if len(sys.argv) < 2:
        # not a single command line parameter is given -> print help instead of asking for a string
        parser.print_help()
        sys.exit(0)

    text = args.text

    if not text:

        logging.debug("interactive mode: asking for text ...")
        logging.info("Add text to file name ...")

        vocabulary = locate_and_parse_controlled_vocabulary()
        if vocabulary:

            assert(isinstance(vocabulary, list))

            # Register our completer function
            readline.set_completer(SimpleCompleter(vocabulary).complete)

            # Use the tab key for completion
            readline.parse_and_bind('tab: complete')

            tabcompletiondescription = '; complete ' + str(len(vocabulary)) + ' words with TAB'

        print('         (abort with Ctrl-C' + tabcompletiondescription + ')')
        print()
        text = input('Please enter text: ').strip()

        if not text or len(text) < 1:
            logging.info("no text given, exiting.")
            sys.stdout.flush()
            sys.exit(0)

        logging.info("adding text \"%s\" ..." % text)

    logging.debug("text found: [%s]" % text)

    logging.debug("extracting list of files ...")
    logging.debug("len(args) [%s]" % str(len(args.files)))
    if len(args.files) < 1:
        error_exit(2, "Please add at least one file name as argument")
    files = args.files
    logging.debug("%s filenames found: [%s]" % (str(len(files)), '], ['.join(files)))

    logging.debug("iterate over files ...")
    for filename in files:

        filepath = Path(filename)

        if is_broken_link(filepath):
            # skip broken links completely and write error message:
            logging.error('File "' + filepath + '" is a broken symbolic link. Skipping this one …')

        else:
            # if filename is a symbolic link, tag the source file as well:
            num_errors, new_filename = handle_file_and_symlink_source_if_found(filepath, text, args.sep, args.dryrun, args.prepend, args.smartprepend)

    if num_errors > 0:
        error_exit(4, str(num_errors) + ' error(s) occurred. Please check output above.')

    logging.debug("successfully finished.")
    if args.verbose:
        input('Please press <Enter> for finishing...').strip()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

# END OF FILE #################################################################
