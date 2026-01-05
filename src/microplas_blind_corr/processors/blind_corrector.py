"""
Blind correction processor.

This module implements the blind correction procedure to validate method
quality by removing particles that match those found in blind samples.
"""

import pandas as pd
from typing import Tuple
import logging

from ..config.settings import ColumnMapping


logger = logging.getLogger(__name__)


class BlindCorrector:
    """Processor for blind correction of particle data."""
    
    def __init__(self, column_mapping: ColumnMapping):
        """
        Initialize the blind corrector.
        
        Args:
            column_mapping: Column name mapping
        """
        self.column_mapping = column_mapping
        
    def create_synthetic_blind(self, blind_particles: pd.DataFrame) -> pd.DataFrame:
        """
        Create a synthetic blind sample from multiple blind samples.
        
        This combines particles from all blind samples, but only includes
        every nth particle (where n = number of blind samples) to avoid
        over-representation.
        
        Args:
            blind_particles: All blind sample particles
            
        Returns:
            Synthetic blind sample
        """
        if len(blind_particles) == 0:
            logger.warning("No blind particles provided")
            return pd.DataFrame()
            
        sample_col = 'sample_name'
        polymer_col = 'polymer_type'
        color_col = 'color'
        shape_col = 'shape'
        
        # Count unique blind samples
        num_blind_samples = blind_particles[sample_col].nunique()
        logger.info(f"Creating synthetic blind from {num_blind_samples} blind samples")
        
        if num_blind_samples == 0:
            return pd.DataFrame()
            
        # Group by phenotype (polymer, color, shape)
        phenotype_groups = blind_particles.groupby([polymer_col, color_col, shape_col])
        
        synthetic_blind_particles = []
        
        for phenotype, group in phenotype_groups:
            # Sort by size to maintain size distribution
            sorted_group = group.sort_values('blind_size_geom_mean', ascending=False)
            
            # Take every nth particle where n = number of blind samples
            selected_particles = sorted_group.iloc[::num_blind_samples]
            
            synthetic_blind_particles.append(selected_particles)
            
        if synthetic_blind_particles:
            synthetic_blind = pd.concat(synthetic_blind_particles, ignore_index=False)
            logger.info(f"Created synthetic blind with {len(synthetic_blind)} particles")
        else:
            synthetic_blind = pd.DataFrame()
            
        return synthetic_blind
        
    def apply_blind_correction(self, environmental_particles: pd.DataFrame,
                             synthetic_blind: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply blind correction to validate method quality.
        
        This procedure identifies particles in environmental samples that match
        particles found in the synthetic blind sample and removes them to assess
        method contamination.
        
        Args:
            environmental_particles: Environmental sample particles  
            synthetic_blind: Synthetic blind sample particles
            
        Returns:
            Tuple of (corrected_environmental_particles, elimination_log)
        """
        logger.info(f"Starting blind correction with {len(environmental_particles)} environmental "
                   f"and {len(synthetic_blind)} synthetic blind particles")
        
        env_particles_copy = environmental_particles.copy()
        elimination_log = pd.DataFrame(columns=[
            'blind_particle_id',
            'blind_sample_name',
            'eliminated_particle_id',
            'sample_name', 
            'polymer_type',
            'color',
            'shape',
            'size_difference'
        ])
        
        total_eliminated = 0
        
        # Process each environmental sample separately
        sample_col = 'sample_name'
        
        for sample_name, sample_group in environmental_particles.groupby(sample_col):
            eliminated_in_sample = 0
            
            # For each blind particle, try to find a match in this sample
            for blind_id, blind_particle in synthetic_blind.iterrows():
                matching_particles = self._find_matching_particles(
                    sample_group, blind_particle
                )
                
                if len(matching_particles) > 0:
                    # Find the particle with smallest size difference
                    eliminated_particle_id = self._find_closest_particle(
                        matching_particles, blind_particle
                    )
                    
                    # Check if particle still exists (might have been eliminated already)
                    if eliminated_particle_id in env_particles_copy.index:
                        # Log the elimination
                        elimination_record = {
                            'blind_particle_id': blind_id,
                            'blind_sample_name': blind_particle[sample_col],
                            'eliminated_particle_id': eliminated_particle_id,
                            'sample_name': sample_name,
                            'polymer_type': blind_particle['polymer_type'],
                            'color': blind_particle['color'],
                            'shape': blind_particle['shape'],
                            'size_difference': abs(
                                env_particles_copy.loc[eliminated_particle_id, 'size_geom_mean'] - 
                                blind_particle['blind_size_geom_mean']
                            )
                        }
                        
                        elimination_log = pd.concat([
                            elimination_log,
                            pd.DataFrame([elimination_record])
                        ], ignore_index=True)
                        
                        # Remove the particle from environmental dataset
                        env_particles_copy = env_particles_copy.drop(eliminated_particle_id)
                        sample_group = sample_group.drop(eliminated_particle_id)
                        eliminated_in_sample += 1
                        
                        logger.debug(f"Eliminated particle {eliminated_particle_id} from {sample_name}")
                        
            logger.info(f"Eliminated {eliminated_in_sample} particles from sample {sample_name}")
            total_eliminated += eliminated_in_sample
            
        logger.info(f"Blind correction complete. Total eliminated: {total_eliminated} particles.")
        
        return env_particles_copy, elimination_log
        
    def _find_matching_particles(self, sample_particles: pd.DataFrame,
                               blind_particle: pd.Series) -> pd.DataFrame:
        """
        Find particles in a sample that match a blind particle in polymer, color, and shape.
        
        Args:
            sample_particles: Particles from one environmental sample
            blind_particle: Single blind particle
            
        Returns:
            DataFrame of matching particles
        """
        polymer_col = 'polymer_type'
        color_col = 'color'  
        shape_col = 'shape'
        
        # Create matching criteria
        matching_mask = (
            (sample_particles[polymer_col] == blind_particle[polymer_col]) &
            (sample_particles[color_col] == blind_particle[color_col]) &
            (sample_particles[shape_col] == blind_particle[shape_col])
        )
        
        matching_particles = sample_particles[matching_mask].copy()
        
        # Add size difference for sorting
        if len(matching_particles) > 0:
            matching_particles['size_diff'] = abs(
                matching_particles['size_geom_mean'] - blind_particle['blind_size_geom_mean']
            )
            
        return matching_particles
        
    def _find_closest_particle(self, matching_particles: pd.DataFrame,
                             blind_particle: pd.Series) -> str:
        """
        Find the particle with the smallest size difference to the blind particle.
        
        Args:
            matching_particles: Particles that match in polymer/color/shape
            blind_particle: Blind particle to compare against
            
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
        Generate summary statistics for the blind correction.
        
        Args:
            elimination_log: Log of eliminated particles
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_eliminated': len(elimination_log),
            'eliminated_by_sample': elimination_log['sample_name'].value_counts().to_dict(),
            'eliminated_by_blind_sample': elimination_log['blind_sample_name'].value_counts().to_dict(),
            'eliminated_by_polymer': elimination_log['polymer_type'].value_counts().to_dict(),
            'eliminated_by_color': elimination_log['color'].value_counts().to_dict(),
            'eliminated_by_shape': elimination_log['shape'].value_counts().to_dict(),
            'mean_size_difference': elimination_log['size_difference'].mean() if len(elimination_log) > 0 else 0,
            'median_size_difference': elimination_log['size_difference'].median() if len(elimination_log) > 0 else 0
        }
        
        return summary
