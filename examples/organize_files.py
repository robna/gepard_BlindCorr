#!/usr/bin/env python3
"""
Command-line utility for organizing microplastics Excel files.

This script helps users organize their Excel files into appropriate
categories (environmental, blank, blind) and validate file structure.
"""

import argparse
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from microplas_blind_corr.config import EXCEL_COLUMN_MAPPING
from microplas_blind_corr.utils import FileOrganizer


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Organize and validate microplastics Excel files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze files in a directory
  python organize_files.py analyze /path/to/data/

  # Validate specific files
  python organize_files.py validate file1.xlsx file2.xlsx

  # Get organization suggestions
  python organize_files.py suggest /path/to/data/
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze files in a directory')
    analyze_parser.add_argument('directory', type=Path, help='Directory containing Excel files')
    analyze_parser.add_argument('--env-patterns', nargs='+', default=['sample', 'environmental', 'env', 'sediment', 'water', 'biota'],
                               help='Patterns to identify environmental files')
    analyze_parser.add_argument('--blank-patterns', nargs='+', default=['blank', 'control'],
                               help='Patterns to identify blank files')
    analyze_parser.add_argument('--blind-patterns', nargs='+', default=['blind', 'spike'],
                               help='Patterns to identify blind files')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate specific Excel files')
    validate_parser.add_argument('files', nargs='+', type=Path, help='Excel files to validate')
    
    # Suggest command
    suggest_parser = subparsers.add_parser('suggest', help='Get file organization suggestions')
    suggest_parser.add_argument('directory', type=Path, help='Directory to analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    # Initialize file organizer
    organizer = FileOrganizer(EXCEL_COLUMN_MAPPING)
    
    if args.command == 'analyze':
        analyze_files(organizer, args)
    elif args.command == 'validate':
        validate_files(organizer, args)
    elif args.command == 'suggest':
        suggest_organization(organizer, args)


def analyze_files(organizer: FileOrganizer, args):
    """Analyze files in a directory."""
    print(f"🔍 Analyzing files in: {args.directory}")
    print()
    
    try:
        categorized = organizer.organize_files_by_pattern(
            args.directory,
            args.env_patterns,
            args.blank_patterns, 
            args.blind_patterns
        )
        
        total_files = sum(len(files) for files in categorized.values())
        print(f"📊 Found {total_files} Excel files:")
        print()
        
        for file_type, files in categorized.items():
            if files:
                print(f"📁 {file_type.title()} files ({len(files)}):")
                for file_path in files:
                    # Validate each file
                    validation = organizer.validate_file_structure(file_path)
                    status = "✅" if validation['valid'] else "❌"
                    particle_count = validation['particle_count']
                    print(f"   {status} {file_path.name} ({particle_count:,} particles)")
                    
                    if validation['errors']:
                        for error in validation['errors']:
                            print(f"      ⚠️ {error}")
                print()
                
        if categorized['unclassified']:
            print("❓ Unclassified files:")
            print("   These files don't match any patterns. Consider renaming them.")
            for file_path in categorized['unclassified']:
                print(f"   📄 {file_path.name}")
            print()
            
    except Exception as e:
        print(f"❌ Error analyzing files: {e}")


def validate_files(organizer: FileOrganizer, args):
    """Validate specific files."""
    print(f"🔍 Validating {len(args.files)} files:")
    print()
    
    overall_valid = True
    
    for file_path in args.files:
        print(f"📄 {file_path.name}")
        
        validation = organizer.validate_file_structure(file_path)
        
        if validation['valid']:
            print(f"   ✅ Valid ({validation['particle_count']:,} particles)")
        else:
            print(f"   ❌ Invalid")
            overall_valid = False
            
        for error in validation['errors']:
            print(f"   ⚠️ Error: {error}")
            
        for warning in validation['warnings']:
            print(f"   ⚠️ Warning: {warning}")
            
        print(f"   📋 Columns: {', '.join(validation['columns_found'][:3])}{'...' if len(validation['columns_found']) > 3 else ''}")
        print()
        
    if overall_valid:
        print("✅ All files are valid!")
    else:
        print("❌ Some files have issues that need to be addressed.")


def suggest_organization(organizer: FileOrganizer, args):
    """Suggest file organization."""
    print(organizer.suggest_file_organization(args.directory))


if __name__ == "__main__":
    main()
