"""
Multi-file workflow example for microplastics blind correction.

This example demonstrates how to set up and run the complete workflow
when you have separate Excel files for environmental, blank, and blind samples.
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
from microplas_blind_corr.utils import FileOrganizer


def setup_example_workflow():
    """
    Demonstrate how to set up a complete workflow with multiple files.
    
    This function shows the recommended approach for organizing and
    processing microplastics data from separate Excel files.
    """
    
    print("=== Multi-File Microplastics Workflow Setup ===")
    print()
    
    # === STEP 1: ORGANIZE YOUR FILES ===
    print("📁 Step 1: File Organization")
    print("   For the complete workflow, you need separate Excel files for:")
    print("   ")
    print("   🌱 Environmental samples:")
    print("      - sample_001_particles.xlsx")
    print("      - sample_002_particles.xlsx") 
    print("      - sample_003_particles.xlsx")
    print("      - ...")
    print("   ")
    print("   🧽 Blank samples (laboratory controls):")
    print("      - blank_001_particles.xlsx")
    print("      - blank_002_particles.xlsx")
    print("      - ...")
    print("   ")
    print("   👁️ Blind samples (method validation):")
    print("      - blind_001_particles.xlsx")
    print("      - blind_002_particles.xlsx")
    print("      - ...")
    print("   ")
    print("   📋 Each Excel file should have the same structure:")
    print("      - Spectrum ID, Polymer Type, Color, Shape")
    print("      - Long Size (µm), Short Size (µm), Height (µm)")
    print("      - Area (µm²), and any other analysis columns")
    print()
    
    # === STEP 2: FILE VALIDATION ===
    print("🔍 Step 2: File Validation")
    
    # Initialize file organizer
    organizer = FileOrganizer(EXCEL_COLUMN_MAPPING)
    
    # Example: validate our test file
    test_file = Path("data/250606_Sterni_500_5_Particle_List.xlsx")
    if test_file.exists():
        print(f"   Validating example file: {test_file.name}")
        validation = organizer.validate_file_structure(test_file)
        
        if validation['valid']:
            print(f"   ✅ File is valid ({validation['particle_count']:,} particles)")
            print(f"   📊 Columns found: {len(validation['columns_found'])}")
            print("      - " + ", ".join(validation['columns_found'][:4]) + "...")
        else:
            print("   ❌ File has validation errors:")
            for error in validation['errors']:
                print(f"      - {error}")
    else:
        print("   ℹ️  No test file available for validation demonstration")
    print()
    
    # === STEP 3: WORKFLOW CONFIGURATION ===
    print("⚙️ Step 3: Workflow Configuration")
    
    # Load configuration
    config = ProcessingConfig()
    print(f"   Size filter: {config.size_filter_highpass}-{config.size_filter_lowpass} µm")
    print(f"   Excluded polymers: {len(config.excluded_polymers)} types")
    print(f"   Color standardization: {len(config.color_standardization)} mappings")
    print(f"   Shape standardization: {len(config.shape_standardization)} mappings")
    print()
    
    # === STEP 4: PROCESSING WORKFLOW ===
    print("🔄 Step 4: Processing Workflow")
    print("   The complete processing workflow includes:")
    print("   ")
    print("   1️⃣ Load and validate data from Excel files")
    print("      - Environmental sample files")
    print("      - Blank sample files")  
    print("      - Blind sample files")
    print("   ")
    print("   2️⃣ Process particle data")
    print("      - Remove excluded polymers")
    print("      - Apply size filtering")
    print("      - Standardize colors and shapes")
    print("      - Calculate geometric mean sizes")
    print("   ")
    print("   3️⃣ Apply blank correction")
    print("      - Match particles between environmental and blank samples")
    print("      - Remove matching particles from environmental data")
    print("      - Log eliminated particles")
    print("   ")
    print("   4️⃣ Apply blind correction")
    print("      - Create synthetic blind sample")
    print("      - Match particles between environmental and blind samples")  
    print("      - Remove matching particles for quality assessment")
    print("      - Log eliminated particles")
    print("   ")
    print("   5️⃣ Export results")
    print("      - Processed environmental data")
    print("      - Elimination logs")
    print("      - Processing statistics")
    print("      - Quality control reports")
    print()
    
    # === STEP 5: EXAMPLE FILE STRUCTURE ===
    print("📂 Step 5: Recommended Directory Structure")
    print("   ")
    print("   your_project/")
    print("   ├── data/")
    print("   │   ├── environmental/")
    print("   │   │   ├── sample_001_particles.xlsx")
    print("   │   │   ├── sample_002_particles.xlsx")
    print("   │   │   └── sample_003_particles.xlsx")
    print("   │   ├── blanks/")
    print("   │   │   ├── blank_001_particles.xlsx")
    print("   │   │   └── blank_002_particles.xlsx")
    print("   │   └── blinds/")
    print("   │       ├── blind_001_particles.xlsx")
    print("   │       └── blind_002_particles.xlsx")
    print("   ├── config/")
    print("   │   └── custom_config.yaml")
    print("   ├── output/")
    print("   └── scripts/")
    print("       └── process_data.py")
    print()
    
    # === STEP 6: CODE EXAMPLE ===
    print("💻 Step 6: Example Code Structure")
    print("   ")
    print("   ```python")
    print("   from microplas_blind_corr import *")
    print("   ")
    print("   # Load configuration")
    print("   config = ProcessingConfig.load_from_file('config/custom_config.yaml')")
    print("   ")
    print("   # Initialize processors")
    print("   loader = ExcelLoader(EXCEL_COLUMN_MAPPING)")
    print("   processor = ParticleProcessor(config, EXCEL_COLUMN_MAPPING)")
    print("   blank_corrector = BlankCorrector(EXCEL_COLUMN_MAPPING)")
    print("   blind_corrector = BlindCorrector(EXCEL_COLUMN_MAPPING)")
    print("   ")
    print("   # Load data")
    print("   env_files = ['data/environmental/sample_001.xlsx', ...]")
    print("   blank_files = ['data/blanks/blank_001.xlsx', ...]") 
    print("   blind_files = ['data/blinds/blind_001.xlsx', ...]")
    print("   ")
    print("   env_data = loader.load_multiple_samples(env_files)")
    print("   blank_data = loader.load_multiple_samples(blank_files)")
    print("   blind_data = loader.load_multiple_samples(blind_files)")
    print("   ")
    print("   # Process and correct")
    print("   processed_env = processor.process_particles(env_data)")
    print("   processed_blank = processor.process_particles(blank_data)")
    print("   processed_blind = processor.process_particles(blind_data)")
    print("   ")
    print("   # Apply corrections")
    print("   corrected_env, blank_log = blank_corrector.apply_blank_correction(")
    print("       processed_env, processed_blank")
    print("   )")
    print("   ")
    print("   synthetic_blind = blind_corrector.create_synthetic_blind(processed_blind)")
    print("   final_env, blind_log = blind_corrector.apply_blind_correction(")
    print("       corrected_env, synthetic_blind")
    print("   )")
    print("   ```")
    print()
    
    # === STEP 7: NEXT STEPS ===
    print("🚀 Step 7: Getting Started")
    print("   ")
    print("   To use this workflow with your data:")
    print("   ")
    print("   1. Organize your Excel files using the recommended structure")
    print("   2. Use the file organization tool: `python organize_files.py analyze data/`")
    print("   3. Validate your files: `python organize_files.py validate file1.xlsx file2.xlsx`")
    print("   4. Customize the configuration in `configs/default_config.yaml`")
    print("   5. Run the processing workflow with your files")
    print("   6. Review the results and elimination logs")
    print("   ")
    print("   📖 See `examples/excel_workflow_example.py` for a complete working example")
    print("   ⚙️  See `examples/organize_files.py` for file organization utilities")
    print()
    
    print("✅ Workflow setup guide complete!")
    print("   Ready to process your microplastics data! 🎉")


if __name__ == "__main__":
    setup_example_workflow()
