from setuptools import find_packages, setup

setup(
    author="rr-",
    author_email="rr-@sakuya.pl",
    name="pqcli",
    long_description="Progress Quest: the CLI edition",
    version="1.0.1",
    url="https://github.com/rr-/pq-cli.git",
    packages=find_packages(),
    entry_points={"console_scripts": ["pqcli = pqcli.__main__:main"]},
    package_dir={"pqcli": "pqcli"},
    install_requires=["xdg", "urwid", "urwid_readline"],
    classifiers=[
        "Environment :: Console",
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Topic :: Games/Entertainment :: Role-Playing",
        "Topic :: Games/Entertainment :: Simulation",
    ],
)
