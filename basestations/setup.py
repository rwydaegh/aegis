from setuptools import setup, find_packages

# Read long description from README
with open("readme.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="basestationlib",
    version="0.1.0",
    description="Multi-country mobile base station data extraction and standardization library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Matthias Leeman - Ghent University/IMEC - WAVES",
    author_email="matthias.leeman@ugent.be",
    url="https://github.ugent.be/mattleem/basestations",
    license="MIT",
    keywords=[
        "base station",
        "cell tower",
        "mobile networks",
        "telecom",
        "antenna",
        "geospatial",
        "OpenCellID",
        "Belgium",
        "Poland",
        "Switzerland",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
    packages=find_packages(exclude=("tests", "docs", "examples")),
    include_package_data=True,
    package_data={
        "basestationLib": [
            "core/*.json",
            "Countries/Belgium/*.json",
            "Countries/Netherlands/*.json",
        ]
    },
    install_requires=[
        "pandas>=1.0.0",
        "numpy>=1.19.0",
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
        "lxml>=4.6.0",
        "pyproj>=3.0.0",
        "scipy>=1.5.0",
        "matplotlib>=3.3.0",
        "tqdm>=4.50.0",
        "pyyaml>=5.3.0",
    ],
    python_requires=">=3.9",
    project_urls={
        "Bug Tracker": "https://github.ugent.be/mattleem/basestations/issues",
        "Documentation": "https://github.ugent.be/mattleem/basestations#readme",
        "Source Code": "https://github.ugent.be/mattleem/basestations",
    },
)
