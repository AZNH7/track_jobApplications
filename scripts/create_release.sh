#!/bin/bash

# Release Management Script for Job Application Tracker
# This script helps create releases and update version numbers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get current version
get_current_version() {
    cat VERSION
}

# Function to update version
update_version() {
    local new_version=$1
    echo "$new_version" > VERSION
    print_success "Version updated to $new_version"
}

# Function to create a release
create_release() {
    local version=$1
    local release_notes=$2
    
    print_status "Creating release v$version..."
    
    # Update version file
    update_version "$version"
    
    # Create git tag
    git add VERSION
    git commit -m "Bump version to $version"
    git tag -a "v$version" -m "Release v$version"
    
    print_success "Release v$version created successfully!"
    print_status "To push the release:"
    echo "  git push origin main"
    echo "  git push origin v$version"
}

# Function to show help
show_help() {
    echo "Job Application Tracker Release Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  version                    Show current version"
    echo "  bump [major|minor|patch]   Bump version number"
    echo "  release [version]          Create a new release"
    echo "  help                       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 version                 # Show current version"
    echo "  $0 bump patch              # Bump patch version (1.0.0 -> 1.0.1)"
    echo "  $0 bump minor              # Bump minor version (1.0.0 -> 1.1.0)"
    echo "  $0 bump major              # Bump major version (1.0.0 -> 2.0.0)"
    echo "  $0 release 1.1.0           # Create release v1.1.0"
    echo ""
}

# Function to bump version
bump_version() {
    local bump_type=$1
    local current_version=$(get_current_version)
    local major minor patch
    
    # Parse current version
    IFS='.' read -r major minor patch <<< "$current_version"
    
    case $bump_type in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
        *)
            print_error "Invalid bump type. Use: major, minor, or patch"
            exit 1
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    update_version "$new_version"
    print_success "Version bumped to $new_version"
}

# Main script logic
case "${1:-help}" in
    "version")
        print_status "Current version: $(get_current_version)"
        ;;
    "bump")
        if [ -z "$2" ]; then
            print_error "Please specify bump type: major, minor, or patch"
            exit 1
        fi
        bump_version "$2"
        ;;
    "release")
        if [ -z "$2" ]; then
            print_error "Please specify version number"
            exit 1
        fi
        create_release "$2"
        ;;
    "help"|*)
        show_help
        ;;
esac
