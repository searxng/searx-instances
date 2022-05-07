import sys
import tempfile
import subprocess

from . import model


def run_instance_diff(content_after: str):
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(content_after)
        tmpfile.flush()
    with subprocess.Popen(['diff', tmpfile.name, model.FILENAME]):
        pass


def check():
    print(f'Checking {model.FILENAME}')
    with open(model.FILENAME, 'r', encoding='utf-8') as input_file:
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
    check()
