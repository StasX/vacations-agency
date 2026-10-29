import assert from 'node:assert/strict';
import { createServer as createHttpServer, request } from 'node:http';
import { once } from 'node:events';
import { test } from 'node:test';
import { createServer as createViteServer } from 'vite';

test('API proxy preserves browser Host, Origin, auth headers, and cookies', { timeout: 15000 }, async () => {
    const backend = createHttpServer((req, res) => {
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Set-Cookie', 'csrftoken=proxy-test; HttpOnly; SameSite=Lax; Path=/');
        res.end(JSON.stringify({ path: req.url, host: req.headers.host,
            origin: req.headers.origin, authorization: req.headers.authorization,
            csrf: req.headers['x-csrftoken'], cookie: req.headers.cookie }));
    });
    let vite;
    let frontend;
    const previousTarget = process.env.API_PROXY_TARGET;
    try {
        backend.listen(0, '127.0.0.1');
        await once(backend, 'listening');
        process.env.API_PROXY_TARGET = `http://127.0.0.1:${backend.address().port}`;
        vite = await createViteServer({ server: { middlewareMode: true, hmr: false }, appType: 'custom' });
        frontend = createHttpServer(vite.middlewares);
        frontend.listen(0, '127.0.0.1');
        await once(frontend, 'listening');
        const result = await new Promise((resolve, reject) => {
            const req = request({ hostname: '127.0.0.1', port: frontend.address().port,
                path: '/api/users/total', agent: false,
                headers: { Host: 'localhost:3000', Origin: 'http://localhost:3000',
                    Authorization: 'proxy-test-token', 'X-CSRFToken': 'proxy-test-csrf',
                    Cookie: 'csrftoken=proxy-test' } }, res => {
                let body = '';
                res.setEncoding('utf8');
                res.on('data', chunk => { body += chunk; });
                res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: JSON.parse(body) }));
            });
            req.on('error', reject);
            req.end();
        });
        assert.equal(result.status, 200);
        assert.deepEqual(result.body, { path: '/api/users/total', host: 'localhost:3000',
            origin: 'http://localhost:3000', authorization: 'proxy-test-token',
            csrf: 'proxy-test-csrf', cookie: 'csrftoken=proxy-test' });
        assert.deepEqual(result.headers['set-cookie'], ['csrftoken=proxy-test; HttpOnly; SameSite=Lax; Path=/']);
    } finally {
        if (previousTarget === undefined) delete process.env.API_PROXY_TARGET;
        else process.env.API_PROXY_TARGET = previousTarget;
        if (frontend) await new Promise(resolve => frontend.close(resolve));
        if (vite) await vite.close();
        await new Promise(resolve => backend.close(resolve));
    }
});
