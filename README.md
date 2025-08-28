# Microplastics Blind Correction Tool

A general-purpose Python tool for processing microplastics particle data with quality control procedures including blank correction and blind sample validation. This tool processes particle data from various sources (Excel files, CSV, SQL databases) and applies standardized correction procedures to ensure data quality.

## What is this project about?

This project provides tools for processing microplastics particle data with quality control procedures including:
- **Blank correction** for laboratory contamination removal  
- **Blind sample processing** for method validation
- **Particle size filtering** and standardization
- **Shape and color standardization**
- **Flexible data input** from Excel files or SQL databases
- **Comprehensive reporting** and statistical analysis

## Key Features

### 🔧 **Flexible Data Input**
- **Excel files**: Process individual sample files (recommended approach)
- **CSV files**: Alternative file format support
- **SQL databases**: Legacy database integration
- **Automatic file organization** and validation

### 🧽 **Quality Control Pipeline**
- **Laboratory blank correction** removes contamination artifacts
- **Procedural blind validation** ensures method reliability  
- **Configurable polymer exclusion** lists for contamination removal
- **Size filtering** with customizable parameters
- **Shape and color standardization**

### ⚙️ **Configurable Processing**
- **YAML-based configuration** for different research contexts
- **Customizable column mappings** for various data formats
- **Flexible sample identification** patterns
- **Extensible processing pipeline**

## Installation

### Prerequisites
- Python 3.11+
- UV package manager (recommended) or pip

### Using UV (Recommended)
```bash
git clone https://github.com/robna/gepard_BlindCorr.git
cd gepard_BlindCorr
git checkout refactor/general-tool
uv sync
```

### Using pip
```bash
git clone https://github.com/robna/gepard_BlindCorr.git
cd gepard_BlindCorr
git checkout refactor/general-tool
pip install -e .
```

## Quick Start

### 1. Organize Your Data Files

For the file-based workflow, organize your Excel files as follows:

```
your_project/
├── data/
│   ├── environmental/
│   │   ├── sample_001_particles.xlsx
│   │   ├── sample_002_particles.xlsx
│   │   └── sample_003_particles.xlsx
│   ├── blanks/
│   │   ├── blank_001_particles.xlsx
│   │   └── blank_002_particles.xlsx
│   └── blinds/
│       ├── blind_001_particles.xlsx
│       └── blind_002_particles.xlsx
└── output/
```

Each Excel file should contain particle data with columns like:
- `Spectrum ID` (unique particle identifier)
- `Polymer Type` (identified polymer)
- `Color` (particle color)
- `Shape` (particle shape: fiber, irregular, etc.)
- `Long Size (µm)` (primary dimension)
- `Short Size (µm)` (secondary dimension)
- `Height (µm)` (tertiary dimension, optional)
- `Area (µm²)` (particle area, optional)

### 2. Validate Your Files

Use the built-in file organization tool:

```bash
# Analyze and categorize files in a directory
uv run python examples/organize_files.py analyze data/

# Validate specific files
uv run python examples/organize_files.py validate data/environmental/*.xlsx

# Get organization suggestions
uv run python examples/organize_files.py suggest data/
```

### 3. Run the Processing Workflow

```python
from microplas_blind_corr import (
    ExcelLoader, ParticleProcessor, BlankCorrector, BlindCorrector, ProcessingConfig
)
from microplas_blind_corr.config import EXCEL_COLUMN_MAPPING

# Load configuration
config = ProcessingConfig()
loader = ExcelLoader(EXCEL_COLUMN_MAPPING)

# Load your data files
env_files = ["data/environmental/sample_001.xlsx", "data/environmental/sample_002.xlsx"]
blank_files = ["data/blanks/blank_001.xlsx"]
blind_files = ["data/blinds/blind_001.xlsx"]

env_data = loader.load_multiple_samples(env_files)
blank_data = loader.load_multiple_samples(blank_files)
blind_data = loader.load_multiple_samples(blind_files)

# Process and apply corrections
processor = ParticleProcessor(config, EXCEL_COLUMN_MAPPING)
processed_env = processor.process_particles(env_data)
processed_blank = processor.process_particles(blank_data)
processed_blind = processor.process_particles(blind_data)

# Apply blank correction
blank_corrector = BlankCorrector(EXCEL_COLUMN_MAPPING)
corrected_env, blank_log = blank_corrector.apply_blank_correction(processed_env, processed_blank)

# Apply blind correction
blind_corrector = BlindCorrector(EXCEL_COLUMN_MAPPING)
synthetic_blind = blind_corrector.create_synthetic_blind(processed_blind)
final_env, blind_log = blind_corrector.apply_blind_correction(corrected_env, synthetic_blind)
```

## Examples

The `examples/` directory contains several demonstration scripts:

- **`workflow_setup_guide.py`**: Complete setup guide and workflow overview
- **`excel_workflow_example.py`**: Full working example with Excel files
- **`organize_files.py`**: File organization and validation utility

Run the setup guide to get started:
```bash
uv run python examples/workflow_setup_guide.py
```

## Configuration

### Default Configuration

The tool comes with sensible defaults in `configs/default_config.yaml`. Key settings include:

```yaml
# Size filtering
size_filter_highpass: 50.0  # Minimum size in micrometers
size_filter_lowpass: 5000.0  # Maximum size in micrometers

# Polymer exclusion (contamination)
excluded_polymers:
  - "Poly (tetrafluoro ethylene)"
  - "PV23"
  - "Parafilm"
  # ... more contamination sources

# Sample identification patterns
blank_sample_patterns: ["blank", "Blank", "BLANK"]
blind_sample_patterns: ["blind", "Blind", "BLIND"]
```

### Custom Configuration

Create your own configuration file:

```python
from microplas_blind_corr import ProcessingConfig

# Load custom configuration
config = ProcessingConfig.load_from_file("my_config.yaml")

# Or modify defaults programmatically
config = ProcessingConfig()
config.size_filter_highpass = 100.0  # Different size threshold
config.excluded_polymers.append("My_Custom_Contaminant")
```

## Repository Structure

```
├── src/microplas_blind_corr/          # Main package
│   ├── config/                        # Configuration management
│   ├── data_loaders/                  # Data input modules
│   ├── processors/                    # Core processing algorithms
│   └── utils/                         # Utility functions
├── examples/                          # Example scripts and tutorials
├── configs/                           # Configuration files
├── tests/                            # Test suite
└── test_data/                        # Example data files
```

## Migration from Legacy Version

If you're migrating from the original project-specific version:

1. **File organization**: Convert your SQL data to Excel files (one per sample)
2. **Configuration**: Update your settings in the new YAML format
3. **Column mapping**: Verify column names match the expected format
4. **Workflow**: Use the new modular API instead of the original scripts

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this tool in your research, please cite:

```
Microplastics Blind Correction Tool
GitHub: https://github.com/robna/gepard_BlindCorr
```

## Support

- **Documentation**: See `examples/` directory for detailed usage examples
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions and community support
- Size-based particle filtering

**Data Processing:**
- Particle amplification for sub-sample extrapolation
- Geometric mean size calculations
- Shape and color standardization
- Automated particle ID management

**Export Capabilities:**
- Clean, processed microplastic datasets
- Elimination tracking for transparency
- CSV export for downstream analysis

## Getting Started

### Prerequisites
- Python 3.8+
- pandas, numpy
- mysql-connector-python (for database access)
- jupyter (for notebook execution)

### Installation
```bash
git clone [repository-url]
cd gepardBlindCorr
pip install pandas numpy mysql-connector-python jupyter
```

### Basic Usage

1. **Configure Database Connection:**
   - Update `MPDB_server` in `MPDB_settings.py` if needed
   - Ensure you have MPDB database access credentials

2. **Run Processing Pipeline:**
   - Open and run MPDB_notebook.ipynb
   - Follow the step-by-step processing workflow
   - Provides interactive database connection

## Methods

**Blank Correction:**
- Matches particles in samples with laboratory blank particles
- Removes closest size matches by phenotype (polymer, color, shape)
- Tracks all eliminations for transparency


## Configuration

Key settings in `MPDB_settings.py`:
- `size_filter_highpass`: Minimum particle size (default: 50 μm)
- `size_filter_lowpass`: Maximum particle size (default: 5000 μm)  
- `polyDropList`: Polymers to exclude from analysis
- `blindList`: Blind samples to include in processing

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.
