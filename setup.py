from setuptools import setup, find_packages

setup(
    name='flexilims',
    version='v0.1',
    url='https://github.com/znamlab/flexilims',
    license='MIT',
    author='Antonin Blot',
    author_email='antonin.blot@gmail.com',
    description='Python wrapper for Flexilims API',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        flexiznam=znamdb.cli:cli
        ''',
)
