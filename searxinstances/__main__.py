import argparse
import re
import sys
import tempfile
import subprocess
import os.path

import editor
import git
import httpx
import rfc3986

from . import model


class UserRequest:

    __slots__ = ['request_id', 'request_url', 'user', 'command', 'url', 'message']

    def __init__(self, request_id, request_url, user, command, url, message):
        self.request_id = request_id
        self.request_url = request_url
        self.user = user
        self.command = command
        self.url = url
        self.message = message


TITLE_RE = re.compile('(add|remove|delete|del)[ ]+(.+)', re.IGNORECASE)
COMMENT_RE = re.compile('<!-- .* -->', re.MULTILINE | re.DOTALL)


def get_git_repo():
    repo_path = os.path.realpath(os.path.dirname(os.path.realpath(__file__))+ '/..')
    repo = git.Repo(repo_path)
    return repo

def normalize_url(url):
    if url.startswith('http://'):
        return None

    if not url.startswith('https://'):
        url = 'https://' + url

    try:
        return rfc3986.normalize_uri(url)
    except Exception:
        return None


def load_user_request_list(issue_number) -> list:
    user_request_list = []
    with httpx.Client() as client:
        # response = client.get('https://api.github.com/repos/dalf/searx-instances/issues?state=open')
        # rjson = response.json()
        import json
        with open('fake_github_result.json', 'r') as input_file:
            rjson = json.load(input_file)
        # END HACK OFF LINE
        for issue in rjson:
            if issue_number is not None and issue.get('number') != issue_number:
                continue
            if len(list(filter(lambda label: label.get('name') == 'instance', issue['labels']))):
                rtitle = re.search(TITLE_RE, issue.get('title'))
                request_number = issue.get('number')
                request_url = issue.get('html_url')
                user = issue.get('user').get('login')
                message = issue.get('body')
                command = rtitle.group(1).lower()
                url = normalize_url(rtitle.group(2))
                user_request = UserRequest(request_number, request_url, user, command, url, message)
                user_request_list.append(user_request)
    return user_request_list


def add_comment_prefix(message, prefix='# '):
    result = ""
    for line in message.splitlines():
        result += f"{prefix}{line.strip()}\n"
    return result


def exception_to_error_msg(ex):
    if ex is not None:
        return str(ex)
    return None


def get_commit_message(user_request: UserRequest):
    return f"{user_request.command} {user_request.url}\n\n" \
            + f"Close {user_request.request_url}\n"\
            + f"From @{user_request.user}\n\n"\
            + re.sub(COMMENT_RE, '', user_request.message).strip() + "\n"


def get_content(user_request: UserRequest):
    tmp_instance_list = model.InstanceList()
    tmp_instance_list[user_request.url] = model.Instance(False)
    content = model.yaml_dump(tmp_instance_list)
    commit_message = get_commit_message(user_request)
    return content + "\n" +\
           add_comment_prefix(commit_message) + "\n"


def add_error_to_content(content: str, error_msg: str) -> str:
    if error_msg is None or error_msg == "":
        return content
    line_break = '' if content[-2:] == '\n\n' else '\n'
    return content +\
        line_break +\
        "## -- ERROR -----------------------\n" +\
        add_comment_prefix(error_msg, prefix='## ')


def remove_error_from_content(content: str) -> str:
    result = ""
    for line in content.splitlines():
        if line.startswith('##'):
            # remove last new line char
            if result[-2:] == '\n\n':
                result = result[:-1]
            # ignore the error message lines
            break
        result += line + "\n"
    return result


def call_editor(content: str, error_msg: str) -> str:
    input_raw = add_error_to_content(content, error_msg).encode('utf-8')
    output_raw = editor.edit(contents=input_raw, suffix='.yaml')
    return remove_error_from_content(output_raw.decode('utf-8'))


def extract_commit_message(content: str) -> str:
    result = ""
    cm_started = False
    for line in content.splitlines():
        if line.startswith('# '):
            cm_started = True
        if cm_started and line.startswith('# '):
            result += line + "\n"
        else:
            break
    return result


def apply_add_request(instance_list: model.InstanceList, user_request: UserRequest):
    # set after the while
    instance_list_update = model.InstanceList()
    commit_message = None

    #
    content = get_content(user_request)
    valid = False
    edit = True
    error_msg = None

    # edit until no error and no content
    while edit:
        content = call_editor(content, error_msg)

        # no content: stop
        if content.strip() == '':
            edit = False
            error_msg = None
            continue

        # parse content
        try:
            instance_list_update = model.yaml_load(content)
            commit_message = extract_commit_message(content)
            error_msg = None
        except Exception as ex:
            edit = True
            error_msg = exception_to_error_msg(ex)
            continue

        # try to add the new instance(s)
        new_instance_list = instance_list.copy()
        for url, instance in instance_list_update.items():
            try:
                new_instance_list[url] = instance
                error_msg = None
            except ValueError as ex:
                edit = True
                error_msg = exception_to_error_msg(ex)
                break

        # exit while if no error
        if error_msg is None:
            # done
            edit = False
            valid = True

    if valid:
        # update
        for url, instance in instance_list_update.items():
            instance_list[url] = instance
        model.save(instance_list)

        # commit
        return (True, commit_message)
    else:
        return (False, None)


def apply_remove_request(instance_list, user_request):
    del instance_list[user_request.url]


def apply_user_request(repo, instance_list, user_request):
    # check that instanes.yml not dirty
    if repo.is_dirty(path=model.FILENAME):
        print(f'{model.FILENAME} has uncommited changes')
        return False

    # apply the change
    print('Issue #', user_request.request_id)
    if user_request.command in ['add']:
        func = apply_add_request
    elif user_request.command in ['remove', 'delete', 'del']:
        func = apply_remove_request
    else:
        print(f'Unknow command {user_request.command}')
        return False
    valid, commit_message = func(instance_list, user_request)

    # commit the change
    if valid:
        repo.git.add(model.FILENAME)
        commit = repo.git.commit('-m', commit_message)
        print(f'commit {commit.binsha}')
        return True
    else:
        return False


def apply_user_request_list(repo, instance_list: model.InstanceList, user_request_list):
    # check if model.FILENAME is dirty
    for user_request in user_request_list:
        if not apply_user_request(repo, instance_list, user_request):
            break

def load_and_apply_user_request_list(issue_number: int):
    repo = get_git_repo()
    instance_list = model.load()
    user_request_list = load_user_request_list(issue_number)
    apply_user_request_list(repo, instance_list, user_request_list)


def run_instance_diff(content_after: str):
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(content_after)
        tmpfile.flush()
    subprocess.Popen(['diff', tmpfile.name, model.FILENAME])


def check():
    print(f'Checking {model.FILENAME}')
    with open(model.FILENAME, 'r') as input_file:
        content = input_file.read()
    instance_list = model.yaml_load(content)
    content_after = model.yaml_dump(instance_list)
    if content == content_after:
        print('OK')
    else:
        print('ERROR: The file is not normalized')
        run_instance_diff(content_after.encode('utf-8'))
        sys.exit(1)


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(description='Update the instance list according to the github issues.')
    PARSER.add_argument('--check', action='store_true',
                        help='Check instances.yml syntax',
                        default=False)
    PARSER.add_argument('--issue', '-i',
                        type=int, nargs='?', dest='issue',
                        help='Issue number to process, by default all',
                        default=None)

    ARGS = PARSER.parse_args()
    if ARGS.check:
        check()
    else:
        load_and_apply_user_request_list(ARGS.issue)
