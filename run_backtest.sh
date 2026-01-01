#!/bin/bash

PYTHON="python3"

# Function to parse yaml (simple version using grep/awk)
parse_yaml() {
    local file=$1
    local key=$2
    grep -v "^[[:space:]]*#" "$file" | grep "$key:" | head -n 1 | awk -F': ' '{print $2}' | tr -d '"' | tr -d "'" | xargs
}

# Load configurations from YAML files
BACKTEST_YAML="config/backtest.yaml"
OPTIONS_YAML="config/options.yaml"

# Default values from YAML
# We'll pick the first enabled index from options.yaml or default to nifty50
SYMBOL="nifty50"
# Get date range from backtest.yaml
DATE_RANGE=$(parse_yaml "$BACKTEST_YAML" "date_range")
FROM_DATE=""
TO_DATE=""

if [ -n "$DATE_RANGE" ]; then
    FROM_DATE=$(echo "$DATE_RANGE" | cut -d'_' -f1)
    TO_DATE=$(echo "$DATE_RANGE" | cut -d'_' -f2)
fi

# Help message
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -s, --symbol <symbol>      Symbol to backtest (default from config)"
    echo "  -f, --from <date>          Start date YYYYMMDDHHMM"
    echo "  -t, --to <date>            End date YYYYMMDDHHMM"
    echo "  -h, --help                 Show this help message"
    exit 1
}

# Parse arguments (overrides)
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s|--symbol) SYMBOL="$2"; shift ;;
        -f|--from) FROM_DATE="$2"; shift ;;
        -t|--to) TO_DATE="$2"; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

echo "--------------------------------------------------"
echo "🚀 Starting Backtest Workflow"
echo "Symbol:   $SYMBOL"
echo "Range:    $FROM_DATE to $TO_DATE"
echo "--------------------------------------------------"

# Step 1: Run backtest (Python script handles multi-timeframe loading)
echo "Running candlestick pattern backtest..."

# Build backtest arguments
BACKTEST_ARGS=("--symbol" "$SYMBOL")
if [ -n "$FROM_DATE" ]; then
    # run_backtest.py expects YYYYMMDD for from-date/to-date
    BACKTEST_ARGS+=("--from-date" "${FROM_DATE:0:8}")
fi
if [ -n "$TO_DATE" ]; then
    BACKTEST_ARGS+=("--to-date" "${TO_DATE:0:8}")
fi

$PYTHON backtest/run_backtest.py "${BACKTEST_ARGS[@]}"

echo "--------------------------------------------------"
echo "✅ Backtest Workflow Completed"
echo "--------------------------------------------------"
