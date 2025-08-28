"""
Excel data loader for microplastics particle data.

This module provides functionality to load particle data from Excel files
and standardize the format for processing.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from ..config.settings import ColumnMapping, EXCEL_COLUMN_MAPPING


logger = logging.getLogger(__name__)


class ExcelLoader:
    """Loads microplastics particle data from Excel files."""
    
    def __init__(self, column_mapping: ColumnMapping = EXCEL_COLUMN_MAPPING):
        """
        Initialize the Excel loader.
        
        Args:
            column_mapping: Mapping between file columns and standardized names
        """
        self.column_mapping = column_mapping
        
    def load_sample(self, file_path: Union[str, Path], sample_name: Optional[str] = None) -> pd.DataFrame:
        """
        Load particle data from a single Excel file.
        
        Args:
            file_path: Path to the Excel file
            sample_name: Name to assign to the sample (if None, uses filename)
            
        Returns:
            DataFrame with standardized column names
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        logger.info(f"Loading particle data from {file_path}")
        
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise ValueError(f"Error reading Excel file {file_path}: {e}")
            
        # Use filename as sample name if not provided
        if sample_name is None:
            sample_name = file_path.stem
            
        # Add sample name column
        df[self.column_mapping.sample_name] = sample_name
        
        # Standardize column names
        df = self._standardize_columns(df)
        
        # Validate required columns are present
        self._validate_required_columns(df)
        
        logger.info(f"Loaded {len(df)} particles from sample '{sample_name}'")
        
        return df
        
    def load_multiple_samples(self, file_paths: List[Union[str, Path]], 
                            sample_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load particle data from multiple Excel files.
        
        Args:
            file_paths: List of paths to Excel files
            sample_names: List of sample names (if None, uses filenames)
            
        Returns:
            Combined DataFrame with all samples
        """
        if sample_names is not None and len(sample_names) != len(file_paths):
            raise ValueError("Number of sample names must match number of file paths")
            
        dataframes = []
        
        for i, file_path in enumerate(file_paths):
            sample_name = sample_names[i] if sample_names else None
            df = self.load_sample(file_path, sample_name)
            dataframes.append(df)
            
        combined_df = pd.concat(dataframes, ignore_index=True)
        logger.info(f"Combined {len(dataframes)} samples with {len(combined_df)} total particles")
        
        return combined_df
        
    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns according to the column mapping."""
        # Create reverse mapping to find original column names
        reverse_mapping = {}
        for std_name, attr_name in self.column_mapping.__dict__.items():
            if attr_name in df.columns:
                reverse_mapping[attr_name] = std_name
                
        if reverse_mapping:
            df = df.rename(columns=reverse_mapping)
            logger.debug(f"Renamed columns: {reverse_mapping}")
            
        return df
        
    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """Validate that required columns are present."""
        required_columns = [
            'sample_name',
            'polymer_type',
            'color',
            'shape',
            'size_1',
            'size_2'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
    def get_available_columns(self, file_path: Union[str, Path]) -> List[str]:
        """
        Get list of available columns in an Excel file.
        
        Args:
            file_path: Path to the Excel file
            
        Returns:
            List of column names
        """
        try:
            df = pd.read_excel(file_path, nrows=0)  # Read only headers
            return df.columns.tolist()
        except Exception as e:
            raise ValueError(f"Error reading Excel file headers: {e}")
            
    def detect_sample_type(self, df: pd.DataFrame, 
                          blank_patterns: List[str] = None,
                          blind_patterns: List[str] = None) -> Dict[str, str]:
        """
        Detect sample types (environmental, blank, blind) based on sample names.
        
        Args:
            df: DataFrame with particle data
            blank_patterns: Patterns to identify blank samples
            blind_patterns: Patterns to identify blind samples
            
        Returns:
            Dictionary mapping sample names to types
        """
        if blank_patterns is None:
            blank_patterns = ['blank', 'Blank', 'BLANK']
        if blind_patterns is None:
            blind_patterns = ['blind', 'Blind', 'BLIND']
            
        sample_types = {}
        
        for sample_name in df[self.column_mapping.sample_name].unique():
            sample_type = 'environmental'  # default
            
            # Check if sample is a blank
            for pattern in blank_patterns:
                if pattern in sample_name:
                    sample_type = 'blank'
                    break
                    
            # Check if sample is a blind (takes precedence over blank)
            for pattern in blind_patterns:
                if pattern in sample_name:
                    sample_type = 'blind'
                    break
                    
            sample_types[sample_name] = sample_type
            
        logger.info(f"Detected sample types: {sample_types}")
        
        return sample_types
