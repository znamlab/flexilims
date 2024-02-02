from setuptools import setup, find_packages

setup(
    name="flexilims",
    version="v0.8-dev",
    url="https://github.com/znamlab/flexilims",
    license="MIT",
    author="Antonin Blot",
    author_email="antonin.blot@gmail.com",
    description="Python wrapper for Flexilims API",
    packages=find_packages(),
    install_requires=[
        "requests",
        "pandas",
    ],
)
