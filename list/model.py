import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


class AdditionalUrl(yaml.YAMLObject):

    yaml_tag = '!AdditionalUrl'
    __slots__ = ['url', 'relation']

    def __init__(self, url, relation):
        self.url = url
        self.relation = relation

    def __str__(self):
        return self.url + ',' + str(self.relation)

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, additional_url):
        return dumper.represent_dict([
            ('url', additional_url.url),
            ('relation', additional_url.relation)
        ])

    @staticmethod
    def yaml_constructor(loader, node):
        mapping = loader.construct_mapping(node)
        return AdditionalUrl(**mapping)


class Instance(yaml.YAMLObject):

    yaml_tag = '!Instance'
    __slots__ = ['url', 'safe', 'comments', 'additional_urls']

    def __init__(self, url, safe, comments, additional_urls):
        self.url = url
        self.safe = safe
        self.comments = comments
        self.additional_urls = additional_urls

    def __str__(self):
        return self.url + ',' + str(self.safe) + ',"' + self.comments + '",' + str(self.additional_urls)

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, instance):
        return dumper.represent_dict([
            ('url', instance.url),
            ('safe', instance.safe),
            ('comments', instance.comments),
            ('additional_urls', instance.additional_urls)
        ])

    @staticmethod
    def yaml_constructor(loader, node):
        mapping = loader.construct_mapping(node)
        return Instance(**mapping)  


class InstanceList(yaml.YAMLObject):

    yaml_tag = '!InstanceList'
    __slots__ = 'list', '_urls'

    def __init__(self, instance_list=[]):
        super().__init__()
        self.list = instance_list
        self._urls = set()

    def add(self, instance: Instance):
        if instance.url in self._urls:
            raise ValueError(f'{instance.url} already declared')
        for aurl in instance.additional_urls:
            if aurl.url in self._urls:
                raise ValueError(f'{aurl.url} already declared')
        self.list.append(instance)
    
    @property
    def urls():
        return self._urls

    @staticmethod
    def yaml_representer(dumper: yaml.Dumper, instance_list):
        return dumper.represent_list(instance_list.list)

    @staticmethod
    def yaml_constructor(loader: yaml.Loader, node):
        instances = loader.construct_sequence(node)
        return InstanceList(instances)


class InstanceListStorage():

    def __init__(self):
        self.loader, self.dumper = self._get_loader_dumper()

    def _get_loader_dumper(self):
        class ILLoader(Loader):
            pass

        class ILDumper(Dumper):
            pass

        for c in [InstanceList, Instance, AdditionalUrl]:
            ILDumper.add_representer(c, c.yaml_representer)
            ILLoader.add_constructor(c.yaml_tag, c.yaml_constructor)

        ILLoader.add_path_resolver('!InstanceList', [], yaml.SequenceNode)
        ILLoader.add_path_resolver('!Instance', [ None ], yaml.MappingNode)
        ILLoader.add_path_resolver('!AdditionalUrl', [ None, 'additional_urls', None ], yaml.MappingNode)

        return ILLoader, ILDumper

    def load(self, filename) -> InstanceList:
        with open(filename, 'r') as input_file:
            instance_list = yaml.load(input_file, Loader=self.loader)
            if instance_list:
                try:
                    for i in instance_list.list:
                        print(i)
                except:
                    pass
            assert instance_list is not None
            return instance_list

    def save(self, filename: str, instance_list: InstanceList):
        output_content = yaml.dump(instance_list, Dumper=self.dumper)
        with open(filename, 'w') as output_file:  
            output_file.write(output_content)
            

Storage = InstanceListStorage()


__all__ = [ 'InstanceList', 'Instance', 'AdditionalUrl', 'Storage' ]
