import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';

const OPTIONS_PATH = path.resolve('../config/options.yaml');

function readOptions() {
  const fileContents = fs.readFileSync(OPTIONS_PATH, 'utf8');
  return yaml.load(fileContents) as any;
}

function writeOptions(options: any) {
  const yamlStr = yaml.dump(options, { indent: 2 });
  fs.writeFileSync(OPTIONS_PATH, yamlStr, 'utf8');
}

export const GET: RequestHandler = async () => {
  try {
    const options = readOptions();
    return json(options);
  } catch (error: any) {
    return json({ error: error.message }, { status: 500 });
  }
};

export const PATCH: RequestHandler = async ({ request }) => {
  try {
    const newOptions = await request.json();
    const options = readOptions();
    
    const mergedOptions = { ...options, ...newOptions };
    
    writeOptions(mergedOptions);
    return json({ success: true });
  } catch (error: any) {
    return json({ error: error.message }, { status: 500 });
  }
};
