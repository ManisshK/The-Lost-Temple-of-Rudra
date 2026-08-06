"""
setup.py — The Lost Temple of Rudra

Build and packaging configuration.

Usage:
    pip install -e .                    # editable install for development
    python setup.py build               # build
    pyinstaller temple.spec             # create Windows executable
"""

from setuptools import setup, find_packages

setup(
    name="lost-temple-of-rudra",
    version="0.1.0",
    description="The Lost Temple of Rudra — an AI-driven text adventure",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.11",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "temple=main:run",
            "temple-cli=main:run_cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Games/Entertainment :: Role-Playing",
    ],
    include_package_data=True,
    package_data={
        "": ["../config/*.json", "../assets/**/*", "../data/**/*"],
    },
)
