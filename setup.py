from setuptools import setup, find_packages

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="opencodespace",
    version="0.3.1",
    description="Disposable VS Code instances for YOLO mode development on claude code and gemini cli. Local or cloud.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ngram.com",
    author_email="eng@ngram.com",
    url="https://github.com/ngramai/opencodespace",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "opencodespace=opencodespace.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "opencodespace": [".opencodespace/*", ".opencodespace/**/*"],
    },
    python_requires=">=3.7",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="development, vscode, docker, cloud, devops, ai",
)