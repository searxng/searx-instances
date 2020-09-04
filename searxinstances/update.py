import argparse
import re
import os.path
from abc import abstractmethod

import git
import httpx
import rfc3986
import idna

from . import model
from .utils import editor


class UserRequest:

    __slots__ = ['request_id', 'request_url', 'user', 'command', 'url', 'message']
    user_request_name = None

    # pylint: disable=too-many-arguments
    def __init__(self, request_id: str, request_url: str, user: str, url: str, message: str):
        self.request_id = request_id
        self.request_url = request_url
        self.user = user
        self.url = url
        self.message = message

    @abstractmethod
    def execute(self, instance_list: model.InstanceList, instance_list_update: model.InstanceList):
        raise RuntimeError('Abstract method')

    @abstractmethod
    def get_content(self, existing_instance_list) -> str:
        raise RuntimeError('Not implemented')

    def get_generic_content(self) -> str:
        commit_message = f"{self.user_request_name} {self.url}\n\n"

        if self.request_url is not None:
            commit_message += f"Close {self.request_url}\n"

        if self.user is not None:
            commit_message += f"From @{self.user}\n"

        return add_comment_prefix(commit_message) + "\n" +\
            "#> The above text is the commit message\n" +\
            "#> Delete the whole buffer to cancel the request\n" +\
            "\n" +\
            "#> -- MESSAGE -----------------------\n" +\
            add_comment_prefix(self.message, prefix='#> ') + "\n"

    def run(self, instance_list):
        # set after the while
        instance_list_update = model.InstanceList()
        commit_message = None

        #
        content = self.get_content(instance_list)  # pylint: disable=assignment-from-no-return
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
                print(ex)
                edit = True
                error_msg = exception_to_error_msg(ex)
                continue

            # try to add the new instance(s)
            error_msg = None
            try:
                dummy_instance_list = instance_list.copy()
                self.execute(dummy_instance_list, instance_list_update)
            except ValueError as ex:
                edit = True
                error_msg = exception_to_error_msg(ex)
                continue

            # exit while if no error
            if error_msg is None:
                # done
                edit = False
                valid = True

        if valid:
            # update
            self.execute(instance_list, instance_list_update)
            model.save(instance_list)

            # commit
            return (True, commit_message)
        else:
            return (False, None)


class UserRequestAdd(UserRequest):

    user_request_name = 'Add'

    def get_content(self, existing_instance_list) -> str:
        tmp_instance_list = model.InstanceList()
        tmp_instance_list[self.url] = model.Instance()
        content = model.yaml_dump(tmp_instance_list)
        return content + "\n" +\
            self.get_generic_content()

    def execute(self, instance_list: model.InstanceList, instance_list_update: model.InstanceList):
        for url, instance in instance_list_update.items():
            instance_list[url] = instance


class UserRequestDelete(UserRequest):

    user_request_name = 'Delete'

    def get_content(self, existing_instance_list) -> str:
        return self.get_generic_content()

    def execute(self, instance_list: model.InstanceList, instance_list_update: model.InstanceList):
        del instance_list[self.url]


class UserRequestEdit(UserRequest):

    user_request_name = 'Edit'

    def get_content(self, existing_instance_list) -> str:
        tmp_instance_list = model.InstanceList()
        tmp_instance_list[self.url] = existing_instance_list[self.url]
        content = model.yaml_dump(tmp_instance_list)
        return content + "\n" +\
            self.get_generic_content()

    def execute(self, instance_list: model.InstanceList, instance_list_update: model.InstanceList):
        del instance_list[self.url]
        for url, instance in instance_list_update.items():
            instance_list[url] = instance


class GitCommitContext:

    def __init__(self, repo, file_name_list):
        self.repo = repo
        self.file_name_list = file_name_list
        self.message = None

    def __enter__(self):
        count_staged_files = len(self.repo.index.diff("HEAD"))
        if count_staged_files > 0:
            raise ValueError('There are staged file')
        for file_name in self.file_name_list:
            if self.repo.is_dirty(path=file_name):
                raise ValueError(f'{file_name} is dirty')
        return self

    def commit(self, message: str):
        self.message = message

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if not exc_type and self.message is not None:
            for file_name in self.file_name_list:
                self.repo.git.add(file_name)
            commit = self.repo.git.commit('-m', self.message)
            print('Commit', commit)
        else:
            for file_name in self.file_name_list:
                self.repo.git.checkout(file_name)
        # Don't exceptions
        return False


def get_git_repo():
    repo_path = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + '/..')
    repo = git.Repo(repo_path)
    return repo


def add_comment_prefix(message, prefix='# '):
    result = ""
    for line in message.splitlines():
        result += f"{prefix}{line.strip()}\n"
    return result


def exception_to_error_msg(ex):
    if ex is not None:
        return str(ex)
    return None


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
    output_raw = editor.edit(contents=input_raw, suffix='.yml')
    return remove_error_from_content(output_raw.decode('utf-8'))


def extract_commit_message(content: str) -> str:
    result = ""
    cm_started = False
    for line in content.splitlines():
        if line.startswith('#'):
            cm_started = True
        if cm_started:
            if line.startswith('#'):
                result += line[1:].strip() + '\n'
            else:
                break
    return result


def run_user_request_list(instance_list: model.InstanceList, user_request_list):
    repo = get_git_repo()
    for user_request in user_request_list:
        print(user_request.user_request_name, user_request.url)
        with GitCommitContext(repo, [model.FILENAME]) as git_commit:
            assert isinstance(git_commit, GitCommitContext)
            valid, commit_message = user_request.run(instance_list)
            if valid:
                git_commit.commit(commit_message)
            else:
                print('Cancelled')
                break


TITLE_RE = re.compile('[a-z]*[ ]?(http.+)', re.IGNORECASE)
COMMENT_RE = re.compile('<!--.*-->', re.MULTILINE | re.DOTALL)
LABEL_TO_CLASS = {
    'instance add': UserRequestAdd,
    'instance delete': UserRequestDelete,
    'instance edit': UserRequestEdit
}


def normalize_url(url):
    purl = rfc3986.urlparse(url)

    if purl.scheme is None and purl.host is None and purl.path is not None:
        # no protocol, no // : it is a path according to the rfc3986
        # but we know it is a host
        purl = rfc3986.urlparse('//' + url)

    if purl.scheme is None:
        # The url starts with //
        # Add https (or http for .onion or i2p TLD)
        if model.host_use_http(purl.host):
            purl = purl.copy_with(scheme='http')
        else:
            purl = purl.copy_with(scheme='https')

    # first normalization
    # * idna encoding to avoid misleading host
    # * remove query and fragment
    # * remove empty path
    purl = purl.copy_with(scheme=purl.scheme.lower(),
                          host=idna.encode(purl.host).decode('utf-8').lower(),
                          path='' if purl.path == '/' else purl.path,
                          query=None,
                          fragment=None)

    # only https (exception: http for .onion and .i2p TLD)
    if (purl.scheme == 'https' and not model.host_use_http(purl.host)) or\
       (purl.scheme == 'http' and model.host_use_http(purl.host)):
        # normalize the URL
        return rfc3986.normalize_uri(purl.geturl())

    #
    return None


def get_user_request_class(label_names: list):
    user_request_class = None
    for l_name in label_names:
        if l_name in LABEL_TO_CLASS:
            if user_request_class is None:
                user_request_class = LABEL_TO_CLASS[l_name]
            else:
                return None
    return user_request_class


def load_user_request_list_from_github(github_issue_list) -> list:
    user_request_list = []
    with httpx.Client() as client:
        response = client.get('https://api.github.com/repos/searx/searx-instances/issues?state=open')
        rjson = response.json()
    for issue in rjson:
        if len(github_issue_list) > 0 and issue.get('number') not in github_issue_list:
            # There is an issue selection (len is not zero),
            # and the current issue is not in the list
            continue
        if len(list(filter(lambda label: label.get('name') == 'instance', issue['labels']))):
            request_number = issue.get('number')
            request_url = issue.get('html_url')
            user = issue.get('user').get('login')
            message = re.sub(COMMENT_RE, '', issue.get('body', '')).strip()

            # url
            rtitle = re.search(TITLE_RE, issue.get('title', ''))
            if rtitle is None:
                print(f'Ignoring #{request_number}: URL not found in the title of issue')
                continue
            url = normalize_url(rtitle.group(1))

            # user_request_class
            label_names = set(map(lambda label: label.get('name'), issue['labels']))
            user_request_class = get_user_request_class(label_names)
            if user_request_class is None:
                # incoherent labels, for example add and edit at the same time
                print(f'Ignoring #{request_number}: Incoherent labels: {" ".join(label_names)}')
                continue

            # create and add a new instance of UserRequest
            user_request = user_request_class(request_number, request_url, user, url, message)
            user_request_list.append(user_request)
    return user_request_list


def load_user_request_list():
    parser = argparse.ArgumentParser(description='Update the instance list according to the github issues.')
    parser.add_argument('--github-issues',
                        type=int, nargs='*', dest='github_issue_list',
                        help='Github issue number to process, by default all',
                        default=None)
    parser.add_argument('--add',
                        type=str, nargs='*', dest='add_instances',
                        help='Add instance(s)',
                        default=[])
    parser.add_argument('--delete',
                        type=str, nargs='*', dest='delete_instances',
                        help='Delete instance(s)',
                        default=[])
    parser.add_argument('--edit',
                        type=str, nargs='*', dest='edit_instances',
                        help='Edit instance(s)',
                        default=[])
    args = parser.parse_args()

    user_request_list = []
    if args.github_issue_list is not None:
        user_request_list += load_user_request_list_from_github(args.github_issue_list)
    if len(args.add_instances) > 0:
        for url in args.add_instances:
            user_request_list.append(UserRequestAdd(None, None, None, normalize_url(url), ''))
    if len(args.delete_instances) > 0:
        for url in args.delete_instances:
            user_request_list.append(UserRequestDelete(None, None, None, url, ''))
    if len(args.edit_instances) > 0:
        for url in args.edit_instances:
            user_request_list.append(UserRequestEdit(None, None, None, url, ''))
    return user_request_list


def main():
    instance_list = model.load()
    user_request_list = load_user_request_list()
    run_user_request_list(instance_list, user_request_list)


if __name__ == "__main__":
    main()
