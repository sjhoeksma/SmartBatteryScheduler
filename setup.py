from setuptools import setup, find_namespace_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="ecactus-ecos-scheduler",
    version="0.1.0",
    author="S.J.Hoeksma",
    author_email="sjhoeksma@gmail.com",
    description="Client for Ecactus ECOS",
    long_description= "A library for eCactus Ecos battery energy optimization and scheduling",,
    long_description_content_type="text/markdown",
    url="https://github.com/sjhoeksma/ecactus-ecos-scheduler",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.5.0",
        "plotly>=5.0.0",
        "requests>=2.25.0",
        "python-dateutil>=2.8.0",
        "streamlit>=1.8.0",
        "pytz>=2024.1",
    ],
    extras_require={
        "frontend": [
            "streamlit>=1.8.0",
            "plotly>=5.0.0",
        ],
        "backend": [
            "streamlit>=1.8.0",
        ],
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0.0",
            "isort>=5.0.0",
        ]
    },
    python_requires=">=3.11",
)