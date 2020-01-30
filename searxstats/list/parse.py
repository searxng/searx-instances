import argparse
import re

import httpx
import rfc3986

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
                requests.append((issue_number, command, url))
    return requests


def apply_add_request(instance_list, url):
    new_instance = model.Instance(False, ['test'])
    instance_list[url] = new_instance


def apply_remove_request(instance_list, url):
    del instance_list[url]


def apply_requests(instance_list, requests):
    for request in requests:
        if request[1] in ['add']:
            apply_add_request(instance_list, request[2])
        elif request[1] in ['remove', 'delete', 'del']:
            apply_remove_request(instance_list, request[2])


def main(issue_number):
    requests = load_requests(issue_number)
    instance_list = model.load()
    apply_requests(instance_list, requests)
    model.save(instance_list)
    # print(instance_list.json_dump())
    # git commit


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(description='Update the instance list according to the github issues.')
    PARSER.add_argument('--issue', '-i',
                        type=str, nargs='?', dest='issue',
                        help='Issue number to process, by default all',
                        default=None)

    ARGS = PARSER.parse_args()
    main(ARGS.issue)
