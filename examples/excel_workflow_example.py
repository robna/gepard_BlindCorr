"""
Example script demonstrating microplastics blind correction with separate Excel files.

This example shows how to process microplastics data when:
- Environmental samples are in separate Excel files
- Blank samples are in separate Excel files  
- Blind samples are in separate Excel files

Each file has the same structure but represents different sample types.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microplas_blind_corr import (
    ExcelLoader, 
    ParticleProcessor, 
    BlankCorrector, 
    BlindCorrector,
    ProcessingConfig
)
from microplas_blind_corr.config import EXCEL_COLUMN_MAPPING
from microplas_blind_corr.utils import (
    validate_dataframe_structure,
    calculate_particle_statistics,
    export_results,
    generate_processing_report
)


def main():
    """Demonstrate the complete processing workflow."""
    
    print("=== Microplastics Blind Correction Tool ===")
    print("Processing separate Excel files for environmental, blank, and blind samples")
    print()
    
    # Initialize configuration
    config = ProcessingConfig()
    column_mapping = EXCEL_COLUMN_MAPPING
    
    # Initialize processors
    loader = ExcelLoader(column_mapping)
    particle_processor = ParticleProcessor(config, column_mapping)
    blank_corrector = BlankCorrector(column_mapping)
    blind_corrector = BlindCorrector(column_mapping)
    
    # === FILE PATHS CONFIGURATION ===
    # In a real scenario, you would have multiple files:
    
    # Environmental sample files
    environmental_files = [
        "data/250606_Sterni_500_5_Particle_List.xlsx"  # We only have one example
        # "data/sample_002_particles.xlsx",
        # "data/sample_003_particles.xlsx",
    ]
    
    # Blank sample files (these would be separate files in reality)
    blank_files = [
        # "data/blank_001_particles.xlsx",
        # "data/blank_002_particles.xlsx",
    ]
    
    # Blind sample files (these would be separate files in reality)
    blind_files = [
        # "data/blind_001_particles.xlsx", 
        # "data/blind_002_particles.xlsx",
    ]
    
    # === LOAD DATA ===
    print("📁 Loading particle data from Excel files...")
    
    try:
        # Load environmental samples
        if environmental_files:
            print(f"   Loading {len(environmental_files)} environmental sample(s)...")
            env_sample_names = [f"Environmental_Sample_{i+1}" for i in range(len(environmental_files))]
            environmental_data = loader.load_multiple_samples(environmental_files, env_sample_names)
            print(f"   ✓ Loaded {len(environmental_data)} environmental particles")
        else:
            print("   ⚠️  No environmental files specified")
            environmental_data = None
            
        # Load blank samples
        if blank_files:
            print(f"   Loading {len(blank_files)} blank sample(s)...")
            blank_sample_names = [f"Blank_Sample_{i+1}" for i in range(len(blank_files))]
            blank_data = loader.load_multiple_samples(blank_files, blank_sample_names)
            print(f"   ✓ Loaded {len(blank_data)} blank particles")
        else:
            print("   ℹ️  No blank files specified - skipping blank correction")
            blank_data = None
            
        # Load blind samples
        if blind_files:
            print(f"   Loading {len(blind_files)} blind sample(s)...")
            blind_sample_names = [f"Blind_Sample_{i+1}" for i in range(len(blind_files))]
            blind_data = loader.load_multiple_samples(blind_files, blind_sample_names)
            print(f"   ✓ Loaded {len(blind_data)} blind particles")
        else:
            print("   ℹ️  No blind files specified - skipping blind correction")
            blind_data = None
            
    except Exception as e:
        print(f"   ❌ Error loading data: {e}")
        return
    
    if environmental_data is None:
        print("❌ No environmental data loaded. Cannot proceed.")
        return
        
    print()
    
    # === PROCESS ENVIRONMENTAL DATA ===
    print("🔧 Processing environmental particle data...")
    
    try:
        # Validate input data
        validate_dataframe_structure(environmental_data, column_mapping)
        
        # Process particles (standardization, filtering, etc.)
        processed_env_data = particle_processor.process_particles(environmental_data)
        print(f"   ✓ Processed environmental data: {len(processed_env_data)} particles retained")
        
    except Exception as e:
        print(f"   ❌ Error processing environmental data: {e}")
        return
        
    print()
    
    # === BLANK CORRECTION ===
    blank_elimination_log = None
    if blank_data is not None:
        print("🧽 Applying blank correction...")
        
        try:
            # Process blank data
            processed_blank_data = particle_processor.process_particles(blank_data)
            print(f"   ✓ Processed blank data: {len(processed_blank_data)} particles")
            
            # Apply blank correction
            corrected_env_data, blank_elimination_log = blank_corrector.apply_blank_correction(
                processed_env_data, processed_blank_data
            )
            
            # Update environmental data
            processed_env_data = corrected_env_data
            
            print(f"   ✓ Blank correction complete: {len(blank_elimination_log)} particles eliminated")
            
        except Exception as e:
            print(f"   ❌ Error in blank correction: {e}")
            
        print()
    
    # === BLIND CORRECTION ===
    blind_elimination_log = None
    if blind_data is not None:
        print("👁️ Applying blind correction...")
        
        try:
            # Process blind data
            processed_blind_data = particle_processor.process_particles(blind_data)
            print(f"   ✓ Processed blind data: {len(processed_blind_data)} particles")
            
            # Create synthetic blind sample
            synthetic_blind = blind_corrector.create_synthetic_blind(processed_blind_data)
            print(f"   ✓ Created synthetic blind: {len(synthetic_blind)} particles")
            
            # Apply blind correction
            corrected_env_data, blind_elimination_log = blind_corrector.apply_blind_correction(
                processed_env_data, synthetic_blind
            )
            
            # Update environmental data
            processed_env_data = corrected_env_data
            
            print(f"   ✓ Blind correction complete: {len(blind_elimination_log)} particles eliminated")
            
        except Exception as e:
            print(f"   ❌ Error in blind correction: {e}")
            
        print()
    
    # === RESULTS AND STATISTICS ===
    print("📊 Generating results and statistics...")
    
    # Calculate final statistics
    final_stats = calculate_particle_statistics(processed_env_data, column_mapping)
    print("\n📈 Final particle statistics by sample:")
    print(final_stats)
    
    # Generate comprehensive report
    report = generate_processing_report(
        environmental_data, 
        processed_env_data,
        blank_elimination_log,
        blind_elimination_log,
        column_mapping
    )
    
    print(f"\n📋 Processing Summary:")
    print(f"   Original particles: {report['processing_summary']['original_particle_count']}")
    print(f"   Final particles: {report['processing_summary']['final_particle_count']}")
    print(f"   Retention rate: {report['processing_summary']['retention_rate']:.1%}")
    
    if blank_elimination_log is not None:
        print(f"   Blank correction eliminated: {len(blank_elimination_log)} particles")
    if blind_elimination_log is not None:
        print(f"   Blind correction eliminated: {len(blind_elimination_log)} particles")
    
    print()
    
    # === EXPORT RESULTS ===
    print("💾 Exporting results...")
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Export processed environmental data
        export_results(processed_env_data, output_dir / "processed_environmental_particles.xlsx")
        
        # Export elimination logs if available
        if blank_elimination_log is not None and len(blank_elimination_log) > 0:
            export_results(blank_elimination_log, output_dir / "blank_elimination_log.xlsx")
            
        if blind_elimination_log is not None and len(blind_elimination_log) > 0:
            export_results(blind_elimination_log, output_dir / "blind_elimination_log.xlsx")
        
        # Export processing report
        import json
        with open(output_dir / "processing_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        print(f"   ✓ Results exported to {output_dir}")
        
    except Exception as e:
        print(f"   ❌ Error exporting results: {e}")
    
    print("\n✅ Processing complete!")
    print(f"\nℹ️  Note: This example only demonstrates with environmental data.")
    print(f"   In practice, you would provide separate Excel files for:")
    print(f"   - Environmental samples (one file per sample)")
    print(f"   - Blank samples (one file per blank)")  
    print(f"   - Blind samples (one file per blind)")


if __name__ == "__main__":
    main()
