"""
Core particle data processor.

This module provides the main functionality for processing microplastics
particle data, including standardization, filtering, and preparation for
blank and blind correction procedures.
"""

import pandas as pd
import numpy as np
from typing import Tuple
import logging

from ..config.settings import ProcessingConfig, ColumnMapping


logger = logging.getLogger(__name__)


class ParticleProcessor:
    """Core processor for microplastics particle data."""
    
    def __init__(self, config: ProcessingConfig, column_mapping: ColumnMapping):
        """
        Initialize the particle processor.
        
        Args:
            config: Processing configuration
            column_mapping: Column name mapping
        """
        self.config = config
        self.column_mapping = column_mapping
        
    def process_particles(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply the complete processing pipeline to particle data.
        
        Args:
            df: Raw particle data
            
        Returns:
            Processed particle data
        """
        logger.info(f"Starting particle processing for {len(df)} particles")
        
        # Make a copy to avoid modifying original data
        processed_df = df.copy()
        
        # Apply processing steps
        processed_df = self.exclude_polymers(processed_df)
        processed_df = self.amplify_particles(processed_df)
        processed_df = self.calculate_geometric_mean_size(processed_df)
        processed_df = self.apply_size_filter(processed_df)
        processed_df = self.standardize_shape_color(processed_df)
        processed_df = self.set_particle_id_as_index(processed_df)
        
        logger.info(f"Processing complete. {len(processed_df)} particles remaining")
        
        return processed_df
        
    def exclude_polymers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove particles with excluded polymer types.
        
        Args:
            df: Particle data
            
        Returns:
            Filtered particle data
        """
        initial_count = len(df)
        
        # Filter by polymer type
        polymer_mask = ~df[self.column_mapping.polymer_type].isin(self.config.excluded_polymers)
        
        # Also filter by library entry if available
        if self.column_mapping.library_entry in df.columns:
            library_mask = ~df[self.column_mapping.library_entry].isin(self.config.excluded_polymers)
            polymer_mask = polymer_mask & library_mask
            
        df_filtered = df[polymer_mask].copy()
        
        excluded_count = initial_count - len(df_filtered)
        logger.info(f"Excluded {excluded_count} particles due to polymer type filtering")
        
        return df_filtered
        
    def amplify_particles(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Amplify particles based on analyzed fraction to extrapolate to whole sample.
        
        Args:
            df: Particle data
            
        Returns:
            Amplified particle data
        """
        if self.column_mapping.fraction_analysed not in df.columns:
            logger.warning("Fraction analysed column not found. Skipping particle amplification.")
            return df
            
        # Fill NaN values with 1 (assuming whole sample analyzed)
        df[self.column_mapping.fraction_analysed].fillna(1.0, inplace=True)
        
        # Calculate amplification factor
        amplification_factor = 1.0 / df[self.column_mapping.fraction_analysed]
        
        # Round to nearest integer (can't have fractional particles)
        amplification_factor = amplification_factor.round().astype(int)
        
        # Replicate particles based on amplification factor
        amplified_particles = []
        
        for idx, factor in amplification_factor.items():
            particle_row = df.loc[idx]
            for rep in range(factor):
                new_particle = particle_row.copy()
                # Create unique particle ID
                if rep > 0:  # Keep original ID for first replica
                    new_particle[self.column_mapping.particle_id] = f"{particle_row[self.column_mapping.particle_id]}_{rep}"
                amplified_particles.append(new_particle)
                
        if amplified_particles:
            amplified_df = pd.DataFrame(amplified_particles)
            logger.info(f"Amplified {len(df)} particles to {len(amplified_df)} particles")
            return amplified_df
        else:
            return df
            
    def calculate_geometric_mean_size(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate geometric mean of particle dimensions.
        
        Args:
            df: Particle data
            
        Returns:
            Data with geometric mean size column
        """
        size_1 = df[self.column_mapping.size_1]
        size_2 = df[self.column_mapping.size_2]
        
        # Calculate geometric mean, handling zero/negative values
        df['size_geom_mean'] = np.sqrt(np.maximum(size_1 * size_2, 0.01))
        
        logger.debug("Calculated geometric mean sizes")
        
        return df
        
    def apply_size_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter particles by size range.
        
        Args:
            df: Particle data
            
        Returns:
            Size-filtered particle data
        """
        initial_count = len(df)
        
        # Get the dimension to filter on
        filter_dimension = self.config.size_filter_dimension
        
        if filter_dimension not in df.columns:
            logger.warning(f"Size filter dimension '{filter_dimension}' not found. Skipping size filtering.")
            return df
            
        # Apply size filters
        size_mask = (
            (df[filter_dimension] >= self.config.size_filter_highpass) &
            (df[filter_dimension] < self.config.size_filter_lowpass)
        )
        
        df_filtered = df[size_mask].copy()
        
        filtered_count = initial_count - len(df_filtered)
        logger.info(f"Size filtering: removed {filtered_count} particles "
                   f"(kept particles {self.config.size_filter_highpass}-{self.config.size_filter_lowpass} μm)")
        
        return df_filtered
        
    def standardize_shape_color(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize shape and color categories.
        
        Args:
            df: Particle data
            
        Returns:
            Data with standardized shape and color
        """
        # Standardize colors
        if self.column_mapping.color in df.columns:
            df[self.column_mapping.color] = df[self.column_mapping.color].replace(
                self.config.color_standardization
            )
            
        # Standardize shapes
        if self.column_mapping.shape in df.columns:
            df[self.column_mapping.shape] = df[self.column_mapping.shape].replace(
                self.config.shape_standardization
            )
            
        logger.debug("Applied shape and color standardization")
        
        return df
        
    def set_particle_id_as_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set particle ID as DataFrame index.
        
        Args:
            df: Particle data
            
        Returns:
            Data with particle ID as index
        """
        if self.column_mapping.particle_id in df.columns:
            df = df.set_index(self.column_mapping.particle_id)
            
        return df
        
    def separate_sample_types(self, df: pd.DataFrame, 
                            sample_types: dict) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Separate particles into environmental, blank, and blind samples.
        
        Args:
            df: Processed particle data
            sample_types: Dictionary mapping sample names to types
            
        Returns:
            Tuple of (environmental_particles, blank_particles, blind_particles)
        """
        sample_col = self.column_mapping.sample_name
        
        # Create masks for different sample types
        env_mask = df[sample_col].map(sample_types) == 'environmental'
        blank_mask = df[sample_col].map(sample_types) == 'blank'
        blind_mask = df[sample_col].map(sample_types) == 'blind'
        
        env_particles = df[env_mask].copy()
        blank_particles = df[blank_mask].copy()
        blind_particles = df[blind_mask].copy()
        
        # Rename size column for blank particles to distinguish it
        if len(blank_particles) > 0:
            blank_particles = blank_particles.rename(columns={'size_geom_mean': 'blank_size_geom_mean'})
            
        # Rename size column for blind particles
        if len(blind_particles) > 0:
            blind_particles = blind_particles.rename(columns={'size_geom_mean': 'blind_size_geom_mean'})
            
        logger.info(f"Separated particles: {len(env_particles)} environmental, "
                   f"{len(blank_particles)} blank, {len(blind_particles)} blind")
        
        return env_particles, blank_particles, blind_particles
