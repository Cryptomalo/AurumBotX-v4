#!/bin/bash

##############################################################################
# Bot Monitoring Script
# Description: Monitors bot_output.log and provides real-time status updates
# Features:
#   - Proper file existence checks before reading
#   - Improved error handling and recovery
#   - Robustness to missing or inaccessible files
#   - Clear error messages and logging
##############################################################################

set -o pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BOT_LOG="${PROJECT_ROOT}/bot_output.log"
LOG_CHECK_INTERVAL=2
ERROR_LOG="${PROJECT_ROOT}/monitor_errors.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

##############################################################################
# Helper Functions
##############################################################################

# Log errors to file and console
log_error() {
    local message="$1"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo -e "${RED}[ERROR]${NC} $message" >&2
    echo "[$timestamp] ERROR: $message" >> "$ERROR_LOG" 2>/dev/null || true
}

# Log info messages
log_info() {
    local message="$1"
    echo -e "${BLUE}[INFO]${NC} $message"
}

# Log success messages
log_success() {
    local message="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $message"
}

# Log warning messages
log_warning() {
    local message="$1"
    echo -e "${YELLOW}[WARNING]${NC} $message"
}

# Check if file exists and is readable
check_file_exists() {
    local file_path="$1"
    
    if [[ ! -e "$file_path" ]]; then
        return 1
    fi
    
    if [[ ! -r "$file_path" ]]; then
        log_error "Log file exists but is not readable: $file_path"
        return 2
    fi
    
    return 0
}

# Initialize monitoring
initialize_monitor() {
    log_info "Initializing bot monitor..."
    
    # Check if project root exists
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log_error "Project root directory not found: $PROJECT_ROOT"
        return 1
    fi
    
    # Check if bot log file exists, if not, create it or wait for it
    if ! check_file_exists "$BOT_LOG"; then
        log_warning "Bot output log not found: $BOT_LOG"
        log_info "Waiting for bot to start logging..."
        
        # Wait up to 30 seconds for the log file to be created
        local wait_count=0
        local max_wait=15
        
        while [[ ! -f "$BOT_LOG" ]] && [[ $wait_count -lt $max_wait ]]; do
            sleep 2
            ((wait_count++))
        done
        
        if [[ ! -f "$BOT_LOG" ]]; then
            log_error "Bot log file was not created within ${max_wait}0 seconds"
            log_info "You can start monitoring once the bot begins logging"
            return 1
        fi
    fi
    
    log_success "Monitor initialized successfully"
    return 0
}

# Display current log tail
display_log_tail() {
    local num_lines="${1:-20}"
    
    if ! check_file_exists "$BOT_LOG"; then
        log_warning "Log file not accessible: $BOT_LOG"
        return 1
    fi
    
    if [[ ! -s "$BOT_LOG" ]]; then
        log_info "Log file is empty"
        return 0
    fi
    
    log_info "Last $num_lines lines of bot output:"
    echo "---"
    tail -n "$num_lines" "$BOT_LOG" 2>/dev/null || {
        log_error "Failed to read log file"
        return 1
    }
    echo "---"
    
    return 0
}

# Monitor log file in real-time
monitor_log_realtime() {
    log_info "Starting real-time log monitoring..."
    log_info "Press Ctrl+C to stop monitoring"
    echo ""
    
    if ! check_file_exists "$BOT_LOG"; then
        log_error "Cannot start monitoring - log file not accessible"
        return 1
    fi
    
    # Use tail -f with error handling
    if ! tail -f "$BOT_LOG" 2>/dev/null; then
        log_error "Failed to tail log file. File may have been deleted."
        return 1
    fi
    
    return 0
}

# Check bot status
check_bot_status() {
    log_info "Checking bot status..."
    
    if ! check_file_exists "$BOT_LOG"; then
        log_warning "Bot log file not found - bot may not be running yet"
        return 1
    fi
    
    # Check file size
    local file_size
    file_size=$(stat -f%z "$BOT_LOG" 2>/dev/null || stat -c%s "$BOT_LOG" 2>/dev/null || echo "unknown")
    
    if [[ "$file_size" == "unknown" ]]; then
        log_warning "Could not determine log file size"
    else
        log_info "Log file size: $file_size bytes"
    fi
    
    # Check if log file is being written to (modified recently)
    local last_modified
    last_modified=$(stat -f%m "$BOT_LOG" 2>/dev/null || stat -c%Y "$BOT_LOG" 2>/dev/null || echo "0")
    
    if [[ "$last_modified" != "0" ]]; then
        local current_time
        current_time=$(date +%s)
        local time_diff=$((current_time - last_modified))
        
        if [[ $time_diff -lt 60 ]]; then
            log_success "Bot is actively logging (modified $(date -d @"$last_modified" 2>/dev/null || echo "recently"))"
        else
            log_warning "Log file hasn't been modified for $time_diff seconds"
        fi
    fi
    
    # Check for errors in recent log entries
    local error_count
    error_count=$(grep -ci "error\|exception\|failed" "$BOT_LOG" 2>/dev/null || echo "0")
    
    if [[ $error_count -gt 0 ]]; then
        log_warning "Found $error_count error-related entries in log"
    else
        log_success "No recent errors detected"
    fi
    
    return 0
}

# Clean up and rotate logs if needed
cleanup_logs() {
    log_info "Cleaning up old logs..."
    
    # Archive old error logs if they exceed 1MB
    if [[ -f "$ERROR_LOG" ]]; then
        local log_size
        log_size=$(stat -f%z "$ERROR_LOG" 2>/dev/null || stat -c%s "$ERROR_LOG" 2>/dev/null || echo "0")
        
        if [[ $log_size -gt 1048576 ]]; then
            local archive_name="${ERROR_LOG}.$(date +%Y%m%d_%H%M%S)"
            mv "$ERROR_LOG" "$archive_name" 2>/dev/null && log_info "Archived old error log to $archive_name" || true
        fi
    fi
}

# Display help
show_help() {
    cat << EOF
Usage: ./monitor.sh [COMMAND] [OPTIONS]

Commands:
    start           Start real-time monitoring of bot output
    status          Check current bot status and log file
    tail [N]        Display last N lines (default: 20)
    help            Show this help message

Options:
    -h, --help      Show this help message

Examples:
    ./monitor.sh start              # Start real-time monitoring
    ./monitor.sh status             # Check bot status
    ./monitor.sh tail 50            # Show last 50 lines
    ./monitor.sh tail               # Show last 20 lines

EOF
}

##############################################################################
# Main Script
##############################################################################

main() {
    local command="${1:-help}"
    
    # Ensure error log directory exists
    mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true
    
    case "$command" in
        start)
            initialize_monitor || exit 1
            monitor_log_realtime
            ;;
        status)
            check_bot_status
            echo ""
            display_log_tail 10
            ;;
        tail)
            local num_lines="${2:-20}"
            if ! [[ "$num_lines" =~ ^[0-9]+$ ]]; then
                log_error "Invalid number of lines: $num_lines"
                exit 1
            fi
            display_log_tail "$num_lines"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
    
    cleanup_logs
}

# Trap errors and exit gracefully
trap 'echo ""; log_warning "Monitor interrupted"; exit 0' INT TERM

# Run main function
main "$@"
