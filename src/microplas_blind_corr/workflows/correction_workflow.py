"""
Correction workflow manager for particle data processing.

This module handles the complex workflow of applying multiple correction files
to target files in the correct dependency order, including circular dependency
detection and synthetic control creation.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict, deque
import logging

from ..data_loaders.excel_loader import ExcelLoader
from ..processors.particle_processor import ParticleProcessor
from ..processors.blank_corrector import BlankCorrector
from ..processors.blind_corrector import BlindCorrector
from ..config.settings import ProcessingConfig, ColumnMapping
from ..utils.data_utils import export_results
import pandas as pd


logger = logging.getLogger(__name__)


class CorrectionWorkflow:
    """Manages complex particle correction workflows with dependency resolution."""
    
    def __init__(self, config: ProcessingConfig, column_mapping: ColumnMapping):
        """
        Initialize the correction workflow manager.
        
        Args:
            config: Processing configuration
            column_mapping: Column mapping for data loading
        """
        self.config = config
        self.column_mapping = column_mapping
        self.loader = ExcelLoader(column_mapping)
        self.processor = ParticleProcessor(config, column_mapping)
        self.blank_corrector = BlankCorrector(column_mapping, config)
        self.blind_corrector = BlindCorrector(column_mapping)
        
        # Workflow state
        self.correction_config = {}
        self.data_directory = Path("data")
        self.output_directory = Path("output")
        self.loaded_files = {}  # Cache for loaded files
        self.processed_files = {}  # Cache for processed files
        
    def load_correction_config(self, config_file: Path, data_directory: Path = None) -> None:
        """
        Load correction configuration from YAML file.
        
        Args:
            config_file: Path to the YAML configuration file
            data_directory: Directory containing data files (default: 'data')
        """
        if not config_file.exists():
            raise FileNotFoundError(f"Correction configuration file not found: {config_file}")
            
        if data_directory:
            self.data_directory = Path(data_directory)
            
        with open(config_file, 'r') as f:
            self.correction_config = yaml.safe_load(f)
            
        logger.info(f"Loaded correction configuration from {config_file}")
        
        # Validate configuration structure
        self._validate_config()
        
        # Set output settings if specified
        if 'output' in self.correction_config:
            output_settings = self.correction_config['output']
            if 'directory' in output_settings:
                self.output_directory = self.data_directory / output_settings['directory']
                
        # Apply settings to processing config if specified
        if 'settings' in self.correction_config:
            settings = self.correction_config['settings']
            if 'size_matching_dimension' in settings:
                self.config.size_matching_dimension = settings['size_matching_dimension']
                logger.info(f"Using size matching dimension: {self.config.size_matching_dimension}")
                
    def _validate_config(self) -> None:
        """Validate the correction configuration structure."""
        if 'corrections' not in self.correction_config:
            raise ValueError("Configuration must contain 'corrections' section")
            
        corrections = self.correction_config['corrections']
        
        if not isinstance(corrections, dict):
            raise ValueError("'corrections' must be a dictionary")
            
        # Validate each correction entry
        for target_file, control_files in corrections.items():
            if not isinstance(target_file, str):
                raise ValueError(f"Target file names must be strings, got: {type(target_file)}")
                
            if isinstance(control_files, str):
                # Single control file as string
                continue
            elif isinstance(control_files, list):
                # Multiple control files as list
                for control_file in control_files:
                    if not isinstance(control_file, str):
                        raise ValueError(f"Control file names must be strings, got: {type(control_file)}")
            else:
                raise ValueError(f"Control files must be string or list, got: {type(control_files)}")
                
    def detect_circular_dependencies(self) -> List[str]:
        """
        Detect circular dependencies in the correction configuration.
        
        Returns:
            List of error messages describing circular dependencies
        """
        corrections = self.correction_config['corrections']
        errors = []
        
        # Build dependency graph
        dependencies = {}
        for target_file, control_files in corrections.items():
            if isinstance(control_files, str):
                control_files = [control_files]
            dependencies[target_file] = control_files
            
        # Check for circular dependencies using DFS
        def has_cycle(node: str, visiting: Set[str], visited: Set[str]) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
                
            visiting.add(node)
            
            # Check dependencies of this node
            if node in dependencies:
                for dep in dependencies[node]:
                    if has_cycle(dep, visiting, visited):
                        return True
                        
            visiting.remove(node)
            visited.add(node)
            return False
            
        visited = set()
        for target_file in dependencies:
            if target_file not in visited:
                visiting = set()
                if has_cycle(target_file, visiting, visited):
                    errors.append(f"Circular dependency detected involving: {target_file}")
                    
        # Check for direct self-dependencies
        for target_file, control_files in corrections.items():
            if isinstance(control_files, str):
                control_files = [control_files]
            if target_file in control_files:
                errors.append(f"File cannot correct itself: {target_file}")
                
        return errors
        
    def resolve_processing_order(self) -> List[Tuple[str, List[str]]]:
        """
        Resolve the correct processing order based on dependencies.
        
        Returns:
            List of (target_file, control_files) tuples in processing order
        """
        corrections = self.correction_config['corrections']
        
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        all_files = set()
        
        for target_file, control_files in corrections.items():
            if isinstance(control_files, str):
                control_files = [control_files]
                
            all_files.add(target_file)
            all_files.update(control_files)
            
            for control_file in control_files:
                if control_file in corrections:  # Control file is also a target
                    graph[control_file].append(target_file)
                    in_degree[target_file] += 1
                    
        # Initialize in_degree for all files
        for file in all_files:
            if file not in in_degree:
                in_degree[file] = 0
                
        # Topological sort
        queue = deque([file for file in all_files if in_degree[file] == 0])
        processing_order = []
        
        while queue:
            current_file = queue.popleft()
            
            # Add to processing order if it's a target file
            if current_file in corrections:
                control_files = corrections[current_file]
                if isinstance(control_files, str):
                    control_files = [control_files]
                processing_order.append((current_file, control_files))
                
            # Update in_degrees of dependent files
            for dependent in graph[current_file]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    
        logger.info(f"Resolved processing order for {len(processing_order)} correction steps")
        return processing_order
        
    def _resolve_file_path(self, filename: str) -> Path:
        """
        Resolve a filename to a full path.
        
        Args:
            filename: Filename or path
            
        Returns:
            Resolved Path object
        """
        file_path = Path(filename)
        
        if file_path.is_absolute():
            return file_path
        elif "/" in filename or "\\" in filename:
            # Relative path
            return self.data_directory / file_path
        else:
            # Just filename
            return self.data_directory / filename
            
    def _load_file(self, filename: str) -> pd.DataFrame:
        """
        Load a file with caching.
        
        Args:
            filename: Name or path of file to load
            
        Returns:
            Loaded DataFrame
        """
        if filename in self.loaded_files:
            return self.loaded_files[filename].copy()
            
        file_path = self._resolve_file_path(filename)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
            
        logger.info(f"Loading file: {file_path}")
        data = self.loader.load_sample(file_path, filename)
        self.loaded_files[filename] = data
        
        return data.copy()
        
    def _get_processed_file(self, filename: str) -> pd.DataFrame:
        """
        Get processed version of a file, processing if necessary.
        
        Args:
            filename: Name of file to get processed version of
            
        Returns:
            Processed DataFrame
        """
        if filename in self.processed_files:
            return self.processed_files[filename].copy()
            
        # Load and process file
        data = self._load_file(filename)
        processed_data = self.processor.process_particles(data)
        
        self.processed_files[filename] = processed_data
        logger.info(f"Processed file: {filename} ({len(processed_data)} particles)")
        
        return processed_data.copy()
        
    def _save_corrected_file(self, data: pd.DataFrame, original_filename: str) -> Path:
        """
        Save corrected data to output file.
        
        Args:
            data: Corrected particle data
            original_filename: Original filename
            
        Returns:
            Path to saved file
        """
        # Get output settings
        output_settings = self.correction_config.get('output', {})
        suffix = output_settings.get('suffix', '_corrected')
        format_type = output_settings.get('format', 'excel')
        
        # Map format types to file extensions
        format_extensions = {
            'excel': 'xlsx',
            'csv': 'csv'
        }
        
        # Get the correct file extension
        file_extension = format_extensions.get(format_type, format_type)
        
        # Create output filename
        original_path = Path(original_filename)
        output_filename = f"{original_path.stem}{suffix}.{file_extension}"
        output_path = self.output_directory / output_filename
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export file
        export_results(data, output_path, format_type)
        
        return output_path
        
    def run_workflow(self) -> Dict[str, Any]:
        """
        Run the complete correction workflow.
        
        Returns:
            Dictionary with workflow results and statistics
        """
        logger.info("Starting correction workflow")
        
        # Check for circular dependencies
        circular_errors = self.detect_circular_dependencies()
        if circular_errors:
            error_msg = "Circular dependencies detected:\n" + "\n".join(circular_errors)
            raise ValueError(error_msg)
            
        # Resolve processing order
        processing_order = self.resolve_processing_order()
        
        if not processing_order:
            raise ValueError("No valid corrections found in configuration")
            
        # Process corrections in order
        results = {
            'processed_files': [],
            'total_corrections': 0,
            'total_particles_eliminated': 0,
            'correction_logs': []
        }
        
        for target_file, control_files in processing_order:
            logger.info(f"Processing correction: {target_file} ← {control_files}")
            
            # Get processed target data
            target_data = self._get_processed_file(target_file)
            original_particle_count = len(target_data)
            
            if len(control_files) == 1:
                # Single control file
                control_data = self._get_processed_file(control_files[0])
                
                corrected_data, elimination_log = self.blank_corrector.apply_blank_correction(
                    target_data, control_data
                )
                
            else:
                # Multiple control files - create synthetic control
                control_datasets = []
                for control_file in control_files:
                    control_data = self._get_processed_file(control_file)
                    
                    # Rename size column for blind correction if it exists
                    if 'size_geom_mean' in control_data.columns:
                        control_data = control_data.rename(columns={'size_geom_mean': 'blind_size_geom_mean'})
                        
                    control_datasets.append(control_data)
                    
                # Combine control datasets
                combined_controls = pd.concat(control_datasets, ignore_index=True)
                
                # Create synthetic control
                synthetic_control = self.blind_corrector.create_synthetic_blind(combined_controls)
                
                # Apply correction
                corrected_data, elimination_log = self.blind_corrector.apply_blind_correction(
                    target_data, synthetic_control
                )
                
            # Update processed files cache with corrected data
            self.processed_files[target_file] = corrected_data
            
            # Save corrected file
            output_path = self._save_corrected_file(corrected_data, target_file)
            
            # Record results
            particles_eliminated = original_particle_count - len(corrected_data)
            correction_result = {
                'target_file': target_file,
                'control_files': control_files,
                'original_particles': original_particle_count,
                'final_particles': len(corrected_data),
                'particles_eliminated': particles_eliminated,
                'output_file': str(output_path),
                'elimination_log': elimination_log
            }
            
            results['processed_files'].append(correction_result)
            results['total_corrections'] += 1
            results['total_particles_eliminated'] += particles_eliminated
            results['correction_logs'].append(elimination_log)
            
            logger.info(f"Completed correction: {target_file} "
                       f"({particles_eliminated} particles eliminated, "
                       f"{len(corrected_data)} remaining)")
                       
        logger.info(f"Workflow complete: {results['total_corrections']} corrections, "
                   f"{results['total_particles_eliminated']} total particles eliminated")
                   
        return results
