#!/usr/bin/env python3
"""
Command-line tool for running particle correction workflows.

This tool processes particle data according to a YAML configuration file
that defines which files should be corrected by which control samples.
"""

import argparse
import sys
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microplas_blind_corr.workflows import CorrectionWorkflow
from microplas_blind_corr.config import ProcessingConfig, EXCEL_COLUMN_MAPPING


def create_template(output_path: Path) -> None:
    """Create a template correction configuration file."""
    template_source = Path(__file__).parent.parent / "configs" / "correction_template.yaml"
    
    if not template_source.exists():
        print(f"❌ Template file not found: {template_source}")
        return
        
    # Copy template to specified location
    with open(template_source, 'r') as src:
        template_content = src.read()
        
    with open(output_path, 'w') as dst:
        dst.write(template_content)
        
    print(f"✅ Created template configuration file: {output_path}")
    print(f"📝 Edit this file to define your correction workflow")


def validate_config(config_file: Path, data_directory: Path) -> bool:
    """
    Validate a correction configuration file.
    
    Args:
        config_file: Path to configuration file
        data_directory: Data directory path
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Load configuration
        workflow = CorrectionWorkflow(ProcessingConfig(), EXCEL_COLUMN_MAPPING)
        workflow.load_correction_config(config_file, data_directory)
        
        print(f"✅ Configuration file is valid: {config_file}")
        
        # Check for circular dependencies
        circular_errors = workflow.detect_circular_dependencies()
        if circular_errors:
            print("⚠️  Circular dependencies detected:")
            for error in circular_errors:
                print(f"   • {error}")
            return False
            
        # Show processing order
        processing_order = workflow.resolve_processing_order()
        print(f"📋 Processing order ({len(processing_order)} steps):")
        for i, (target_file, control_files) in enumerate(processing_order, 1):
            control_list = ', '.join(control_files)
            print(f"   {i}. {target_file} ← {control_list}")
            
        # Check if files exist
        corrections = workflow.correction_config['corrections']
        missing_files = []
        
        for target_file, control_files in corrections.items():
            if isinstance(control_files, str):
                control_files = [control_files]
                
            # Check target file
            target_path = workflow._resolve_file_path(target_file)
            if not target_path.exists():
                missing_files.append(target_file)
                
            # Check control files
            for control_file in control_files:
                control_path = workflow._resolve_file_path(control_file)
                if not control_path.exists():
                    missing_files.append(control_file)
                    
        if missing_files:
            print("⚠️  Missing files:")
            for file in set(missing_files):
                print(f"   • {file}")
            return False
            
        print("🎉 All validation checks passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


def run_workflow(config_file: Path, data_directory: Path, dry_run: bool = False) -> None:
    """
    Run the correction workflow.
    
    Args:
        config_file: Path to configuration file
        data_directory: Data directory path
        dry_run: If True, validate only without processing
    """
    try:
        print(f"🔧 Starting particle correction workflow")
        print(f"📁 Data directory: {data_directory}")
        print(f"⚙️  Configuration: {config_file}")
        print()
        
        # Initialize workflow
        config = ProcessingConfig()
        workflow = CorrectionWorkflow(config, EXCEL_COLUMN_MAPPING)
        workflow.load_correction_config(config_file, data_directory)
        
        # Validate configuration first
        if not validate_config(config_file, data_directory):
            print("❌ Configuration validation failed. Please fix errors before running.")
            return
            
        if dry_run:
            print("🏃 Dry run complete - configuration is valid")
            return
            
        print()
        print("🚀 Running correction workflow...")
        
        # Run the workflow
        results = workflow.run_workflow()
        
        # Display results
        print()
        print("📊 Workflow Results:")
        print(f"   • Total corrections applied: {results['total_corrections']}")
        print(f"   • Total particles eliminated: {results['total_particles_eliminated']:,}")
        print()
        
        print("📋 Correction Details:")
        for correction in results['processed_files']:
            target = correction['target_file']
            controls = ', '.join(correction['control_files'])
            eliminated = correction['particles_eliminated']
            remaining = correction['final_particles']
            output = correction['output_file']
            
            print(f"   • {target}")
            print(f"     Controls: {controls}")
            print(f"     Eliminated: {eliminated:,} particles")
            print(f"     Remaining: {remaining:,} particles")
            print(f"     Output: {output}")
            print()
            
        # Save workflow report
        report_path = workflow.output_directory / "workflow_report.json"
        with open(report_path, 'w') as f:
            # Convert DataFrames to dict for JSON serialization
            json_results = results.copy()
            json_results['correction_logs'] = [
                log.to_dict('records') if hasattr(log, 'to_dict') else str(log)
                for log in results['correction_logs']
            ]
            json.dump(json_results, f, indent=2, default=str)
            
        print(f"📄 Detailed report saved: {report_path}")
        print("✅ Workflow completed successfully!")
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        sys.exit(1)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Run particle correction workflows using YAML configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a template configuration file
  python run_corrections.py template data/corrections.yaml

  # Validate configuration without running
  python run_corrections.py validate data/corrections.yaml --data-dir data/

  # Run the correction workflow
  python run_corrections.py run data/corrections.yaml --data-dir data/

  # Dry run (validate only)
  python run_corrections.py run data/corrections.yaml --data-dir data/ --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Create template configuration file')
    template_parser.add_argument('output', type=Path, help='Output path for template file')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration file')
    validate_parser.add_argument('config', type=Path, help='Path to correction configuration file')
    validate_parser.add_argument('--data-dir', type=Path, default=Path('data'),
                                help='Directory containing data files (default: data)')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run correction workflow')
    run_parser.add_argument('config', type=Path, help='Path to correction configuration file')
    run_parser.add_argument('--data-dir', type=Path, default=Path('data'),
                           help='Directory containing data files (default: data)')
    run_parser.add_argument('--dry-run', action='store_true',
                           help='Validate configuration without running corrections')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    if args.command == 'template':
        create_template(args.output)
    elif args.command == 'validate':
        validate_config(args.config, args.data_dir)
    elif args.command == 'run':
        run_workflow(args.config, args.data_dir, args.dry_run)


if __name__ == "__main__":
    main()
