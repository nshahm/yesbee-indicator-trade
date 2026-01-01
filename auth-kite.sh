#!/bin/bash

# Configuration file path
CONFIG_FILE="config/kite-config.yaml"

# Ensure config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found."
    exit 1
fi

# Get current values from config
CURRENT_KEY=$(grep "key:" $CONFIG_FILE | head -n 1 | awk '{print $2}')
CURRENT_SECRET=$(grep "secret:" $CONFIG_FILE | head -n 1 | awk '{print $2}')

echo "--------------------------------------------------"
echo "🔑 Kite API Authentication Update"
echo "--------------------------------------------------"

# Prompt for API Key
read -p "Enter API Key [$CURRENT_KEY]: " API_KEY
API_KEY=${API_KEY:-$CURRENT_KEY}

# Prompt for API Secret
read -p "Enter API Secret [$CURRENT_SECRET]: " API_SECRET
API_SECRET=${API_SECRET:-$CURRENT_SECRET}

# Prompt for Request Token
echo "Please login to Kite and paste the request_token from the redirect URL."
read -p "Enter Request Token: " REQUEST_TOKEN

if [ -z "$REQUEST_TOKEN" ]; then
    echo "❌ Error: Request Token is required."
    exit 1
fi

# Calculate Checksum
# Checksum is SHA256(api_key + request_token + api_secret)
CHECKSUM_INPUT="${API_KEY}${REQUEST_TOKEN}${API_SECRET}"
# Handle different openssl output formats by taking the last field
CHECKSUM=$(echo -n "$CHECKSUM_INPUT" | openssl dgst -sha256 | awk '{print $NF}')

echo "⏳ Exchanging request token for access token..."

# Call Kite API
RESPONSE=$(curl -s -X POST https://api.kite.trade/session/token \
  -d "api_key=$API_KEY" \
  -d "request_token=$REQUEST_TOKEN" \
  -d "checksum=$CHECKSUM")

# Check if successful
STATUS=$(echo $RESPONSE | jq -r '.status' 2>/dev/null)

if [ "$STATUS" == "success" ]; then
    ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.data.access_token')
    USER_ID=$(echo $RESPONSE | jq -r '.data.user_id')
    
    echo "✅ Successfully obtained access token for user: $USER_ID"
    
    # Update config file
    # We use temporary file to avoid issues with sed -i variations across platforms if possible, 
    # but since we are on macOS, sed -i '' is fine.
    # To be safer and more portable, we'll write to a temp file.
    TEMP_FILE=$(mktemp)
    
    sed -e "s/^[[:space:]]*access_token:.*/    access_token: $ACCESS_TOKEN/" \
        -e "s/^[[:space:]]*key:.*/    key: $API_KEY/" \
        -e "s/^[[:space:]]*secret:.*/    secret: $API_SECRET/" \
        -e "s/^[[:space:]]*user_id:.*/    user_id: $USER_ID/" \
        "$CONFIG_FILE" > "$TEMP_FILE"
    
    mv "$TEMP_FILE" "$CONFIG_FILE"
    
    echo "--------------------------------------------------"
    echo "🚀 Updated $CONFIG_FILE with new credentials."
    echo "--------------------------------------------------"
else
    ERROR_MESSAGE=$(echo $RESPONSE | jq -r '.message' 2>/dev/null)
    [ -z "$ERROR_MESSAGE" ] && ERROR_MESSAGE="Unknown error"
    echo "❌ Failed to obtain access token: $ERROR_MESSAGE"
    echo "Response: $RESPONSE"
    exit 1
fi
