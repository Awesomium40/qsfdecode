import setuptools
import os

with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="qsfdecode",
    version="0.1.0",
    author="Jay Walthers",
    author_email="justin_walthers@brown.edu",
    description="A Simple utility to extract SPSS code from Qualtrics QSF survey definitions",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Awesomium40/qsfdecode",
    install_requires=['beautifulsoup4 >= 4.10.0'],
    packages=setuptools.find_packages(),
    package_data={'': ['*.xml', '*.xsd', '*.xslt']},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires='>=3.6',
)