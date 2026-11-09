"""WebRevive CLI - AI-Based Web Accessibility and Content Refactoring System.

Setup script for packaging the CLI application.
"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read() if fh else ""

setup(
    name="webrevive-cli",
    version="1.0.0",
    author="WebRevive AI Contributors",
    author_email="maintainers@webrevive.ai",
    description="Autonomous CLI for AI-powered web accessibility auditing and remediation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/webrevive-ai/webrevive",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.0",
        "httpx>=0.27.0",
        "playwright>=1.42.0",
    ],
    entry_points={
        "console_scripts": [
            "webrevive=webrevive_cli.main:cli",
        ],
    },
)
