"""
Error handling and logging utilities
"""
import sys
import traceback
from pathlib import Path
from typing import Optional, Callable


class ItemGeneratorError(Exception):
    """Base exception for ItemGenerator errors"""
    def __init__(self, message: str, error_code: str = "ERR_GENERIC"):
        self.message = message
        self.error_code = error_code
        super().__init__(f"[{error_code}] {message}")


class DataLoadError(ItemGeneratorError):
    """Error loading input data"""
    def __init__(self, message: str):
        super().__init__(message, "ERR_DATA_LOAD")


class ValidationError(ItemGeneratorError):
    """Error validating data"""
    def __init__(self, message: str):
        super().__init__(message, "ERR_VALIDATION")


class PricingError(ItemGeneratorError):
    """Error calculating prices"""
    def __init__(self, message: str):
        super().__init__(message, "ERR_PRICING")


class OutputError(ItemGeneratorError):
    """Error writing output"""
    def __init__(self, message: str):
        super().__init__(message, "ERR_OUTPUT")


class ErrorHandler:
    """Centralized error handling and logging"""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self.errors = []
        self.warnings = []
        self.fatal = False
    
    def log_error(self, message: str, error_code: str = "ERR_UNKNOWN"):
        """Log an error"""
        full_msg = f"[{error_code}] {message}"
        self.errors.append(full_msg)
        print(f"❌ {full_msg}", file=sys.stderr)
        
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"ERROR: {full_msg}\n")
    
    def log_warning(self, message: str):
        """Log a warning"""
        self.warnings.append(message)
        print(f"⚠️  {message}")
        
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"WARNING: {message}\n")
    
    def log_exception(self, e: Exception, context: str = ""):
        """Log an exception with traceback"""
        msg = f"Exception in {context}: {str(e)}"
        self.errors.append(msg)
        print(f"❌ {msg}", file=sys.stderr)
        traceback.print_exc()
        
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"ERROR: {msg}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n")
    
    def mark_fatal(self):
        """Mark error handler as having fatal error"""
        self.fatal = True
    
    def summary(self) -> dict:
        """Get error summary"""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'is_fatal': self.fatal,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def print_summary(self):
        """Print error summary"""
        summary = self.summary()
        print("\n" + "=" * 60)
        print("ERROR SUMMARY")
        print("=" * 60)
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"Fatal: {summary['is_fatal']}")
        
        if self.errors:
            print("\nErrors:")
            for err in self.errors[:10]:
                print(f"  - {err}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        
        if self.warnings:
            print("\nWarnings:")
            for warn in self.warnings[:10]:
                print(f"  - {warn}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")


def safe_int_conversion(value, default: int = 0, error_handler: Optional[ErrorHandler] = None) -> int:
    """Safely convert value to int with error handling"""
    try:
        return int(value)
    except (ValueError, TypeError):
        if error_handler:
            error_handler.log_warning(f"Could not convert '{value}' to int, using default {default}")
        return default


def safe_float_conversion(value, default: float = 0.0, error_handler: Optional[ErrorHandler] = None) -> float:
    """Safely convert value to float with error handling"""
    try:
        return float(value)
    except (ValueError, TypeError):
        if error_handler:
            error_handler.log_warning(f"Could not convert '{value}' to float, using default {default}")
        return default


def safe_function_call(func: Callable, *args, fallback=None, error_handler: Optional[ErrorHandler] = None, error_msg: str = ""):
    """
    Safely call a function with error handling
    """
    try:
        return func(*args)
    except Exception as e:
        if error_handler:
            context = error_msg or f"Calling {func.__name__}"
            error_handler.log_exception(e, context)
        return fallback


def validate_required_field(data: dict, field_name: str, error_handler: Optional[ErrorHandler] = None) -> bool:
    """
    Validate that required field exists in data
    Returns True if valid
    """
    if field_name not in data:
        msg = f"Missing required field: {field_name}"
        if error_handler:
            error_handler.log_error(msg, "ERR_VALIDATION")
        return False
    
    if data[field_name] is None or (isinstance(data[field_name], str) and not data[field_name].strip()):
        msg = f"Empty required field: {field_name}"
        if error_handler:
            error_handler.log_warning(msg)
        return False
    
    return True


def validate_file_exists(filepath: Path, error_handler: Optional[ErrorHandler] = None) -> bool:
    """Validate that file exists"""
    if not filepath.exists():
        msg = f"File not found: {filepath}"
        if error_handler:
            error_handler.log_error(msg, "ERR_FILE_NOT_FOUND")
        return False
    return True
