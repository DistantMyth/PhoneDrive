from setuptools import setup, find_packages
from phonedrive import __version__

setup(
    name="phonedrive",
    version=__version__,
    packages=find_packages(),
    install_requires=[
        "customtkinter>=5.2.0",
        "zeroconf>=0.131.0",
        "Pillow>=10.0.0",
        "pystray>=0.19.0",
    ],
    entry_points={
        "console_scripts": [
            "phonedrive=phonedrive.app:main",
        ],
    },
    author="Theta",
    description="Mount PhoneDrive SFTP as a Windows Drive",
    python_requires=">=3.10",
)
