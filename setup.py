from setuptools import setup, find_packages

setup(
    name="dynamicbalancing",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "plotly>=5.0.0",
        "streamlit>=1.8.0",
        "requests>=2.25.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        'dev': [
            'pytest>=6.0.0',
            'pytest-cov>=2.0.0',
            'black>=21.0.0',
            'isort>=5.0.0',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A library for battery energy optimization and scheduling",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dynamicbalancing",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
