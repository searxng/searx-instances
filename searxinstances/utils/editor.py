# Programmatically open an editor, capture the result.
#
# mostly copy paste from
# https://github.com/fmoo/python-editor (including PR 15 and 16)
# https://github.com/jpscaletti/texteditor
# both use an Apache 2 license.
# both use distutils.spawn.find_executable which is a problem with pytest
# see https://github.com/fmoo/python-editor/issues/29


import sys
import os.path
import subprocess
import tempfile
import shlex
from shutil import which


__all__ = [
    'edit',
    'get_editor',
    'EditorError',
]


MACOS_EDITORS = [
    # The -t flag make MacOS open the default *editor* for the file
    "open -t"
]

COMMON_EDITORS = ["subl", "vscode", "atom"]

# In some linuxes `vim` and/or `emacs` come preinstalled, but we don't want
# to throw you to their unfamiliar UI unless there are other options.
# If you are using them you probably have set your $EDITOR variable anyway.
LINUX_EDITORS = COMMON_EDITORS + ["kate", "geany", "gedit", "nano", "editor"]

WINDOWS_EDITORS = COMMON_EDITORS + ["notepad++.exe", "notepad.exe"]

EDITORS = {"darwin": MACOS_EDITORS, "linux": LINUX_EDITORS, "win": WINDOWS_EDITORS}


class EditorError(RuntimeError):
    pass


def get_default_editors():
    sys_platform = sys.platform

    for platform in EDITORS:
        if sys_platform.startswith(platform):
            return EDITORS[platform]

    return COMMON_EDITORS


def get_editor_args(editor):
    if editor in ['vim', 'gvim', 'vim.basic', 'vim.tiny']:
        return ['-f', '-o']

    elif editor == 'emacs':
        return ['-nw']

    elif editor == 'gedit':
        return ['-w', '--new-window']

    elif editor == 'nano':
        return ['-R']

    elif editor == 'code':
        return ['-w', '-n']

    else:
        return []


def get_editor():
    # Get the editor from the environment.  Prefer VISUAL to EDITOR
    editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
    if editor:
        return editor

    # None found in the environment.  Fallback to platform-specific defaults.
    for editor in get_default_editors():
        path = which(editor)
        if path is not None:
            return path

    raise EditorError("Unable to find a viable editor on this system."
                      "Please consider setting your $EDITOR variable")


def get_tty_filename():
    if sys.platform == 'win32':
        return 'CON:'
    return '/dev/tty'


def edit(filename=None, contents=None, use_tty=None, suffix=''):
    # editor
    editor = get_editor()

    # filename
    tmp = None
    if filename is None:
        tmp = tempfile.NamedTemporaryFile(suffix=suffix)
        filename = tmp.name

    try:
        # write contents
        if contents is not None:
            if isinstance(contents, str):
                contents = contents.encode('utf-8')

            with open(filename, mode='wb') as file_stream:
                file_stream.write(contents)

        # args
        args = shlex.split(editor) +\
            get_editor_args(os.path.basename(os.path.realpath(editor))) +\
            [filename]

        # stdout
        stdout = None
        if use_tty is None and sys.stdin.isatty() and not sys.stdout.isatty():
            stdout = open(get_tty_filename(), 'wb')

        # call editor
        proc = subprocess.Popen(args, close_fds=True, stdout=stdout)
        proc.communicate()

        # read result
        result = None
        if os.path.isfile(filename):
            with open(filename, mode='rb') as file_stream:
                result = file_stream.read()

        # return result
        return result

    finally:
        # delete the temporary file for security reasons
        if tmp is not None:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
