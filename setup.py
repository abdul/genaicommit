import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="genaicommit",
    version="0.1.0",
    author="Abdul Qabiz",
    author_email="abdul.qabiz@gmail.com",
    description="AI-powered git commit message generator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/abdul/genaicommit",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "inquirer",
        "cryptography",
        "colorama",
    ],
    entry_points={
        "console_scripts": [
            "genaicommit=genaicommit.main:main"
        ],
    },
)