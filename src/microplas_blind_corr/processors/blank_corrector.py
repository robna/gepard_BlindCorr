"""
Blank correction processor.

This module implements the blank correction procedure to remove particles
that match those found in laboratory blank samples, indicating potential
contamination.
"""

import pandas as pd
from typing import Tuple
import logging

from ..config.settings import ColumnMapping


logger = logging.getLogger(__name__)


class BlankCorrector:
    """Processor for blank correction of particle data."""
    
    def __init__(self, column_mapping: ColumnMapping):
        """
        Initialize the blank corrector.
        
        Args:
            column_mapping: Column name mapping
        """
        self.column_mapping = column_mapping
        
    def apply_blank_correction(self, environmental_particles: pd.DataFrame, 
                             blank_particles: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply blank correction to remove contamination.
        
        This procedure identifies particles in environmental samples that match
        particles found in corresponding blank samples and removes the most similar
        particle from the environmental dataset.
        
        Args:
            environmental_particles: Environmental sample particles
            blank_particles: Blank sample particles
            
        Returns:
            Tuple of (corrected_environmental_particles, elimination_log)
        """
        logger.info(f"Starting blank correction with {len(environmental_particles)} environmental "
                   f"and {len(blank_particles)} blank particles")
        
        env_particles_copy = environmental_particles.copy()
        elimination_log = pd.DataFrame(columns=[
            'blank_particle_id',
            'eliminated_particle_id', 
            'sample_name',
            'polymer_type',
            'color',
            'shape',
            'size_difference'
        ])
        
        eliminated_count = 0
        
        # Process each blank particle
        for blank_id, blank_particle in blank_particles.iterrows():
            matching_particles = self._find_matching_particles(
                env_particles_copy, blank_particle
            )
            
            if len(matching_particles) > 0:
                # Find the particle with smallest size difference
                eliminated_particle_id = self._find_closest_particle(
                    matching_particles, blank_particle
                )
                
                # Log the elimination
                elimination_record = {
                    'blank_particle_id': blank_id,
                    'eliminated_particle_id': eliminated_particle_id,
                    'sample_name': env_particles_copy.loc[eliminated_particle_id, self.column_mapping.sample_name],
                    'polymer_type': env_particles_copy.loc[eliminated_particle_id, self.column_mapping.polymer_type],
                    'color': env_particles_copy.loc[eliminated_particle_id, self.column_mapping.color],
                    'shape': env_particles_copy.loc[eliminated_particle_id, self.column_mapping.shape],
                    'size_difference': abs(
                        env_particles_copy.loc[eliminated_particle_id, 'size_geom_mean'] - 
                        blank_particle['blank_size_geom_mean']
                    )
                }
                
                elimination_log = pd.concat([
                    elimination_log, 
                    pd.DataFrame([elimination_record])
                ], ignore_index=True)
                
                # Remove the particle from environmental dataset
                env_particles_copy = env_particles_copy.drop(eliminated_particle_id)
                eliminated_count += 1
                
                logger.debug(f"Eliminated particle {eliminated_particle_id} matching blank {blank_id}")
            else:
                logger.debug(f"No matching particles found for blank {blank_id}")
                
        logger.info(f"Blank correction complete. Eliminated {eliminated_count} particles.")
        
        return env_particles_copy, elimination_log
        
    def _find_matching_particles(self, environmental_particles: pd.DataFrame, 
                               blank_particle: pd.Series) -> pd.DataFrame:
        """
        Find environmental particles that match a blank particle in polymer, color, and shape.
        
        Args:
            environmental_particles: Environmental sample particles
            blank_particle: Single blank particle
            
        Returns:
            DataFrame of matching environmental particles
        """
        sample_col = self.column_mapping.sample_name
        polymer_col = self.column_mapping.polymer_type
        color_col = self.column_mapping.color
        shape_col = self.column_mapping.shape
        
        # Create matching criteria
        matching_mask = (
            (environmental_particles[sample_col] == blank_particle[sample_col]) &
            (environmental_particles[polymer_col] == blank_particle[polymer_col]) &
            (environmental_particles[color_col] == blank_particle[color_col]) &
            (environmental_particles[shape_col] == blank_particle[shape_col])
        )
        
        matching_particles = environmental_particles[matching_mask].copy()
        
        # Add size difference for sorting
        if len(matching_particles) > 0:
            matching_particles['size_diff'] = abs(
                matching_particles['size_geom_mean'] - blank_particle['blank_size_geom_mean']
            )
            
        return matching_particles
        
    def _find_closest_particle(self, matching_particles: pd.DataFrame, 
                             blank_particle: pd.Series) -> str:
        """
        Find the particle with the smallest size difference to the blank particle.
        
        Args:
            matching_particles: Particles that match in polymer/color/shape
            blank_particle: Blank particle to compare against
            
        Returns:
            ID of the closest matching particle
        """
        if len(matching_particles) == 0:
            raise ValueError("No matching particles provided")
            
        # Find particle with minimum size difference
        closest_particle_id = matching_particles['size_diff'].idxmin()
        
        return closest_particle_id
        
    def get_correction_summary(self, elimination_log: pd.DataFrame) -> dict:
        """
        Generate summary statistics for the blank correction.
        
        Args:
            elimination_log: Log of eliminated particles
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_eliminated': len(elimination_log),
            'eliminated_by_sample': elimination_log['sample_name'].value_counts().to_dict(),
            'eliminated_by_polymer': elimination_log['polymer_type'].value_counts().to_dict(),
            'eliminated_by_color': elimination_log['color'].value_counts().to_dict(),
            'eliminated_by_shape': elimination_log['shape'].value_counts().to_dict(),
            'mean_size_difference': elimination_log['size_difference'].mean() if len(elimination_log) > 0 else 0,
            'median_size_difference': elimination_log['size_difference'].median() if len(elimination_log) > 0 else 0
        }
        
        return summary
