from setuptools import setup, find_packages

setup(
    name="apitoolkit_django",
    version="0.1",
    packages=find_packages(),
    description='A Django SDK for Apitoolkit integration',
    author_email='hello@apitoolkit.io',
    author='APIToolkit',
    install_requires=[
        'Django',
        'requests',
        'google-cloud-pubsub',
        'google-auth',
        'jsonpath-ng',
    ],
)
