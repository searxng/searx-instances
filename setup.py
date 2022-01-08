import codecs
import os
import re

from setuptools import find_namespace_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        version_file,
        re.M,
    )
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string.")


long_description = read('README.md')
requirements = list(map(str.strip, open('requirements.txt').readlines()))
requirements_update = list(map(str.strip, open('requirements-update.txt').readlines()))

setup(
    name="searxinstances",
    version=find_version("searxinstances", "__version__.py"),
    description="Searx instances.",
    long_description=long_description,

    license='GNU Affero General Public License',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
    ],
    url='https://github.com/searxng/searx-instances',
    keywords='searx',

    author='SearXNG dev team',
    author_email='contact@searxng.org',

    packages=find_namespace_packages(include=['searxinstances', 'searxinstances.*']),
    package_data={
        'searxinstances': [
            'instances.yml',
        ]
    },
    entry_points={
        'console_scripts': [
            'searxinstances=searxinstances.update:main',
        ],
    },
    zip_safe=False,
    python_requires=">=3.6",
    install_requires=requirements,
    extras_require={
        "update": requirements_update,
    },
)
