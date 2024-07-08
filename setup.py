from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="apitoolkit-django",
    version="1.4.1",
    packages=find_packages(),
    description='A Django SDK for Apitoolkit integration',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email='hello@apitoolkit.io',
    author='APIToolkit',
    install_requires=[
        'Django',
        'requests',
        'google-cloud-pubsub',
        'google-auth',
        'jsonpath-ng',
        'apitoolkit-python',
        'pytz'
    ]
)