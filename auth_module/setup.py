#!/usr/bin/env python3
"""
Setup script for Auth Module
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "..", "auth_module_README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as fh:
            return fh.read()
    return "Auth Module - A Python module for managing API credentials from a JSON vault file"

setup(
    name="auth-module",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python module for managing API credentials from a JSON vault file",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/auth-module",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "auth=auth_module.cli:main",
        ],
    },
    include_package_data=True,
    keywords="auth, credentials, api, vault, security",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/auth-module/issues",
        "Source": "https://github.com/yourusername/auth-module",
    },
) 