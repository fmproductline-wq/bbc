const { exec, spawn } = require('child_process');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');

function installOllama(onLog) {
  return new Promise((resolve, reject) => {
    const platform = process.platform;

    if (platform === 'linux') {
      onLog('Running: curl -fsSL https://ollama.com/install.sh | sh');

      const proc = spawn('bash', ['-c', 'curl -fsSL https://ollama.com/install.sh | sh'], {
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      proc.stdout.on('data', d => onLog(d.toString().trim()));
      proc.stderr.on('data', d => onLog(d.toString().trim()));

      proc.on('close', code => {
        if (code === 0) {
          onLog('Ollama installed. Starting service…');
          exec('ollama serve &', () => {});
          setTimeout(() => resolve(), 2000);
        } else {
          reject(new Error(`Install script exited with code ${code}`));
        }
      });
    } else if (platform === 'win32') {
      // Download the Windows installer silently
      const tmpPath = path.join(os.tmpdir(), 'OllamaSetup.exe');
      onLog('Downloading Ollama for Windows…');

      const file = fs.createWriteStream(tmpPath);
      https.get('https://ollama.com/download/OllamaSetup.exe', res => {
        res.pipe(file);
        file.on('finish', () => {
          file.close();
          onLog('Running installer silently…');
          const proc = spawn(tmpPath, ['/S'], { stdio: 'ignore', detached: true });
          proc.unref();
          proc.on('close', code => {
            if (code === 0 || code === null) {
              onLog('Installation complete. Starting Ollama…');
              setTimeout(() => {
                exec('ollama serve', () => {});
                resolve();
              }, 3000);
            } else {
              reject(new Error('Windows installer failed'));
            }
          });
        });
      }).on('error', reject);
    } else {
      reject(new Error('macOS: please download from https://ollama.com/download'));
    }
  });
}

module.exports = { installOllama };
