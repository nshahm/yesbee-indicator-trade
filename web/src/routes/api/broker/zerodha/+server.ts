import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import crypto from 'crypto';

const CONFIG_PATH = path.resolve('../config/kite-config.yaml');

function readConfig() {
  const fileContents = fs.readFileSync(CONFIG_PATH, 'utf8');
  return yaml.load(fileContents) as any;
}

function writeConfig(config: any) {
  const yamlStr = yaml.dump(config, { indent: 2 });
  fs.writeFileSync(CONFIG_PATH, yamlStr, 'utf8');
}

export const GET: RequestHandler = async () => {
  try {
    const config = readConfig();
    return json(config);
  } catch (error: any) {
    return json({ error: error.message }, { status: 500 });
  }
};

export const PATCH: RequestHandler = async ({ request }) => {
  try {
    const newConfig = await request.json();
    const config = readConfig();
    
    // Deep merge or replace top level keys
    // For simplicity and because we want to maintain the structure, 
    // we'll just merge the incoming object into the existing one
    const mergedConfig = { ...config, ...newConfig };
    
    writeConfig(mergedConfig);
    return json({ success: true });
  } catch (error: any) {
    return json({ error: error.message }, { status: 500 });
  }
};

export const POST: RequestHandler = async ({ request }) => {
  try {
    const { request_token } = await request.json();
    if (!request_token) {
      return json({ error: 'Request token is required' }, { status: 400 });
    }

    const config = readConfig();
    const apiKey = config.kite?.api?.key;
    const apiSecret = config.kite?.api?.secret;

    if (!apiKey || !apiSecret) {
      return json({ error: 'API Key and Secret must be configured first' }, { status: 400 });
    }

    // Checksum = SHA256(api_key + request_token + api_secret)
    const checksumInput = apiKey + request_token + apiSecret;
    const checksum = crypto.createHash('sha256').update(checksumInput).digest('hex');

    const response = await fetch('https://api.kite.trade/session/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        api_key: apiKey,
        request_token: request_token,
        checksum: checksum,
      }),
    });

    const result = await response.json();

    if (result.status === 'success') {
      const { access_token, user_id } = result.data;
      
      config.kite.api.access_token = access_token;
      config.kite.api.user_id = user_id;
      
      writeConfig(config);
      
      return json({ 
        success: true, 
        data: { 
          user_id, 
          access_token: access_token.substring(0, 4) + '...' // Only return partial for UI 
        } 
      });
    } else {
      return json({ error: result.message || 'Authentication failed' }, { status: 401 });
    }
  } catch (error: any) {
    return json({ error: error.message }, { status: 500 });
  }
};
