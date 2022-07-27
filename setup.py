#!/usr/bin/env python

from setuptools import setup

extras_require = {
    "test": [
        "pytest>=6.2",
        "pytest-cov>=2.12",
    ],
    "lint": [
        "flake8>=3.9",
        "isort>=5.9",
        "black>=21.9b0",
        "pyright>=1.1",
    ],
    "dev": [
        "ipython>=7.27",
        "ipdb>=0.13",
    ],
}

extras_require["dev"] += extras_require["test"] + extras_require["lint"]


setup(
    name="wes",
    version="0.1.0",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "wes=wes.cli:main",
        ]
    },
    python_requires=">=3.8",
    extras_require=extras_require,
    packages=["wes"],
)
