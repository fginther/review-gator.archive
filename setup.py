import os
from setuptools import find_packages, setup
from glob import glob
from os.path import basename
from os.path import splitext
try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

reqs_path = os.path.join(os.path.dirname(__file__), 'src/requirements.txt')

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements(reqs_path, session='hack')

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='review-gator',
    version='0.1',
    install_requires=reqs,
    url='',
    license='',
    author='fginther',
    author_email='francis.ginther@canonical.com',
    description='Helpful utility to render merge proposals as HTML',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/review_gator/*.py')],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'review-gator = '
            'review_gator.review_gator:main',
        ],
    },
)
