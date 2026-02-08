"""CLI utilities for API communication and formatting."""
import os
import sys
import requests
from typing import Optional, Dict, Any
from pathlib import Path

# Try to import rich for pretty output, fallback to plain text
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Try to import tabulate for table formatting
try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False


# API Configuration
DEFAULT_API_URL = "http://localhost:8000"


def get_api_url() -> str:
    """Get API URL from environment or default."""
    return os.environ.get("TRADEMIND_API_URL", DEFAULT_API_URL)


API_BASE = get_api_url()


def format_value(value):
    """Format a value for display."""
    if isinstance(value, bool):
        return "True" if value else "False"
    elif isinstance(value, float):
        if 0 < abs(value) < 1:
            return f"{value:.2%}"
        return f"{value:.4f}"
    elif isinstance(value, int):
        return f"{value:,}"
    else:
        return str(value)


def api_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Make an API request to the TradeMind server.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (e.g., '/api/portfolio')
        json_data: JSON payload for POST/PUT requests
        params: Query parameters
        
    Returns:
        Response JSON dict or None if error
    """
    base_url = get_api_url()
    url = f"{base_url}{endpoint}"
    
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            json=json_data,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        error_msg = f"❌ Cannot connect to TradeMind server at {base_url}\n"
        error_msg += "   Is the server running? Start it with: trademind server start"
        print_error(error_msg)
        return None
    except requests.exceptions.Timeout:
        print_error("❌ Request timed out. Server may be busy.")
        return None
    except requests.exceptions.HTTPError as e:
        print_error(f"❌ API error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print_error(f"❌ Error: {str(e)}")
        return None


def print_error(message: str):
    """Print error message with formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[red]{message}[/red]")
    else:
        print(message)


def print_success(message: str):
    """Print success message with formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[green]{message}[/green]")
    else:
        print(message)


def print_warning(message: str):
    """Print warning message with formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[yellow]{message}[/yellow]")
    else:
        print(message)


def print_info(message: str):
    """Print info message with formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[cyan]{message}[/cyan]")
    else:
        print(message)


def format_table(data: list, headers: list, title: Optional[str] = None) -> str:
    """
    Format data as a table.
    
    Args:
        data: List of rows (each row is a list)
        headers: List of column headers
        title: Optional table title
        
    Returns:
        Formatted table string
    """
    if RICH_AVAILABLE and console and title:
        # Use rich table for titled tables
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for header in headers:
            table.add_column(header)
        for row in data:
            table.add_row(*[str(cell) for cell in row])
        console.print(table)
        return ""
    elif TABULATE_AVAILABLE:
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        return tabulate(data, headers=headers, tablefmt="simple")
    else:
        # Fallback to simple formatting
        output = []
        if title:
            output.append(f"\n{title}")
            output.append("=" * len(title))
        
        # Headers
        header_line = " | ".join(headers)
        output.append(header_line)
        output.append("-" * len(header_line))
        
        # Rows
        for row in data:
            output.append(" | ".join(str(cell) for cell in row))
        
        return "\n".join(output)


def print_panel(content: str, title: Optional[str] = None):
    """Print content in a panel."""
    if RICH_AVAILABLE and console:
        panel = Panel(content, title=title, border_style="blue")
        console.print(panel)
    else:
        if title:
            print(f"\n{'='*40}")
            print(f"  {title}")
            print(f"{'='*40}")
        print(content)
        if title:
            print(f"{'='*40}")


def format_currency(amount: float, prefix: str = "$") -> str:
    """Format amount as currency."""
    if amount >= 0:
        return f"{prefix}{amount:,.2f}"
    else:
        return f"-{prefix}{abs(amount):,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage with color indicator."""
    formatted = f"{value:+.2f}%" if value != 0 else f"{value:.2f}%"
    
    if RICH_AVAILABLE:
        if value > 0:
            return f"[green]{formatted}[/green]"
        elif value < 0:
            return f"[red]{formatted}[/red]"
        else:
            return formatted
    else:
        return formatted


def status_emoji(status: bool) -> str:
    """Return emoji for status."""
    return "✅" if status else "❌"


def get_server_pid_file() -> Path:
    """Get path to server PID file."""
    return Path.home() / ".trademind" / "server.pid"


def get_config_dir() -> Path:
    """Get configuration directory."""
    config_dir = Path.home() / ".trademind"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
