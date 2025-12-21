#!/bin/bash

################################################################################
# AurumBotX Bot Loop Runner
# 
# This script continuously monitors and restarts the AurumBotX bot process.
# It supports running from any directory and uses relative paths based on the
# script's location for maximum portability.
#
# Features:
#   - Portable paths (works from any directory)
#   - Comprehensive error handling
#   - Graceful shutdown support
#   - Process monitoring and auto-restart
#   - Detailed logging
#
# Usage: bash scripts/run_bot_loop.sh [OPTIONS]
#        ./scripts/run_bot_loop.sh [OPTIONS]
#
# OPTIONS:
#   -h, --help              Show this help message
#   -l, --log-level LEVEL   Set logging level (DEBUG, INFO, WARN, ERROR)
#   -c, --config FILE       Use custom config file
#
################################################################################

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_DIR="${PROJECT_ROOT}/logs"
readonly LOG_FILE="${LOG_DIR}/bot_loop.log"
readonly PID_FILE="${PROJECT_ROOT}/.bot_pid"
readonly BOT_SCRIPT="${PROJECT_ROOT}/main.py"
readonly VENV_PATH="${PROJECT_ROOT}/venv"
readonly PYTHON_BIN="${VENV_PATH}/bin/python3"

# Default configuration
LOG_LEVEL="${LOG_LEVEL:-INFO}"
RESTART_DELAY="${RESTART_DELAY:-5}"
RESTART_MAX_ATTEMPTS="${RESTART_MAX_ATTEMPTS:-0}" # 0 = unlimited
RESTART_ATTEMPT=0
SHUTDOWN_REQUESTED=false

################################################################################
# Logging Functions
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${timestamp} - ${message}" >&2
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${timestamp} - ${message}" >&2
            ;;
        INFO)
            echo -e "${GREEN}[INFO]${NC} ${timestamp} - ${message}"
            ;;
        DEBUG)
            if [[ "$LOG_LEVEL" == "DEBUG" ]]; then
                echo -e "${BLUE}[DEBUG]${NC} ${timestamp} - ${message}"
            fi
            ;;
    esac
    
    # Also write to log file
    echo "[${level}] ${timestamp} - ${message}" >> "$LOG_FILE" 2>/dev/null || true
}

################################################################################
# Initialization Functions
################################################################################

initialize() {
    log INFO "Initializing AurumBotX Bot Loop Runner..."
    
    # Create necessary directories
    if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
        log ERROR "Failed to create log directory: $LOG_DIR"
        return 1
    fi
    
    # Initialize log file
    if ! touch "$LOG_FILE" 2>/dev/null; then
        log ERROR "Failed to create log file: $LOG_FILE"
        return 1
    fi
    
    log INFO "Project root: $PROJECT_ROOT"
    log INFO "Bot script: $BOT_SCRIPT"
    log INFO "Log file: $LOG_FILE"
    log INFO "Virtual environment: $VENV_PATH"
    
    return 0
}

validate_environment() {
    log INFO "Validating environment..."
    
    # Check if project root exists
    if [[ ! -d "$PROJECT_ROOT" ]]; then
        log ERROR "Project root does not exist: $PROJECT_ROOT"
        return 1
    fi
    
    # Check if bot script exists
    if [[ ! -f "$BOT_SCRIPT" ]]; then
        log ERROR "Bot script not found: $BOT_SCRIPT"
        log INFO "Expected location: $BOT_SCRIPT"
        return 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$VENV_PATH" ]]; then
        log WARN "Virtual environment not found: $VENV_PATH"
        log INFO "Attempting to create virtual environment..."
        if ! create_virtualenv; then
            log ERROR "Failed to create virtual environment"
            return 1
        fi
    fi
    
    # Check if Python is available
    if [[ ! -f "$PYTHON_BIN" ]]; then
        log ERROR "Python executable not found: $PYTHON_BIN"
        log INFO "Virtual environment may not be properly set up"
        return 1
    fi
    
    # Check Python version
    local python_version=$("$PYTHON_BIN" --version 2>&1 | awk '{print $2}')
    log INFO "Python version: $python_version"
    
    return 0
}

create_virtualenv() {
    log INFO "Creating virtual environment..."
    
    if ! python3 -m venv "$VENV_PATH" 2>&1 | tee -a "$LOG_FILE"; then
        log ERROR "Failed to create virtual environment"
        return 1
    fi
    
    log INFO "Installing dependencies..."
    if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
        if ! "$PYTHON_BIN" -m pip install --upgrade pip 2>&1 | grep -i "success\|already" >/dev/null; then
            log WARN "pip upgrade may have failed, continuing anyway..."
        fi
        
        if ! "$PYTHON_BIN" -m pip install -r "${PROJECT_ROOT}/requirements.txt" 2>&1 | tee -a "$LOG_FILE"; then
            log ERROR "Failed to install dependencies"
            return 1
        fi
    fi
    
    return 0
}

################################################################################
# Signal Handlers
################################################################################

handle_sigterm() {
    log INFO "SIGTERM received - initiating graceful shutdown..."
    SHUTDOWN_REQUESTED=true
    stop_bot
    exit 0
}

handle_sigint() {
    log INFO "SIGINT received - initiating graceful shutdown..."
    SHUTDOWN_REQUESTED=true
    stop_bot
    exit 130
}

handle_sighup() {
    log INFO "SIGHUP received - reloading configuration..."
    # Add configuration reload logic here if needed
}

setup_signal_handlers() {
    trap handle_sigterm SIGTERM
    trap handle_sigint SIGINT
    trap handle_sighup SIGHUP
}

################################################################################
# Process Management Functions
################################################################################

start_bot() {
    log INFO "Starting AurumBotX bot..."
    
    # Clean up stale PID file
    if [[ -f "$PID_FILE" ]]; then
        local old_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$old_pid" ]] && ! kill -0 "$old_pid" 2>/dev/null; then
            rm -f "$PID_FILE"
            log DEBUG "Cleaned up stale PID file"
        fi
    fi
    
    # Start the bot process
    if cd "$PROJECT_ROOT"; then
        # Run bot in background and capture PID
        "$PYTHON_BIN" "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
        local bot_pid=$!
        echo "$bot_pid" > "$PID_FILE"
        
        log INFO "Bot started with PID: $bot_pid"
        return 0
    else
        log ERROR "Failed to change directory to $PROJECT_ROOT"
        return 1
    fi
}

stop_bot() {
    if [[ ! -f "$PID_FILE" ]]; then
        log DEBUG "No PID file found"
        return 0
    fi
    
    local bot_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$bot_pid" ]]; then
        log DEBUG "PID file is empty"
        rm -f "$PID_FILE"
        return 0
    fi
    
    if ! kill -0 "$bot_pid" 2>/dev/null; then
        log INFO "Bot process is not running (PID: $bot_pid)"
        rm -f "$PID_FILE"
        return 0
    fi
    
    log INFO "Stopping bot process (PID: $bot_pid)..."
    
    # Try graceful termination first
    if kill -TERM "$bot_pid" 2>/dev/null; then
        # Wait up to 10 seconds for graceful shutdown
        local wait_count=0
        while [[ $wait_count -lt 10 ]]; do
            if ! kill -0 "$bot_pid" 2>/dev/null; then
                log INFO "Bot process terminated gracefully"
                rm -f "$PID_FILE"
                return 0
            fi
            sleep 1
            ((wait_count++))
        done
        
        # Force kill if still running
        log WARN "Graceful shutdown timeout, forcing termination..."
        if kill -KILL "$bot_pid" 2>/dev/null; then
            sleep 1
        fi
    fi
    
    rm -f "$PID_FILE"
    return 0
}

bot_is_running() {
    if [[ ! -f "$PID_FILE" ]]; then
        return 1
    fi
    
    local bot_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$bot_pid" ]]; then
        return 1
    fi
    
    kill -0 "$bot_pid" 2>/dev/null
    return $?
}

################################################################################
# Main Loop Functions
################################################################################

run_loop() {
    log INFO "Starting bot monitoring loop..."
    log INFO "Restart delay: ${RESTART_DELAY}s"
    
    if [[ $RESTART_MAX_ATTEMPTS -gt 0 ]]; then
        log INFO "Max restart attempts: $RESTART_MAX_ATTEMPTS"
    else
        log INFO "Unlimited restart attempts"
    fi
    
    while true; do
        if [[ "$SHUTDOWN_REQUESTED" == true ]]; then
            log INFO "Shutdown requested, exiting loop"
            break
        fi
        
        if bot_is_running; then
            log DEBUG "Bot is running"
            sleep 5
        else
            log WARN "Bot process is not running"
            
            # Check if we've exceeded max restart attempts
            if [[ $RESTART_MAX_ATTEMPTS -gt 0 ]] && [[ $RESTART_ATTEMPT -ge $RESTART_MAX_ATTEMPTS ]]; then
                log ERROR "Maximum restart attempts ($RESTART_MAX_ATTEMPTS) exceeded, stopping"
                return 1
            fi
            
            ((RESTART_ATTEMPT++))
            log WARN "Restart attempt: $RESTART_ATTEMPT"
            
            # Add exponential backoff (optional)
            local backoff_delay=$RESTART_DELAY
            log INFO "Waiting ${backoff_delay}s before restart..."
            sleep "$backoff_delay"
            
            if ! start_bot; then
                log ERROR "Failed to start bot"
                sleep "$RESTART_DELAY"
            else
                RESTART_ATTEMPT=0
            fi
        fi
    done
}

################################################################################
# Help and Usage
################################################################################

show_help() {
    cat << EOF
AurumBotX Bot Loop Runner

USAGE:
    bash scripts/run_bot_loop.sh [OPTIONS]
    ./scripts/run_bot_loop.sh [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    -l, --log-level LEVEL   Set logging level (DEBUG, INFO, WARN, ERROR)
                            Default: INFO
    -d, --restart-delay SEC Delay between restart attempts (seconds)
                            Default: 5
    -m, --max-attempts NUM  Maximum restart attempts (0 = unlimited)
                            Default: 0

ENVIRONMENT VARIABLES:
    LOG_LEVEL               Set logging level
    RESTART_DELAY           Set restart delay in seconds
    RESTART_MAX_ATTEMPTS    Set maximum restart attempts

EXAMPLES:
    # Run with default settings
    ./scripts/run_bot_loop.sh

    # Run with debug logging
    ./scripts/run_bot_loop.sh --log-level DEBUG

    # Run with custom restart delay
    ./scripts/run_bot_loop.sh --restart-delay 10

    # Run with max attempts
    ./scripts/run_bot_loop.sh --max-attempts 5

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            -l|--log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            -d|--restart-delay)
                RESTART_DELAY="$2"
                shift 2
                ;;
            -m|--max-attempts)
                RESTART_MAX_ATTEMPTS="$2"
                shift 2
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

################################################################################
# Main Entry Point
################################################################################

main() {
    parse_arguments "$@"
    
    # Setup signal handlers
    setup_signal_handlers
    
    # Initialize and validate environment
    if ! initialize; then
        log ERROR "Initialization failed"
        exit 1
    fi
    
    if ! validate_environment; then
        log ERROR "Environment validation failed"
        exit 1
    fi
    
    # Start the monitoring loop
    if run_loop; then
        log INFO "Bot loop completed successfully"
        exit 0
    else
        log ERROR "Bot loop encountered an error"
        exit 1
    fi
}

# Run main function
main "$@"
