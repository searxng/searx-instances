from os.path import realpath, dirname
from collections import OrderedDict
import json
import inspect

import rfc3986
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


# Declare NoneType (see https://bugs.python.org/issue19438)
NoneType = type(None)

# Model


def host_use_http(host):
    tld = host.split('.')[-1]
    # onion and i2p can't part of an IP address
    return tld in ['onion', 'i2p']


def url_validation(url):
    nurl = rfc3986.normalize_uri(url)
    if nurl != url:
        return False, f'URL must be normalized to {nurl}'
    purl = rfc3986.urlparse(nurl)
    if not(
            (purl.scheme == 'https' and not host_use_http(purl.host)) or
            (purl.scheme == 'http' and host_use_http(purl.host))
    ):
        return False, 'the protocol is neither https nor http with an .onion/.i2p TLD'
    if purl.query is not None:
        return False, 'no query in the URL'
    if purl.fragment is not None:
        return False, 'no fragment in the URL'
    return True, None


class AdditionalUrlList(OrderedDict, yaml.YAMLObject):

    yaml_tag = '!AdditionalUrlList'
    __slots__ = []

    def __repr__(self):
        return dict(self.items()).__repr__()

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, additional_url):
        return dumper.represent_dict(additional_url)

    @staticmethod
    def yaml_constructor(loader, node):
        mapping = loader.construct_mapping(node)
        return AdditionalUrlList(**mapping)


class Instance(yaml.YAMLObject):

    yaml_tag = '!Instance'
    __slots__ = ['safe', 'comments', 'additional_urls']

    def __init__(self, safe=None, comments=None, additional_urls=None):
        # type check
        if not isinstance(safe, (bool, NoneType)):
            raise ValueError('safe is not a bool')
        if not isinstance(comments, (list, NoneType)):
            raise ValueError('comments is not a list')
        if not isinstance(additional_urls, (AdditionalUrlList, NoneType)):
            raise ValueError('additional_urls is not a AdditionalUrlList instance')
        if comments is None:
            comments = []
        if additional_urls is None:
            additional_urls = AdditionalUrlList()
        # assign
        self.safe = safe
        self.comments = comments
        self.additional_urls = additional_urls

    def to_json(self):
        return dict([
            ("safe", self.safe),
            ("comments", self.comments),
            ("additional_urls", self.additional_urls)
        ])

    def __repr__(self):
        return str(self.to_json())

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, instance):
        output = []
        if instance.safe is not None:
            output.append(('safe', instance.safe))
        if instance.comments is not None and len(instance.comments) > 0:
            output.append(('comments', instance.comments))
        if instance.additional_urls is not None and len(instance.additional_urls) > 0:
            output.append(('additional_urls', instance.additional_urls))
        return dumper.represent_dict(output)

    @staticmethod
    def yaml_constructor(loader, node: yaml.MappingNode):
        mapping = loader.construct_mapping(node)
        return Instance(**mapping)


class InstanceList(OrderedDict, yaml.YAMLObject):

    yaml_tag = '!InstanceList'
    __slots__ = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._urls = set()

    def __setitem__(self, url: str, instance: Instance):
        # type check
        if not isinstance(url, str):
            raise ValueError('url is not a str but is ' + str(url))
        if not isinstance(instance, Instance):
            raise ValueError('instance is not a Instance but is ' + str(instance))
        # check for duplicate URL
        new_urls = set([url, *instance.additional_urls.keys()])
        conflict_urls = new_urls.intersection(self.urls)
        if len(conflict_urls) > 0:
            raise ValueError(f'{", ".join(conflict_urls)} already declared')
        # check for URL not normalized
        for new_url in new_urls:
            valid_url, error_message = url_validation(new_url)
            if not valid_url:
                raise ValueError(f'{new_url}: {error_message}')
        # update
        super().__setitem__(url, instance)

    @property
    def urls(self):
        all_urls = set()
        for url, instance in self.items():
            all_urls.update(set([url, *instance.additional_urls.keys()]))
        return all_urls

    def json_dump(self):
        return json.dumps(self, cls=ObjectEncoder, indent=2, sort_keys=True)

    def __repr__(self):
        result = '{\n'
        for url, instance in self.items():
            result += ' ' + url + ': ' + str(instance) + '\n'
        result += '}'
        return result

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, instance_list):
        return dumper.represent_dict(instance_list)

    @staticmethod
    def yaml_constructor(loader: yaml.Loader, node):
        mapping = loader.construct_mapping(node)
        return InstanceList(mapping)

# JSON serialization


class ObjectEncoder(json.JSONEncoder):

    def default(self, o):  # pylint: disable=E0202
        if hasattr(o, "to_json"):
            return self.default(o.to_json())
        elif hasattr(o, "__dict__"):
            filtered_obj = dict(
                (key, value)
                for key, value in inspect.getmembers(o)
                if not key.startswith("__")
                and not inspect.isabstract(value)
                and not inspect.isbuiltin(value)
                and not inspect.isfunction(value)
                and not inspect.isgenerator(value)
                and not inspect.isgeneratorfunction(value)
                and not inspect.ismethod(value)
                and not inspect.ismethoddescriptor(value)
                and not inspect.isroutine(value)
            )
            return self.default(filtered_obj)
        return o


# YAML (de)serialization

# pylint: disable=too-many-ancestors
class ILLoader(Loader):
    pass


# pylint: disable=too-many-ancestors
class ILDumper(Dumper):
    def ignore_aliases(self, data):
        return True


for c in [InstanceList, Instance, AdditionalUrlList]:
    ILDumper.add_representer(c, c.yaml_representer)
    ILLoader.add_constructor(c.yaml_tag, c.yaml_constructor)

ILLoader.add_path_resolver('!InstanceList', [], yaml.MappingNode)
ILLoader.add_path_resolver('!Instance', [(yaml.MappingNode, False)])
ILLoader.add_path_resolver('!AdditionalUrlList', [None, 'additional_urls'], yaml.MappingNode)

# Storage
FILENAME = realpath(dirname(realpath(__file__))) + '/instances.yml'


def yaml_dump(instance_list: InstanceList) -> str:
    return yaml.dump(instance_list, Dumper=ILDumper, width=240, allow_unicode=True)


def yaml_load(content: str) -> InstanceList:
    instance_list = yaml.load(content, Loader=ILLoader)
    if not isinstance(instance_list, (InstanceList, NoneType)):
        raise RuntimeError('instance_list must be of type InstanceList or NoneType')
    return instance_list


def load(filename: str = FILENAME) -> InstanceList:
    with open(filename, 'r') as input_file:
        instance_list = yaml.load(input_file, Loader=ILLoader)
        assert isinstance(instance_list, InstanceList)
        return instance_list


def save(instance_list: InstanceList, filename: str = FILENAME):
    output_content = yaml_dump(instance_list)
    with open(filename, 'w') as output_file:
        output_file.write(output_content)


__all__ = ['InstanceList', 'Instance', 'AdditionalUrlList', 'yaml_dump', 'yaml_load', 'load', 'save', 'FILENAME']
