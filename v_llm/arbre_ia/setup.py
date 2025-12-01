"""Configuration du package headache_assistants."""

from setuptools import setup, find_packages
from pathlib import Path

# Lire le README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="headache_assistants",
    version="0.1.0",
    author="AlexPeirano",
    author_email="",
    description="Assistant médical pour l'évaluation des céphalées et la prescription d'imagerie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlexPeirano/chat_bot_medicale",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
        "nlp": [
            # Pour enrichir le NLU dans le futur
            # "spacy>=3.6.0",
            # "transformers>=4.30.0",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["rules/*.json"],
    },
    entry_points={
        "console_scripts": [
            "headache-assistant=headache_assistants.cli:main",  # À implémenter si besoin
        ],
    },
)
