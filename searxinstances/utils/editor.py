# Programmatically open an editor, capture the result.
#
# mostly copy paste from
# https://github.com/fmoo/python-editor (including PR 15 and 16)
# https://github.com/jpscaletti/texteditor
# both use an Apache 2 license.
# both use distutils.spawn.find_executable which is a problem with pytest
# see https://github.com/fmoo/python-editor/issues/29
# pylint: disable=consider-using-with


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
    'open -t'
]

COMMON_EDITORS = ['editor', 'vim', 'emacs', 'nano']

# In some linuxes `vim` and/or `emacs` come preinstalled, but we don't want
# to throw you to their unfamiliar UI unless there are other options.
# If you are using them you probably have set your $EDITOR variable anyway.
LINUX_EDITORS = COMMON_EDITORS + ['kate', 'geany', 'gedit', 'nano', 'editor']

WINDOWS_EDITORS = COMMON_EDITORS

EDITORS = {'darwin': MACOS_EDITORS, 'linux': LINUX_EDITORS, 'win': WINDOWS_EDITORS}

ARGUMENTS = {
    'vim': ['-f', '-o'],
    'gvim': ['-f', '-o'],
    'vim.basic': ['-f', '-o'],
    'vim.tiny': ['-f', '-o'],
    'emacs': ['-nw'],
    'nano': ['-R'],
    'gedit': ['-w', '--new-window'],
    'code': ['-w', '-n'],
    'atom': ['-w', '-n'],
    'subl': ['-w', '-n'],
    'kate': ['-b', '-n']
}


class EditorError(RuntimeError):
    pass


def get_editor_args(editor):
    editor = os.path.basename(os.path.realpath(editor))
    return ARGUMENTS.get(editor, [])


def get_default_editors():
    sys_platform = sys.platform

    for platform, editor in EDITORS.items():
        if sys_platform.startswith(platform):
            return editor

    return COMMON_EDITORS


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

    raise EditorError('Unable to find a viable editor on this system.'
                      'Please consider setting your $EDITOR variable')


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
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        filename = tmp.name

    try:
        # write contents
        if contents is not None:
            if isinstance(contents, str):
                contents = contents.encode('utf-8')

            with open(filename, mode='wb') as file_stream:
                file_stream.write(contents)

        # args
        args = shlex.split(editor) + get_editor_args(editor) + [filename]

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


def main():
    # pylint: disable=import-outside-toplevel
    import argparse
    import locale

    def _get_editor(_):
        print(get_editor())

    def _edit(namespace):
        contents = namespace.contents
        if contents is not None:
            contents = contents.encode(locale.getpreferredencoding())
        print(edit(filename=namespace.path, contents=contents))

    argument_parser = argparse.ArgumentParser()
    subparser_action = argument_parser.add_subparsers()

    cmd = subparser_action.add_parser('get-editor')
    cmd.set_defaults(cmd=_get_editor)

    cmd = subparser_action.add_parser('edit')
    cmd.set_defaults(cmd=_edit)
    cmd.add_argument('path', type=str, nargs='?')
    cmd.add_argument('--contents', type=str)

    namespace = argument_parser.parse_args()
    namespace.cmd(namespace)


if __name__ == '__main__':
    main()
