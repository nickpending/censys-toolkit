from setuptools import setup, find_packages

setup(
    name="censys-toolkit",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "censys>=2.2.16",
    ],
    entry_points={
        'console_scripts': [
            'censyspy=censyspy:main',
        ],
    },
    author="nickpending",
    author_email="rudy@voidwire.info",
    description="Command-line utilities to support Censys reconnaissance and data gathering",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/nickpending/censys-toolkit",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
