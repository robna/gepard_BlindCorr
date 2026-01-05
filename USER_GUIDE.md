# Microplastics Blind Correction Tool - User Guide

## Overview

This tool performs automated blind correction on microplastics particle datasets. It removes particles from environmental samples that match particles found in blind control samples, based on polymer type, color, shape, and size similarity.

## Quick Start

### 1. Installation and Setup

```bash
# Clone the repository
git clone <repository-url>
cd gepard_BlindCorr

# Install dependencies with uv (recommended)
uv install

# Or with pip
pip install -e .
```

### 2. Prepare Your Data Files

Place your Excel (.xlsx), CSV (.csv), or ODS (.ods) files in the `data/` directory:
- **Environmental samples**: Files containing particles to be corrected
- **Blind controls**: Files containing control particles used for correction

**Required columns in your data files:**
- `Spectrum ID`: Unique identifier for each particle
- `Polymer Type`: Type of plastic (e.g., "Polyethylene", "Polystyrene")
- `Color`: Particle color (e.g., "white", "blue", "red")
- `Shape`: Particle shape (e.g., "fibre", "irregular", "spherule")
- `Long Size (µm)`: Primary size dimension in micrometers
- `Short Size (µm)`: Secondary size dimension in micrometers
- `Height (µm)`: Tertiary size dimension in micrometers
- `Area (µm²)`: Particle area in square micrometers
- `HQI`: Quality index value
- Size distribution columns: `0 - 5 μm`, `5 - 10 μm`, `10 - 20 μm`, `20 - 50 μm`, `50 - 100 μm`, `> 100 μm`

**Note**: The tool automatically handles variations in column naming (e.g., "Particle ID" vs "particle_id")

### 3. Create a Correction Configuration

Create a YAML file defining which samples should be corrected by which controls:

```yaml
# Example: corrections/my_experiment.yaml
corrections:
  # Environmental sample corrected by blind control
  "environmental_sample_001.xlsx":
    - "blind_control_001.xlsx"
  
  # Multiple controls can be used for one sample
  "environmental_sample_002.xlsx":
    - "blind_control_001.xlsx"
    - "blind_control_002.xlsx"
  
  # Chain corrections: first correct blank, then use it to correct environmental
  "blank_sample.xlsx":
    - "lab_blank.xlsx"
  "environmental_sample_003.xlsx":
    - "blank_sample.xlsx"  # Uses the corrected blank

# Optional output settings
output:
  format: "excel"           # Creates .xlsx files ("excel" or "csv")
  suffix: "_corrected"      # Suffix added to output files
  directory: "results"      # Output directory
  
# Optional processing settings
settings:
  create_synthetic_controls: true    # Combine multiple controls
  log_eliminations: true            # Save detailed elimination logs
  validate_files: true              # Validate file structure
  size_matching_dimension: "geometric_mean"  # Size dimension for matching
```

### 4. Run the Correction

```bash
# Run correction with your configuration
uv run python examples/run_corrections.py run corrections/my_experiment.yaml

# Or validate configuration first
uv run python examples/run_corrections.py validate corrections/my_experiment.yaml

# Create a template configuration
uv run python examples/run_corrections.py template corrections/new_config.yaml
```

## Detailed Usage

### File Organization

Use the file organization tool to automatically sort your data files:

```bash
# Organize files by sample type patterns
uv run python examples/organize_files.py data/ --output organized_data/

# Custom patterns
uv run python examples/organize_files.py data/ \
  --env-patterns "env,environmental,sample" \
  --blind-patterns "blind,control" \
  --blank-patterns "blank,negative"
```

### Understanding the Correction Process

The tool performs correction in several steps:

1. **File Loading**: Reads Excel/CSV/ODS files and standardizes column names
2. **Data Processing**: 
   - Filters out excluded polymer types (contamination, dyes)
   - Calculates geometric mean size from Long Size and Short Size dimensions
   - Standardizes color and shape categories
3. **Dependency Resolution**: Determines the order to process files based on dependencies
4. **Particle Matching**: 
   - **Step 1**: Find all environmental particles matching the control particle's:
     - **Polymer Type**: Exact match
     - **Color**: Exact match (after standardization)
     - **Shape**: Exact match (after standardization)
   - **Step 2**: Among matching particles, select the one with the closest size value
5. **Elimination**: Remove the best-matching particle from the environmental sample

### Matching Criteria

The correction process works in two stages:

**Stage 1: Find Candidate Matches**
Particles are considered matching candidates if they have:
- ✅ **Same polymer type** (e.g., "Polyethylene")
- ✅ **Same color** (e.g., "white" → standardized to "unspecific")
- ✅ **Same shape** (e.g., "spherule" → standardized to "irregular")

**Stage 2: Select Best Match**
Among all candidate matches, the particle with the **closest size** is selected for elimination.

### Size Matching Configuration

You can configure which size dimension to use for matching in your YAML configuration:

```yaml
# Optional processing settings
settings:
  size_matching_dimension: "geometric_mean"  # Options:
  # "geometric_mean" - Geometric mean of Long Size and Short Size (default)
  # "size_1" - Use the standardized Long Size column (after loading)
  # "size_2" - Use the standardized Short Size column (after loading)  
  # "size_3" - Use the standardized Height column (after loading)
  # "area" - Use the standardized Area column (after loading)
```

**Note**: Column names are standardized during loading. The original column names like "Long Size (µm)" become "size_1", "Short Size (µm)" becomes "size_2", etc.

**Default**: Uses geometric mean of `size_1` and `size_2` (calculated from Long Size and Short Size)

### Color and Shape Standardization

The tool automatically standardizes categories:

**Color Standardization:**
- `transparent`, `white`, `grey`, `undetermined` → `unspecific`
- `violet` → `blue`

**Shape Standardization:**
- `spherule`, `flake`, `foam`, `granule` → `irregular`

### Excluded Polymers

By default, these polymer types are excluded from processing:
- `unknown`
- Contamination types: `Parafilm`, `Poly (tetrafluoro ethylene)`
- Dye particles: `PV23`, `PB15`, `PR101`, etc.

## Configuration Options

### Processing Settings

### Output Formats

The tool supports two output formats:

| YAML Configuration | File Extension | Description |
|-------------------|---------------|-------------|
| `format: "excel"` | `.xlsx` | Excel workbook (recommended) |
| `format: "csv"`   | `.csv`  | Comma-separated values |

**Example:**
```yaml
output:
  format: "excel"     # Creates .xlsx files
  suffix: "_corrected"
  directory: "results"
```

```python
@dataclass
class ProcessingConfig:
    # Size filtering
    size_filter_highpass: float = 0.0      # Minimum size (μm)
    size_filter_lowpass: float = 5000.0    # Maximum size (μm)
    
    # Excluded polymers (add your own contamination types)
    excluded_polymers: List[str] = [
        'unknown',
        'Parafilm',
        # ... add more as needed
    ]
    
    # Custom color/shape standardization
    color_standardization: Dict[str, str] = {
        'transparent': 'unspecific',
        # ... add your mappings
    }
```

### Column Mapping

If your files use different column names, update the mapping in `src/microplas_blind_corr/config/settings.py`:

```python
# Example: Your files use "Polymer" instead of "Polymer Type"
EXCEL_COLUMN_MAPPING = ColumnMapping(
    polymer_type="Polymer",           # Your column name
    color="Color",                    # Your column name
    size_1="Length (μm)",            # Your column name
    # ... etc
)
```

## Output Files

The tool generates:

1. **Corrected data files**: Original files with matching particles removed
   - Format: `{original_name}_corrected.{format}`
   - Location: `data/{output_directory}/`

2. **Workflow report**: JSON summary of all corrections
   - File: `workflow_report.json`
   - Contains: elimination counts, processing order, file paths

3. **Elimination logs**: Detailed records of eliminated particles (if enabled)
   - Format: `{sample_name}_elimination_log.xlsx`
   - Contains: matched particle details, size differences, quality metrics

## Troubleshooting

### Common Issues

**❌ "Configuration file not found"**
- Check file path is correct
- Use forward slashes even on Windows: `configs/my_config.yaml`

**❌ "Error reading Excel file"**
- Install required dependencies: `uv add openpyxl` (Excel) or `uv add odfpy` (ODS)
- Check file is not corrupted or password-protected

**❌ "Column not found"**
- Check your column names match the expected format
- Update column mapping if needed
- Ensure all required columns are present

**❌ "Few or no particles eliminated"**
- Check size filter settings (may be too restrictive)
- Verify polymer types match between samples
- Check color/shape standardization is working correctly

### Debugging Tips

1. **Use small test datasets** with known matching particles
2. **Lower size filters** temporarily: set `size_filter_highpass = 0.0`
3. **Check processed data** before correction:
   ```bash
   # View processed particle counts
   uv run python -c "
   from src.microplas_blind_corr.data_loaders.excel_loader import ExcelLoader
   from src.microplas_blind_corr.processors.particle_processor import ParticleProcessor
   # ... check your data step by step
   "
   ```

## Examples

### Simple Correction
```yaml
corrections:
  "sample.xlsx": ["blind.xlsx"]
```

### Multiple Controls
```yaml
corrections:
  "sample.xlsx": 
    - "blind1.xlsx"
    - "blind2.xlsx"
```

### Correction Chain
```yaml
corrections:
  # First correct the blank
  "blank.xlsx": ["lab_blank.xlsx"]
  # Then use corrected blank to correct environmental
  "environmental.xlsx": ["blank.xlsx"]
```

## Support

For issues or questions:
1. Check this user guide
2. Examine the example configurations in `configs/`
3. Run validation: `uv run python examples/run_corrections.py validate config.yaml`
4. Use debug mode with small test files

## Advanced Usage

### Custom Processing Pipeline

For advanced users, you can create custom correction workflows:

```python
from src.microplas_blind_corr.workflows.correction_workflow import CorrectionWorkflow
from src.microplas_blind_corr.config import ProcessingConfig, EXCEL_COLUMN_MAPPING

# Create custom workflow
workflow = CorrectionWorkflow(ProcessingConfig(), EXCEL_COLUMN_MAPPING)
workflow.load_correction_config("my_config.yaml")
workflow.run_workflow("data")
```

### Batch Processing

Process multiple experiments:

```bash
# Process all YAML files in a directory
for config in configs/*.yaml; do
    uv run python examples/run_corrections.py run "$config"
done
```
