"""Server management commands."""
import os
import signal
import subprocess
import time
import click
from pathlib import Path

from cli.utils import (
    api_request, print_success, print_error, print_warning, print_info,
    format_table, get_server_pid_file, get_config_dir
)


@click.group()
def server():
    """Server management commands."""
    pass


@server.command()
@click.option('--port', default=8000, help='Server port')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes')
@click.option('--daemon/--no-daemon', default=True, help='Run as background daemon')
def start(port, reload, daemon):
    """Start the trading server."""
    pid_file = get_server_pid_file()
    
    # Check if already running
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            print_warning(f"⚠️  Server already running (PID: {pid})")
            return
        except (ValueError, OSError, ProcessLookupError):
            # Stale PID file
            pid_file.unlink()
    
    project_dir = Path.home() / "projects" / "trading-agent"
    
    if daemon:
        # Start as background process
        print_info(f"🚀 Starting TradeMind server on port {port}...")
        
        # Use nohup to keep running after terminal closes
        log_file = get_config_dir() / "server.log"
        
        cmd = [
            "python", "-m", "uvicorn",
            "src.main:app",
            "--host", "0.0.0.0",
            "--port", str(port)
        ]
        if reload:
            cmd.append("--reload")
        
        # Start process
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=project_dir,
                start_new_session=True
            )
        
        # Save PID
        pid_file.write_text(str(process.pid))
        
        # Wait a moment and check if it's running
        time.sleep(2)
        try:
            os.kill(process.pid, 0)
            print_success(f"✅ Server started (PID: {process.pid})")
            print_info(f"   API: http://localhost:{port}")
            print_info(f"   Dashboard: http://localhost:{port}")
            print_info(f"   Logs: {log_file}")
        except OSError:
            print_error("❌ Failed to start server. Check logs.")
            if pid_file.exists():
                pid_file.unlink()
    else:
        # Run in foreground
        print_info(f"🚀 Starting TradeMind server on port {port} (foreground)...")
        try:
            import uvicorn
            uvicorn.run(
                "src.main:app",
                host="0.0.0.0",
                port=port,
                reload=reload,
                app_dir=str(project_dir)
            )
        except ImportError:
            print_error("❌ uvicorn not installed. Run: pip install uvicorn")


@server.command()
def stop():
    """Stop the trading server."""
    pid_file = get_server_pid_file()
    
    if not pid_file.exists():
        print_warning("⚠️  Server not running (no PID file found)")
        return
    
    try:
        pid = int(pid_file.read_text().strip())
        
        # Try graceful shutdown first
        print_info(f"🛑 Stopping server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to terminate
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                break
        else:
            # Force kill if still running
            print_warning("⚠️  Force killing server...")
            os.kill(pid, signal.SIGKILL)
        
        pid_file.unlink()
        print_success("✅ Server stopped")
        
    except (ValueError, ProcessLookupError):
        print_warning("⚠️  Server not running (stale PID file removed)")
        pid_file.unlink()
    except Exception as e:
        print_error(f"❌ Error stopping server: {str(e)}")


@server.command()
def status():
    """Check server status."""
    pid_file = get_server_pid_file()
    
    # Check PID file
    pid = None
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
        except (ValueError, OSError, ProcessLookupError):
            pid = None
            pid_file.unlink()
    
    # Check API health
    response = api_request("GET", "/health")
    
    if response:
        print_success("✅ Server is running")
        if pid:
            print_info(f"   PID: {pid}")
        print_info(f"   App: {response.get('app', 'TradeMind AI')}")
        print_info(f"   Status: {response.get('status', 'healthy')}")
        print_info(f"   API: http://localhost:8000")
    else:
        print_error("❌ Server not responding")
        if pid:
            print_warning(f"   PID file exists ({pid}) but process not responding")


@server.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
def logs(follow, lines):
    """View server logs."""
    log_file = get_config_dir() / "server.log"
    
    if not log_file.exists():
        print_warning("⚠️  No log file found")
        return
    
    if follow:
        # Use tail -f equivalent
        try:
            import subprocess
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            print()
    else:
        # Read last N lines
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line.rstrip())
        except Exception as e:
            print_error(f"❌ Error reading logs: {str(e)}")


@server.command()
@click.option('--port', default=8000, help='Server port')
@click.option('--reload', is_flag=True, help='Auto-reload on code changes')
def restart(port, reload):
    """Restart the trading server."""
    print_info("🔄 Restarting server...")
    
    # Stop if running
    pid_file = get_server_pid_file()
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        except:
            pass
    
    # Start again
    ctx = click.get_current_context()
    ctx.invoke(start, port=port, reload=reload, daemon=True)
