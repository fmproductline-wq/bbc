/**
 * Local Express server — acts as an OpenAI-compatible proxy to Ollama.
 * Ollama must be running locally (auto-started if installed).
 */
const express = require('express');
const cors = require('cors');
const http = require('http');
const { exec, spawn } = require('child_process');
const path = require('path');
const { app } = require('electron');

const OLLAMA_BASE = 'http://127.0.0.1:11434';

let ollamaProcess = null;

function getOllamaPath() {
  const platform = process.platform;
  if (platform === 'win32') return 'ollama.exe';
  if (platform === 'darwin') return '/usr/local/bin/ollama';
  return 'ollama'; // linux — expects it on PATH
}

async function ensureOllamaRunning() {
  return new Promise((resolve) => {
    const req = http.get(`${OLLAMA_BASE}/api/tags`, (res) => {
      resolve(true);
    });
    req.on('error', () => {
      // Try to start Ollama
      const ollamaPath = getOllamaPath();
      try {
        ollamaProcess = spawn(ollamaPath, ['serve'], {
          detached: true,
          stdio: 'ignore',
        });
        ollamaProcess.unref();
        setTimeout(() => resolve(false), 2000);
      } catch {
        resolve(false);
      }
    });
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

function proxyRequest(targetUrl, req, res) {
  const url = new URL(targetUrl);
  const options = {
    hostname: url.hostname,
    port: url.port || 80,
    path: url.pathname + (url.search || ''),
    method: req.method,
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    const headers = {
      'Content-Type': proxyRes.headers['content-type'] || 'application/json',
      'Access-Control-Allow-Origin': '*',
    };
    if (proxyRes.headers['transfer-encoding']) {
      headers['Transfer-Encoding'] = proxyRes.headers['transfer-encoding'];
    }
    res.writeHead(proxyRes.statusCode, headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (err) => {
    if (!res.headersSent) {
      res.status(502).json({ error: 'Ollama not reachable', detail: err.message });
    }
  });

  if (req.body) {
    const body = JSON.stringify(req.body);
    proxyReq.write(body);
  }
  proxyReq.end();
}

async function startLocalServer() {
  const expressApp = express();
  expressApp.use(cors());
  expressApp.use(express.json({ limit: '10mb' }));

  // Health check
  expressApp.get('/api/health', async (req, res) => {
    const running = await ensureOllamaRunning();
    res.json({ status: running ? 'ok' : 'ollama_starting', ollama: OLLAMA_BASE });
  });

  // List models
  expressApp.get('/api/models', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/tags`, req, res);
  });

  // Chat — streaming
  expressApp.post('/api/chat', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/chat`, req, res);
  });

  // Generate (single turn)
  expressApp.post('/api/generate', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/generate`, req, res);
  });

  // Pull a model
  expressApp.post('/api/pull', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/pull`, req, res);
  });

  // Delete a model
  expressApp.delete('/api/delete', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/delete`, req, res);
  });

  // Show model info
  expressApp.post('/api/show', (req, res) => {
    proxyRequest(`${OLLAMA_BASE}/api/show`, req, res);
  });

  return new Promise((resolve) => {
    const server = expressApp.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      console.log(`Local API server on port ${port}`);
      ensureOllamaRunning();
      resolve(port);
    });
  });
}

module.exports = { startLocalServer, ensureOllamaRunning };
