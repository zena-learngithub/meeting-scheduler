from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="meeting_scheduler",
    version="2.0.0",
    author="Zenawi Zemene",
    author_email="2201020623@cgu-odisha.ac.in",
    description="A secure command-line meeting scheduler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zena-learngithub/meeting-scheduler",
    project_urls={
        "Bug Tracker": "https://github.com/zena-learngithub/meeting-scheduler/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Topic :: Office/Business :: Scheduling",
        "Environment :: Console",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.6",
)