#!/bin/bash
# Setup Verification Script for Spelling Words Project
# This script verifies that the development environment is properly configured

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "Spelling Words - Setup Verification"
echo "======================================"
echo ""

# Track overall status
ERRORS=0
WARNINGS=0

# Helper functions
error() {
    echo "❌ ERROR: $1"
    ERRORS=$((ERRORS + 1))
}

warning() {
    echo "⚠️  WARNING: $1"
    WARNINGS=$((WARNINGS + 1))
}

success() {
    echo "✅ $1"
}

info() {
    echo "ℹ️  $1"
}

# 1. Check ffmpeg
echo "1. Checking system dependencies..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
    success "ffmpeg is installed: $FFMPEG_VERSION"
else
    error "ffmpeg is not installed. Install with: sudo apt-get install ffmpeg"
fi
echo ""

# 2. Check Python version
echo "2. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    success "Python is installed: $PYTHON_VERSION"

    # Check if it's 3.12+
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "$PYTHON_MINOR" -lt 12 ]; then
        warning "Python 3.12+ is recommended, you have Python 3.$PYTHON_MINOR"
    fi
else
    error "Python 3 is not installed"
fi
echo ""

# 3. Check uv
echo "3. Checking uv package manager..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1)
    success "uv is installed: $UV_VERSION"
else
    error "uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
echo ""

# 4. Check project files
echo "4. Checking project files..."
cd "$PROJECT_DIR"

if [ -f "pyproject.toml" ]; then
    success "pyproject.toml exists"
else
    error "pyproject.toml is missing"
fi

if [ -f ".pre-commit-config.yaml" ]; then
    success ".pre-commit-config.yaml exists"
else
    error ".pre-commit-config.yaml is missing"
fi

if [ -f ".gitignore" ]; then
    success ".gitignore exists"
else
    error ".gitignore is missing"
fi

if [ -f ".env.example" ]; then
    success ".env.example exists"
else
    warning ".env.example is missing"
fi

if [ -f "README_LLM.md" ]; then
    success "README_LLM.md exists"
else
    warning "README_LLM.md is missing"
fi
echo ""

# 5. Check directory structure
echo "5. Checking directory structure..."
REQUIRED_DIRS=(
    "spelling_words"
    "tests"
    "tests/fixtures"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        success "Directory exists: $dir"
    else
        warning "Directory missing: $dir (will be created)"
    fi
done
echo ""

# 6. Check Python module files
echo "6. Checking Python module files..."
REQUIRED_FILES=(
    "spelling_words/__init__.py"
    "spelling_words/__main__.py"
    "tests/__init__.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "File exists: $file"
    else
        warning "File missing: $file (will be created)"
    fi
done
echo ""

# 7. Check if dependencies are installed
echo "7. Checking if dependencies are installed..."
if [ -d ".venv" ] || [ -d "venv" ]; then
    success "Virtual environment exists"

    # Check if we can import key packages
    if uv run python -c "import click" 2>/dev/null; then
        success "Dependencies appear to be installed"
    else
        warning "Dependencies may not be installed. Run: uv sync"
    fi
else
    warning "Virtual environment not found. Run: uv sync"
fi
echo ""

# 8. Check if pre-commit hooks are installed
echo "8. Checking pre-commit hooks..."
if [ -d ".git/hooks" ] && [ -f ".git/hooks/pre-commit" ]; then
    success "Pre-commit hooks are installed"
else
    warning "Pre-commit hooks not installed. Run: uv run pre-commit install"
fi
echo ""

# 9. Check for .env file
echo "9. Checking environment configuration..."
if [ -f ".env" ]; then
    success ".env file exists"

    # Check for required API key
    if grep -q "MW_ELEMENTARY_API_KEY=" ".env" && ! grep -q "MW_ELEMENTARY_API_KEY=your-elementary-api-key-here" ".env"; then
        success "MW_ELEMENTARY_API_KEY is configured"
    else
        warning "MW_ELEMENTARY_API_KEY not configured in .env"
    fi
else
    warning ".env file not found. Copy .env.example to .env and configure API keys"
fi
echo ""

# Summary
echo "======================================"
echo "Verification Summary"
echo "======================================"
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo "✅ All checks passed! Your environment is ready."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo "⚠️  Setup is mostly complete with $WARNINGS warning(s)."
    echo "    Review warnings above and fix as needed."
    exit 0
else
    echo "❌ Setup verification failed with $ERRORS error(s)."
    echo "    Please fix errors before proceeding."
    exit 1
fi
