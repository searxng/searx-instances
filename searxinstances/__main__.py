import argparse
import re
import sys
import tempfile
import subprocess

import httpx
import rfc3986
import editor

from . import model


TITLE_RE = re.compile('(add|remove|delete|del)[ ]+(.+)', re.IGNORECASE)


def normalize_url(url):
    if url.startswith('http://'):
        return None

    if not url.startswith('https://'):
        url = 'https://' + url

    try:
        return rfc3986.normalize_uri(url)
    except Exception:
        return None


def load_requests(issue_number):
    requests = []
    with httpx.Client() as client:
        response = client.get('https://api.github.com/repos/dalf/searx-instances/issues?state=open')
        rjson = response.json()
        for issue in rjson:
            if issue_number is not None and issue.get('number') != issue_number:
                continue
            if len(list(filter(lambda label: label.get('name') == 'instance', issue['labels']))):
                rtitle = re.search(TITLE_RE, issue.get('title'))
                issue_number = issue.get('number')
                command = rtitle.group(1).lower()
                url = normalize_url(rtitle.group(2))
                requests.append((issue_number, command, url, issue))
    return requests


def format_exception(ex):
    result = ""
    if ex is not None:
        msg = str(ex)
        for line in msg.splitlines():
            result += f"\n# {line}"
    return result


def apply_add_request(instance_list, instance_url, issue):
    tmp_instance_list = model.InstanceList()
    new_instance = model.Instance(False)
    tmp_instance_list[instance_url] = new_instance

    tmp_yml = model.yaml_dump(tmp_instance_list)
    tmp_yml += f"#\n# {issue.get('title')}\n#" \
               + f"\n# Issue: #{issue.get('number')}\n"\
               + f"# User: @{issue.get('user').get('login')}\n"
    for line in issue.get('body').splitlines():
        tmp_yml += f"# {line}\n"
    edit = True
    valid = False
    error = ""
    while edit:
        tmp_yml = editor.edit(contents=tmp_yml.encode('utf-8') \
            + format_exception(error).encode('utf-8')).decode('utf-8')

        # no content: stop
        if tmp_yml.strip() == '':
            edit = False
            error = None
            continue

        try:
            # parse yaml
            tmp_instance_list = model.yaml_load(tmp_yml)
        except Exception as ex:
            error = ex
            edit = True
            continue

        # add new yaml
        new_instance_list = instance_list.copy()
        for url, instance in tmp_instance_list.items():
            try:
                new_instance_list[url] = instance
            except ValueError as ex:
                error = ex
                edit = True
                break
        if error is not None:
            continue

        # done
        valid = True
        edit = False

    if valid:
        # update
        for url, instance in tmp_instance_list.items():
            instance_list[url] = instance

        # commit



def apply_remove_request(instance_list, instance_url):
    del instance_list[instance_url]


def apply_requests(instance_list, requests):
    for request in requests:
        print('Issue', request[0])
        if request[1] in ['add']:
            apply_add_request(instance_list, request[2], request[3])
        elif request[1] in ['remove', 'delete', 'del']:
            apply_remove_request(instance_list, request[2])


def apply_change(issue_number):
    requests = load_requests(issue_number)
    instance_list = model.load()
    apply_requests(instance_list, requests)
    model.save(instance_list)


def run_instance_diff(content_after):
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
        apply_change(ARGS.issue)
