from setuptools import setup, find_packages

setup(
    name="censys-toolkit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "censys>=2.2.16",
        "python-dotenv>=1.0.1",
        "click>=8.1.8",
        "rich>=13.7.1",
        "pydantic>=2.10.6",
    ],
    entry_points={
        'console_scripts': [
            'censyspy=censyspy.cli:main',  # Updated entry point to match pyproject.toml
        ],
    },
    author="nickpending",
    author_email="rudy@voidwire.info",
    description="Command-line utilities for Censys API operations with domain discovery features",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/nickpending/censys-toolkit",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "Topic :: Security",
        "Topic :: Internet",
        "Development Status :: 3 - Alpha",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": [
            "black>=24.10.0",
            "isort>=6.0.1",
            "mypy>=1.15.0",
            "pytest>=8.2.2",
            "pytest-cov>=6.1.1",
            "freezegun",
        ],
    },
)
