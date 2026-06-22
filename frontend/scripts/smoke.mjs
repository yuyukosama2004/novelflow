import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const cwd = fileURLToPath(new URL('..', import.meta.url));
const viteBin = fileURLToPath(new URL('../node_modules/vite/bin/vite.js', import.meta.url));

const child = spawn(
  process.execPath,
  [viteBin, '--host', '127.0.0.1', '--port', '5173'],
  {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: false,
  },
);

let output = '';
child.stdout.on('data', (chunk) => {
  output += chunk.toString();
});
child.stderr.on('data', (chunk) => {
  output += chunk.toString();
});

try {
  let lastError = '';
  for (let index = 0; index < 40; index += 1) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    if (child.exitCode !== null) {
      console.error(output);
      process.exit(child.exitCode || 1);
    }
    try {
      const response = await fetch('http://127.0.0.1:5173');
      const text = await response.text();
      if (response.ok && text.includes('<div id="root"></div>')) {
        console.log('Vite smoke ok');
        process.exitCode = 0;
        break;
      }
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
    }
  }
  if (process.exitCode !== 0) {
    console.error(`Vite smoke failed: ${lastError}`);
    console.error(output);
    process.exitCode = 1;
  }
} finally {
  child.kill();
}
