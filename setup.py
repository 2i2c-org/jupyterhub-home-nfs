from setuptools import setup, find_packages

setup(
    name="jupyterhub_home_nfs",
    version="0.0.9",
    packages=find_packages(),
    install_requires=[],
    description="A package for managing storage quotas for JupyterHub home directories",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/2i2c-org/jupyterhub-home-nfs",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
