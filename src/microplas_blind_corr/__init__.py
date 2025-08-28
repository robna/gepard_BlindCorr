"""
Microplastics Blind Correction Tool

A general-purpose tool for processing microplastics particle data with 
quality control procedures including blank correction and blind sample validation.

This package provides functionality for:
- Loading particle data from various sources (Excel, CSV, SQL databases)
- Applying blank correction to remove laboratory contamination
- Performing blind sample validation for method quality control
- Standardizing particle data formats and properties
"""

__version__ = "2.0.0"
__author__ = "Robert Naumann"

from .processors.particle_processor import ParticleProcessor
from .processors.blank_corrector import BlankCorrector
from .processors.blind_corrector import BlindCorrector
from .data_loaders.excel_loader import ExcelLoader
from .config.settings import ProcessingConfig

__all__ = [
    "ParticleProcessor",
    "BlankCorrector", 
    "BlindCorrector",
    "ExcelLoader",
    "ProcessingConfig"
]
