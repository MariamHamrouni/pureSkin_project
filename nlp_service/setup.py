from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="pureskin-nlp",
    version="6.0.0",
    author="PureSkin Team",
    author_email="contact@pureskin.ai",
    description="NLP Engine for cosmetic product analysis and dupe finding",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pureskin-nlp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=6.0.0",
            "mypy>=0.991",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
            "opencv-python>=4.7.0",
        ],
        "gpu": [
            "torch>=1.13.0+cu117",  # For CUDA support
        ],
    },
    entry_points={
        "console_scripts": [
            "pureskin-init=init_engine:main",
            "pureskin-benchmark=run_benchmark:main",
            "pureskin-debug=debug_search:main",
        ],
    },
    include_package_data=True,
)