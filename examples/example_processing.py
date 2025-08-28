"""
Example script demonstrating how to use the microplastics blind correction tool.

This example shows how to:
1. Load particle data from Excel files
2. Apply processing and quality control procedures
3. Perform blank and blind correction
4. Export results and generate reports
"""

import logging
from pathlib import Path

# Import the microplastics processing modules
from microplas_blind_corr import (
    ExcelLoader, 
    ParticleProcessor,
    BlankCorrector,
    BlindCorrector,
    ProcessingConfig
)
from microplas_blind_corr.config import EXCEL_COLUMN_MAPPING
from microplas_blind_corr.utils import (
    calculate_particle_statistics,
    export_results,
    generate_processing_report
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main processing workflow."""
    
    # Configure paths
    data_dir = Path("test_data")
    output_dir = Path("output") 
    config_file = Path("configs/default_config.yaml")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    logger.info("Starting microplastics blind correction processing")
    
    # 1. Load configuration
    if config_file.exists():
        config = ProcessingConfig.load_from_file(config_file)
        logger.info(f"Loaded configuration from {config_file}")
    else:
        config = ProcessingConfig()
        logger.info("Using default configuration")
    
    # 2. Initialize components
    loader = ExcelLoader(column_mapping=EXCEL_COLUMN_MAPPING)
    processor = ParticleProcessor(config=config, column_mapping=EXCEL_COLUMN_MAPPING)
    blank_corrector = BlankCorrector(column_mapping=EXCEL_COLUMN_MAPPING)
    blind_corrector = BlindCorrector(column_mapping=EXCEL_COLUMN_MAPPING)
    
    # 3. Load particle data
    # For this example, we'll use the test file as both environmental and blank data
    # In a real scenario, you would have separate files for each sample type
    
    sample_files = list(data_dir.glob("*.xlsx"))
    if not sample_files:
        logger.error(f"No Excel files found in {data_dir}")
        return
        
    logger.info(f"Found {len(sample_files)} data files")
    
    # Load data from all files
    all_particles = loader.load_multiple_samples(sample_files)
    logger.info(f"Loaded {len(all_particles)} total particles")
    
    # 4. Detect sample types
    sample_types = loader.detect_sample_type(
        all_particles,
        blank_patterns=config.blank_sample_patterns,
        blind_patterns=config.blind_sample_patterns
    )
    
    # For demonstration, let's manually designate some samples as blanks/blinds
    # In practice, this would be based on your actual sample naming
    sample_names = list(sample_types.keys())
    if len(sample_names) > 1:
        # Designate every 3rd sample as blank, every 4th as blind
        for i, sample_name in enumerate(sample_names):
            if i % 4 == 0:
                sample_types[sample_name] = 'blank'
            elif i % 3 == 0:
                sample_types[sample_name] = 'blind'
    
    logger.info(f"Sample type assignments: {sample_types}")
    
    # 5. Process particle data
    processed_particles = processor.process_particles(all_particles)
    
    # 6. Separate particles by type
    env_particles, blank_particles, blind_particles = processor.separate_sample_types(
        processed_particles, sample_types
    )
    
    # 7. Apply blank correction (if blank samples available)
    if len(blank_particles) > 0:
        logger.info("Applying blank correction")
        corrected_env_particles, blank_elimination_log = blank_corrector.apply_blank_correction(
            env_particles, blank_particles
        )
        
        # Export blank correction results
        export_results(blank_elimination_log, output_dir / "blank_elimination_log.xlsx")
        blank_summary = blank_corrector.get_correction_summary(blank_elimination_log)
        logger.info(f"Blank correction summary: {blank_summary}")
    else:
        logger.info("No blank samples found, skipping blank correction")
        corrected_env_particles = env_particles
        blank_elimination_log = None
    
    # 8. Apply blind correction (if blind samples available)
    if len(blind_particles) > 0:
        logger.info("Applying blind correction")
        
        # Create synthetic blind sample
        synthetic_blind = blind_corrector.create_synthetic_blind(blind_particles)
        
        if len(synthetic_blind) > 0:
            final_env_particles, blind_elimination_log = blind_corrector.apply_blind_correction(
                corrected_env_particles, synthetic_blind
            )
            
            # Export blind correction results
            export_results(blind_elimination_log, output_dir / "blind_elimination_log.xlsx")
            blind_summary = blind_corrector.get_correction_summary(blind_elimination_log)
            logger.info(f"Blind correction summary: {blind_summary}")
        else:
            logger.warning("No synthetic blind particles created")
            final_env_particles = corrected_env_particles
            blind_elimination_log = None
    else:
        logger.info("No blind samples found, skipping blind correction")
        final_env_particles = corrected_env_particles
        blind_elimination_log = None
    
    # 9. Generate statistics and reports
    logger.info("Generating statistics and reports")
    
    # Calculate particle statistics
    original_stats = calculate_particle_statistics(processed_particles, EXCEL_COLUMN_MAPPING)
    final_stats = calculate_particle_statistics(final_env_particles, EXCEL_COLUMN_MAPPING)
    
    # Generate processing report
    processing_report = generate_processing_report(
        original_data=processed_particles,
        processed_data=final_env_particles,
        blank_elimination_log=blank_elimination_log,
        blind_elimination_log=blind_elimination_log,
        column_mapping=EXCEL_COLUMN_MAPPING
    )
    
    # 10. Export final results
    logger.info("Exporting results")
    
    # Export processed particles
    export_results(final_env_particles, output_dir / "final_processed_particles.xlsx")
    
    # Export statistics
    export_results(original_stats, output_dir / "original_statistics.xlsx")
    export_results(final_stats, output_dir / "final_statistics.xlsx")
    
    # Save processing report as text
    with open(output_dir / "processing_report.txt", 'w') as f:
        f.write("Microplastics Processing Report\n")
        f.write("=" * 40 + "\n\n")
        
        for section, data in processing_report.items():
            f.write(f"{section.upper()}\n")
            f.write("-" * len(section) + "\n")
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"{key}: {value}\n")
            else:
                f.write(f"{data}\n")
            f.write("\n")
    
    logger.info(f"Processing complete! Results saved to {output_dir}")
    logger.info(f"Final dataset contains {len(final_env_particles)} particles")


if __name__ == "__main__":
    main()
