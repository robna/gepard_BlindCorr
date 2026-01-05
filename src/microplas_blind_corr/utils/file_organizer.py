"""
File organization utilities for multi-file microplastics workflows.

This module provides helper functions to organize and validate
Excel files for environmental, blank, and blind samples.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging

from ..config.settings import ColumnMapping


logger = logging.getLogger(__name__)


class FileOrganizer:
    """Helper class for organizing microplastics Excel files."""
    
    def __init__(self, column_mapping: ColumnMapping):
        """
        Initialize the file organizer.
        
        Args:
            column_mapping: Column mapping configuration
        """
        self.column_mapping = column_mapping
        
    def organize_files_by_pattern(self, 
                                 data_directory: Path,
                                 env_patterns: List[str] = None,
                                 blank_patterns: List[str] = None,
                                 blind_patterns: List[str] = None) -> Dict[str, List[Path]]:
        """
        Automatically organize Excel files based on filename patterns.
        
        Args:
            data_directory: Directory containing Excel files
            env_patterns: Patterns to identify environmental sample files
            blank_patterns: Patterns to identify blank sample files
            blind_patterns: Patterns to identify blind sample files
            
        Returns:
            Dictionary with categorized file paths
        """
        if env_patterns is None:
            env_patterns = ['sample', 'environmental', 'env', 'sediment', 'water', 'biota']
        if blank_patterns is None:
            blank_patterns = ['blank', 'control']
        if blind_patterns is None:
            blind_patterns = ['blind', 'spike']
            
        data_dir = Path(data_directory)
        
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
            
        # Find all Excel files
        excel_files = list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.xls"))
        
        categorized_files = {
            'environmental': [],
            'blank': [],
            'blind': [],
            'unclassified': []
        }
        
        for file_path in excel_files:
            file_name_lower = file_path.name.lower()
            
            # Check file type based on patterns
            file_type = 'unclassified'
            
            # Check for blank patterns first (most specific)
            for pattern in blank_patterns:
                if pattern.lower() in file_name_lower:
                    file_type = 'blank'
                    break
                    
            # Check for blind patterns 
            if file_type == 'unclassified':
                for pattern in blind_patterns:
                    if pattern.lower() in file_name_lower:
                        file_type = 'blind'
                        break
                        
            # Check for environmental patterns
            if file_type == 'unclassified':
                for pattern in env_patterns:
                    if pattern.lower() in file_name_lower:
                        file_type = 'environmental'
                        break
                        
            # If still unclassified and it's an Excel file containing "particle",
            # assume it's environmental (default for particle data files)
            if file_type == 'unclassified':
                if any(keyword in file_name_lower for keyword in ['particle', 'particles']):
                    file_type = 'environmental'
                        
            categorized_files[file_type].append(file_path)
            
        # Log results
        for file_type, files in categorized_files.items():
            if files:
                logger.info(f"Found {len(files)} {file_type} files")
                
        return categorized_files
        
    def validate_file_structure(self, file_path: Path) -> Dict[str, any]:
        """
        Validate that an Excel file has the expected structure.
        
        Args:
            file_path: Path to Excel file to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': False,
            'file_path': file_path,
            'errors': [],
            'warnings': [],
            'particle_count': 0,
            'columns_found': [],
            'missing_columns': []
        }
        
        try:
            # Try to read the file
            df = pd.read_excel(file_path)
            validation_result['particle_count'] = len(df)
            validation_result['columns_found'] = df.columns.tolist()
            
            # Check for required columns (using original column names)
            required_columns = [
                'Spectrum ID',  # or whatever the ID column is called
                'Polymer Type',
                'Color', 
                'Shape',
                'Long Size (µm)',
                'Short Size (µm)'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            validation_result['missing_columns'] = missing_columns
            
            if missing_columns:
                validation_result['errors'].append(f"Missing required columns: {missing_columns}")
            else:
                validation_result['valid'] = True
                
            # Check for empty file
            if len(df) == 0:
                validation_result['warnings'].append("File contains no particle data")
                
            # Check for missing values in critical columns
            critical_columns = ['Polymer Type', 'Long Size (µm)', 'Short Size (µm)']
            for col in critical_columns:
                if col in df.columns:
                    null_count = df[col].isnull().sum()
                    if null_count > 0:
                        validation_result['warnings'].append(
                            f"Column '{col}' has {null_count} missing values"
                        )
                        
        except Exception as e:
            validation_result['errors'].append(f"Error reading file: {str(e)}")
            
        return validation_result
        
    def validate_file_set(self, file_paths: List[Path]) -> Dict[str, any]:
        """
        Validate a set of Excel files for consistency.
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Dictionary with overall validation results
        """
        overall_result = {
            'valid': True,
            'total_files': len(file_paths),
            'valid_files': 0,
            'invalid_files': 0,
            'total_particles': 0,
            'file_results': [],
            'consistency_issues': []
        }
        
        if not file_paths:
            overall_result['valid'] = False
            overall_result['consistency_issues'].append("No files provided")
            return overall_result
            
        column_sets = []
        
        for file_path in file_paths:
            file_result = self.validate_file_structure(file_path)
            overall_result['file_results'].append(file_result)
            
            if file_result['valid']:
                overall_result['valid_files'] += 1
                overall_result['total_particles'] += file_result['particle_count']
                column_sets.append(set(file_result['columns_found']))
            else:
                overall_result['invalid_files'] += 1
                overall_result['valid'] = False
                
        # Check column consistency across files
        if column_sets:
            reference_columns = column_sets[0]
            for i, columns in enumerate(column_sets[1:], 1):
                if columns != reference_columns:
                    overall_result['consistency_issues'].append(
                        f"File {i+1} has different columns than file 1"
                    )
                    
        return overall_result
        
    def suggest_file_organization(self, data_directory: Path) -> str:
        """
        Suggest an organization strategy for files in a directory.
        
        Args:
            data_directory: Directory to analyze
            
        Returns:
            String with organization suggestions
        """
        try:
            categorized = self.organize_files_by_pattern(data_directory)
            
            suggestions = []
            suggestions.append("📁 File Organization Suggestions:")
            suggestions.append("")
            
            for file_type, files in categorized.items():
                if files:
                    suggestions.append(f"{file_type.title()} files ({len(files)}):")
                    for file_path in files[:5]:  # Show first 5
                        suggestions.append(f"  - {file_path.name}")
                    if len(files) > 5:
                        suggestions.append(f"  ... and {len(files) - 5} more")
                    suggestions.append("")
                    
            if categorized['unclassified']:
                suggestions.append("⚠️  Unclassified files found. Consider renaming them to include:")
                suggestions.append("  - 'sample' or 'environmental' for environmental samples")
                suggestions.append("  - 'blank' for blank/control samples") 
                suggestions.append("  - 'blind' for blind/spike samples")
                suggestions.append("")
                
            suggestions.append("💡 Recommended file naming convention:")
            suggestions.append("  - Environmental: sample_001_particles.xlsx, sample_002_particles.xlsx")
            suggestions.append("  - Blanks: blank_001_particles.xlsx, blank_002_particles.xlsx")
            suggestions.append("  - Blinds: blind_001_particles.xlsx, blind_002_particles.xlsx")
            
            return "\n".join(suggestions)
            
        except Exception as e:
            return f"Error analyzing directory: {e}"
            
    def create_sample_mapping(self, file_paths: List[Path], 
                            sample_names: List[str] = None) -> Dict[Path, str]:
        """
        Create a mapping between file paths and sample names.
        
        Args:
            file_paths: List of file paths
            sample_names: Optional list of sample names (if None, uses filenames)
            
        Returns:
            Dictionary mapping file paths to sample names
        """
        if sample_names is not None and len(sample_names) != len(file_paths):
            raise ValueError("Number of sample names must match number of file paths")
            
        mapping = {}
        
        for i, file_path in enumerate(file_paths):
            if sample_names:
                sample_name = sample_names[i]
            else:
                # Use filename without extension as sample name
                sample_name = file_path.stem
                
            mapping[file_path] = sample_name
            
        return mapping
