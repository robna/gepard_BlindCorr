"""
Configuration management for microplastics data processing.

This module provides configuration classes and default settings that can be
customized for different datasets and research contexts.
"""

from dataclasses import dataclass, field
from typing import List, Dict
import yaml
from pathlib import Path


@dataclass
class ColumnMapping:
    """Mapping between different column naming conventions and standardized names."""
    
    # Particle identification
    particle_id: str = "particle_id"
    sample_name: str = "sample_name"
    
    # Physical properties
    size_1: str = "size_1_um"  # Length or primary dimension
    size_2: str = "size_2_um"  # Width or secondary dimension  
    size_3: str = "size_3_um"  # Height or tertiary dimension
    area: str = "area_um2"
    
    # Particle characteristics
    polymer_type: str = "polymer_type"
    color: str = "color"
    shape: str = "shape"
    
    # Analysis metadata
    library_entry: str = "library_entry"
    preferred_method: str = "preferred_method"
    comment: str = "comment"
    
    # Sample metadata
    site_name: str = "site_name"
    compartment: str = "compartment"
    contributor: str = "contributor"
    project: str = "project"
    sampling_weight_kg: str = "sampling_weight_kg"
    fraction_analysed: str = "fraction_analysed"
    lab_blank_id: str = "lab_blank_id"
    
    # GPS coordinates
    gps_lon: str = "gps_lon"
    gps_lat: str = "gps_lat"


@dataclass
class ProcessingConfig:
    """Configuration for particle data processing parameters."""
    
    # Size filtering
    size_filter_dimension: str = "size_1"  # Which dimension to use for filtering
    size_filter_highpass: float = 50.0  # Minimum size in micrometers
    size_filter_lowpass: float = 5000.0  # Maximum size in micrometers
    
    # Polymer exclusion list (contamination and dyes)
    excluded_polymers: List[str] = field(default_factory=lambda: [
        'Poly (tetrafluoro ethylene)',
        'PV23',
        'Parafilm',
        'PR101',
        'PB15', 
        'PW6',
        'PBr29',
        'PY17based',
        'PY74',
        'PB15 + PV23',
        'PV23 + PB15',
        'PB15 + TiO2',
        'PB23 + PY17based',
        'Parafilm/PE',
        'PB15+PY17',
        'PY17+PB15',
        'PV23+PB15+TiO2',
        'PB15+TiO2',
        'TiO2+PB15',
        'PB15+PV23'
    ])
    
    # Color standardization mapping
    color_standardization: Dict[str, str] = field(default_factory=lambda: {
        'transparent': 'unspecific',
        'undetermined': 'unspecific', 
        'white': 'unspecific',
        'non-determinable': 'unspecific',
        'grey': 'unspecific',
        'brown': 'unspecific', 
        'black': 'unspecific',
        'violet': 'blue'
    })
    
    # Shape standardization mapping  
    shape_standardization: Dict[str, str] = field(default_factory=lambda: {
        'spherule': 'irregular',
        'irregular': 'irregular',
        'flake': 'irregular',
        'foam': 'irregular', 
        'granule': 'irregular',
        'undetermined': 'irregular'
    })
    
    # Sample identification patterns
    blank_sample_patterns: List[str] = field(default_factory=lambda: [
        'blank', 'Blank', 'BLANK'
    ])
    
    blind_sample_patterns: List[str] = field(default_factory=lambda: [
        'blind', 'Blind', 'BLIND'
    ])
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'ProcessingConfig':
        """Load configuration from a YAML file."""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return cls(**config_data)
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to a YAML file."""
        config_dict = {
            'size_filter_dimension': self.size_filter_dimension,
            'size_filter_highpass': self.size_filter_highpass,
            'size_filter_lowpass': self.size_filter_lowpass,
            'excluded_polymers': self.excluded_polymers,
            'color_standardization': self.color_standardization,
            'shape_standardization': self.shape_standardization,
            'blank_sample_patterns': self.blank_sample_patterns,
            'blind_sample_patterns': self.blind_sample_patterns
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


# Create default column mappings for common data formats
EXCEL_COLUMN_MAPPING = ColumnMapping(
    particle_id="Spectrum ID",
    polymer_type="Polymer Type", 
    color="Color",
    shape="Shape",
    size_1="Long Size (µm)",
    size_2="Short Size (µm)",
    size_3="Height (µm)",
    area="Area (µm²)"
)

SQL_COLUMN_MAPPING = ColumnMapping(
    particle_id="IDParticles",
    sample_name="Sample",
    polymer_type="polymer_type",
    color="Colour", 
    shape="Shape",
    size_1="Size_1_[µm]",
    size_2="Size_2_[µm]", 
    size_3="Size_3_[µm]",
    library_entry="library_entry",
    preferred_method="Preferred_method",
    comment="Comment",
    site_name="Site_name",
    compartment="Compartment",
    contributor="Contributor",
    project="Project",
    sampling_weight_kg="Sampling_weight_[kg]",
    fraction_analysed="Fraction_analysed",
    lab_blank_id="lab_blank_ID",
    gps_lon="GPS_LON",
    gps_lat="GPS_LAT"
)
