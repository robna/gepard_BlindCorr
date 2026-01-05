"""
Utility functions for microplastics data processing.

This module provides various helper functions for data validation,
visualization preparation, and result export.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Union
import logging

from ..config.settings import ColumnMapping


logger = logging.getLogger(__name__)


def validate_dataframe_structure(df: pd.DataFrame, 
                                column_mapping: ColumnMapping,
                                required_columns: List[str] = None) -> bool:
    """
    Validate that a DataFrame has the expected structure for processing.
    
    Args:
        df: DataFrame to validate
        column_mapping: Expected column mapping
        required_columns: List of required column names (if None, uses defaults)
        
    Returns:
        True if valid, raises ValueError if not
    """
    if required_columns is None:
        required_columns = [
            column_mapping.sample_name,
            column_mapping.polymer_type,
            column_mapping.color,
            column_mapping.shape,
            column_mapping.size_1,
            column_mapping.size_2
        ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"DataFrame missing required columns: {missing_columns}")
        
    # Check for empty DataFrame
    if len(df) == 0:
        raise ValueError("DataFrame is empty")
        
    # Check for critical missing values
    critical_columns = [column_mapping.polymer_type, column_mapping.size_1, column_mapping.size_2]
    for col in critical_columns:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                logger.warning(f"Column {col} has {null_count} null values")
                
    return True


def calculate_particle_statistics(df: pd.DataFrame, 
                                column_mapping: ColumnMapping,
                                group_by: List[str] = None) -> pd.DataFrame:
    """
    Calculate summary statistics for particle data.
    
    Args:
        df: Particle data
        column_mapping: Column mapping
        group_by: Columns to group by (default: sample_name)
        
    Returns:
        DataFrame with summary statistics
    """
    if group_by is None:
        group_by = [column_mapping.sample_name]
        
    # Ensure size_geom_mean exists
    if 'size_geom_mean' not in df.columns and all(col in df.columns for col in [column_mapping.size_1, column_mapping.size_2]):
        df['size_geom_mean'] = np.sqrt(df[column_mapping.size_1] * df[column_mapping.size_2])
        
    stats_functions = {
        'particle_count': 'count',
        'mean_size': 'mean',
        'median_size': 'median', 
        'std_size': 'std',
        'min_size': 'min',
        'max_size': 'max'
    }
    
    if 'size_geom_mean' in df.columns:
        stats = df.groupby(group_by)['size_geom_mean'].agg(**stats_functions)
    else:
        stats = df.groupby(group_by)[column_mapping.size_1].agg(**stats_functions)
        logger.warning("Using size_1 for statistics as size_geom_mean not available")
        
    # Add polymer type counts
    polymer_counts = df.groupby(group_by)[column_mapping.polymer_type].nunique().rename('unique_polymers')
    
    # Add color counts
    color_counts = df.groupby(group_by)[column_mapping.color].nunique().rename('unique_colors')
    
    # Add shape counts  
    shape_counts = df.groupby(group_by)[column_mapping.shape].nunique().rename('unique_shapes')
    
    # Combine all statistics
    combined_stats = pd.concat([stats, polymer_counts, color_counts, shape_counts], axis=1)
    
    return combined_stats


def export_results(df: pd.DataFrame, 
                  output_path: Union[str, Path],
                  format: str = 'excel') -> None:
    """
    Export processed particle data to file.
    
    Args:
        df: Processed particle data
        output_path: Path for output file
        format: Output format ('excel', 'csv')
    """
    output_path = Path(output_path)
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format.lower() == 'excel':
        df.to_excel(output_path, index=True)
    elif format.lower() == 'csv':
        df.to_csv(output_path, index=True)
    else:
        raise ValueError(f"Unsupported format: {format}")
        
    logger.info(f"Exported {len(df)} particles to {output_path}")


def generate_processing_report(original_data: pd.DataFrame,
                             processed_data: pd.DataFrame,
                             blank_elimination_log: pd.DataFrame = None,
                             blind_elimination_log: pd.DataFrame = None,
                             column_mapping: ColumnMapping = None) -> Dict:
    """
    Generate a comprehensive processing report.
    
    Args:
        original_data: Original particle data before processing
        processed_data: Final processed particle data
        blank_elimination_log: Log of particles eliminated by blank correction
        blind_elimination_log: Log of particles eliminated by blind correction
        column_mapping: Column mapping used
        
    Returns:
        Dictionary with processing report
    """
    report = {
        'processing_summary': {
            'original_particle_count': len(original_data),
            'final_particle_count': len(processed_data),
            'total_eliminated': len(original_data) - len(processed_data),
            'retention_rate': len(processed_data) / len(original_data) if len(original_data) > 0 else 0
        }
    }
    
    # Sample-level statistics
    if column_mapping and column_mapping.sample_name in original_data.columns:
        original_by_sample = original_data[column_mapping.sample_name].value_counts()
        processed_by_sample = processed_data[column_mapping.sample_name].value_counts()
        
        report['sample_summary'] = {
            'original_samples': len(original_by_sample),
            'processed_samples': len(processed_by_sample),
            'particles_per_sample_original': original_by_sample.to_dict(),
            'particles_per_sample_processed': processed_by_sample.to_dict()
        }
    
    # Blank correction summary
    if blank_elimination_log is not None and len(blank_elimination_log) > 0:
        report['blank_correction'] = {
            'particles_eliminated': len(blank_elimination_log),
            'elimination_by_polymer': blank_elimination_log['polymer_type'].value_counts().to_dict(),
            'elimination_by_sample': blank_elimination_log['sample_name'].value_counts().to_dict()
        }
    
    # Blind correction summary  
    if blind_elimination_log is not None and len(blind_elimination_log) > 0:
        report['blind_correction'] = {
            'particles_eliminated': len(blind_elimination_log),
            'elimination_by_polymer': blind_elimination_log['polymer_type'].value_counts().to_dict(),
            'elimination_by_sample': blind_elimination_log['sample_name'].value_counts().to_dict()
        }
    
    return report


def detect_outliers_by_size(df: pd.DataFrame, 
                           size_column: str = 'size_geom_mean',
                           method: str = 'iqr',
                           factor: float = 1.5) -> pd.DataFrame:
    """
    Detect size outliers in particle data.
    
    Args:
        df: Particle data
        size_column: Column to use for outlier detection
        method: Method to use ('iqr' or 'zscore')  
        factor: Factor for outlier detection (1.5 for IQR, 3 for z-score)
        
    Returns:
        DataFrame with outlier flags
    """
    df_with_outliers = df.copy()
    
    if size_column not in df.columns:
        logger.warning(f"Size column {size_column} not found")
        df_with_outliers['is_outlier'] = False
        return df_with_outliers
    
    if method == 'iqr':
        Q1 = df[size_column].quantile(0.25)
        Q3 = df[size_column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR
        
        df_with_outliers['is_outlier'] = (
            (df[size_column] < lower_bound) | 
            (df[size_column] > upper_bound)
        )
        
    elif method == 'zscore':
        mean_size = df[size_column].mean()
        std_size = df[size_column].std()
        z_scores = np.abs((df[size_column] - mean_size) / std_size)
        
        df_with_outliers['is_outlier'] = z_scores > factor
        
    else:
        raise ValueError(f"Unknown outlier detection method: {method}")
    
    outlier_count = df_with_outliers['is_outlier'].sum()
    logger.info(f"Detected {outlier_count} size outliers using {method} method")
    
    return df_with_outliers


def create_size_bins(df: pd.DataFrame,
                    size_column: str = 'size_geom_mean', 
                    bins: List[float] = None) -> pd.DataFrame:
    """
    Create size bins for particle data analysis.
    
    Args:
        df: Particle data
        size_column: Column to bin
        bins: Bin edges (if None, uses default microplastics size classes)
        
    Returns:
        DataFrame with size bin column
    """
    if bins is None:
        # Default microplastics size classes
        bins = [0, 5, 10, 20, 50, 100, 1000, np.inf]
        
    bin_labels = [f"{bins[i]}-{bins[i+1]} μm" for i in range(len(bins)-1)]
    bin_labels[-1] = f">{bins[-2]} μm"  # Last bin is open-ended
    
    df_with_bins = df.copy()
    
    if size_column in df.columns:
        df_with_bins['size_bin'] = pd.cut(
            df[size_column], 
            bins=bins,
            labels=bin_labels,
            include_lowest=True
        )
    else:
        logger.warning(f"Size column {size_column} not found")
        df_with_bins['size_bin'] = 'Unknown'
        
    return df_with_bins
