#!/bin/bash
# uv_manage.sh - Unified uv management script for censys-toolkit

set -e  # Exit immediately if a command exits with a non-zero status

# Display help message
function show_help {
  echo "Usage: $0 [command] [options]"
  echo ""
  echo "Unified script to manage Python environment and development tasks using uv."
  echo ""
  echo "Commands:"
  echo "  setup         Create a virtual environment and install dependencies"
  echo "  dev           Install development dependencies"
  echo "  update        Update the lockfile with current dependencies"
  echo "  format        Format code with black and isort"
  echo "  check         Run type checking with mypy"
  echo "  test          Run tests with pytest"
  echo "    test unit       Run only unit tests"
  echo "    test integration Run only integration tests"
  echo "    test cov        Run tests with coverage report"
  echo "    test fast       Skip slow tests"
  echo "  lint          Run all linters and formatters"
  echo "  clean         Clean build artifacts"
  echo "  build         Build distribution packages"
  echo "  help          Show this help message"
  echo ""
  echo "If no command is provided, 'help' is executed by default."
}

# Check if uv is installed
function check_uv {
  if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  # or"
    echo "  python -m pip install uv"
    exit 1
  fi
}

# Ensure we're in the virtual environment if needed
function ensure_venv {
  if [ -z "$VIRTUAL_ENV" ] && [ "$1" != "setup" ]; then
    if [ -d ".venv" ]; then
      echo "Activating virtual environment..."
      # Try to source the activate script (handles both Unix and Windows paths)
      if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
      elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
      else
        echo "Error: Activation script not found. Run './scripts/uv_manage.sh setup' first."
        exit 1
      fi
    else
      echo "Error: Virtual environment not found. Run './scripts/uv_manage.sh setup' first."
      exit 1
    fi
  fi
}

# Create virtual environment and install dependencies
function setup_env {
  echo "Creating virtual environment with uv..."
  uv venv

  echo "Installing project dependencies..."
  uv pip install -e .
  
  echo "Environment setup complete."
  echo "To activate: source .venv/bin/activate (Unix/macOS) or .venv\\Scripts\\activate (Windows)"
}

# Install development dependencies
function install_dev {
  echo "Installing development dependencies..."
  uv pip install -e ".[dev]"
  echo "Development dependencies installed."
}

# Update lockfile
function update_lockfile {
  echo "Updating lockfile with current dependencies..."
  uv pip compile --upgrade pyproject.toml -o uv.lock
  echo "Lockfile updated."
}

# Format code
function format_code {
  echo "Formatting code..."
  uv run black censyspy/
  uv run isort censyspy/
  echo "Code formatting complete."
}

# Run type checking
function run_typecheck {
  echo "Running type checking with mypy..."
  uv run mypy censyspy
  echo "Type checking complete."
}

# Run tests with options
function run_tests {
  echo "Running tests..."
  shift
  if [ -z "$1" ]; then
    # Run all tests
    uv run pytest
  elif [ "$1" == "unit" ]; then
    # Run only unit tests
    uv run pytest -m "unit" "${@:2}"
  elif [ "$1" == "integration" ]; then
    # Run only integration tests
    uv run pytest -m "integration" "${@:2}"
  elif [ "$1" == "cov" ]; then
    # Run tests with coverage report
    uv run pytest --cov=censyspy --cov-report=html --cov-report=term
    echo "Coverage report generated in htmlcov/"
  elif [ "$1" == "fast" ]; then
    # Skip slow tests
    uv run pytest -k "not slow" "${@:2}"
  else
    # Pass all arguments to pytest
    uv run pytest "$@"
  fi
  echo "Tests complete."
}

# Run all linters
function run_lint {
  echo "Running all linters and formatters..."
  uv run black --check censyspy/
  uv run isort --check censyspy/
  uv run mypy censyspy/
  echo "Linting complete."
}

# Clean build artifacts
function clean_build {
  echo "Cleaning build artifacts..."
  rm -rf build/ dist/ *.egg-info
  find . -type d -name __pycache__ -exec rm -rf {} +
  find . -type f -name "*.pyc" -delete
  echo "Clean complete."
}

# Build distribution packages
function build_dist {
  echo "Building distribution packages..."
  uv run python -m build
  echo "Build complete. Packages in dist/"
}

# Initial checks
check_uv

# Main command processing
case "$1" in
  setup)
    setup_env
    ;;
  dev)
    ensure_venv "$1"
    install_dev
    ;;
  update)
    ensure_venv "$1"
    update_lockfile
    ;;
  format)
    ensure_venv "$1"
    format_code
    ;;
  check)
    ensure_venv "$1"
    run_typecheck
    ;;
  test)
    ensure_venv "$1"
    run_tests "$@"
    ;;
  lint)
    ensure_venv "$1"
    run_lint
    ;;
  clean)
    ensure_venv "$1"
    clean_build
    ;;
  build)
    ensure_venv "$1"
    build_dist
    ;;
  help|"")
    # Default command when none is provided
    show_help
    ;;
  *)
    echo "Unknown command: $1"
    show_help
    exit 1
    ;;
esac

exit 0