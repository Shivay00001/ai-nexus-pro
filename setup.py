"""
GOATCLAW Setup Configuration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="goatclaw",
    version="1.0.0",
    author="GOATCLAW Team",
    author_email="info@goatclaw.io",
    description="Advanced Multi-Agent Orchestration System with Production-Grade Features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/goatclaw",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Core has no external dependencies!
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
        "llm": [
            "anthropic>=0.18.0",
            "openai>=1.0.0",
        ],
        "production": [
            "aiohttp>=3.9.0",
            "pydantic>=2.0.0",
            "redis>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "goatclaw=goatclaw.cli:main",
        ],
    },
)
