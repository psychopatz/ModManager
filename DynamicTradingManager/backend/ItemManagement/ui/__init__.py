"""UI module for ItemGenerator - handles menu display and statistics"""

from .stats import display_mod_stats
from .menu import display_interactive_menu, handle_menu_choice

__all__ = ['display_mod_stats', 'display_interactive_menu', 'handle_menu_choice']
