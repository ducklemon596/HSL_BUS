# shared_lib/setup.py
from setuptools import setup, find_packages

setup(
    name="hsl_common",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "kafka": ["kafka-python"],
        "redis": ["redis>=4.5.0"],
        "all": ["kafka-python", "redis>=4.5.0"],
    },
)
