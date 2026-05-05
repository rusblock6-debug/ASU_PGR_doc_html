const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const DATA_FILE = path.join(__dirname, 'data.json');
const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');

if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css',
    '.js': 'application/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml'
};

function readData() {
    try {
        return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    } catch (e) {
        return { title: "Документация", cards: { descriptive: [], instructions: [], about: [] } };
    }
}

function writeData(data) {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
}

function parseBody(req) {
    return new Promise((resolve, reject) => {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            try { resolve(JSON.parse(body)); } 
            catch (e) { resolve(body); }
        });
        req.on('error', reject);
    });
}

const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, `http://localhost:${PORT}`);
    
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    // API: Получить данные
    if (req.method === 'GET' && url.pathname === '/api/data') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(readData()));
        return;
    }

    // API: Сохранить данные
    if (req.method === 'POST' && url.pathname === '/api/data') {
        try {
            const data = await parseBody(req);
            writeData(data);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        } catch (err) {
            console.error('Ошибка сохранения:', err);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    // API: Сохранить справочники
    if (req.method === 'POST' && url.pathname === '/api/save-directory') {
        try {
            const data = await parseBody(req);
            const DIRECTORY_FILE = path.join(__dirname, 'directory_data.json');
            fs.writeFileSync(DIRECTORY_FILE, JSON.stringify(data, null, 4), 'utf8');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    // API: Сохранить изображение
    if (req.method === 'POST' && url.pathname === '/api/save-image') {
        try {
            const data = await parseBody(req);
            const { filename, folder, base64 } = data;
            const folderPath = path.join(SCREENSHOTS_DIR, folder || '');
            if (!fs.existsSync(folderPath)) fs.mkdirSync(folderPath, { recursive: true });
            const base64Data = base64.replace(/^data:image\/\w+;base64,/, '');
            fs.writeFileSync(path.join(folderPath, filename), base64Data, 'base64');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, path: `screenshots/${folder ? folder + '/' : ''}${filename}` }));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    // API: Удалить изображение
    if (req.method === 'POST' && url.pathname === '/api/delete-image') {
        try {
            const data = await parseBody(req);
            const imgPath = path.join(__dirname, data.path);
            if (fs.existsSync(imgPath)) {
                fs.unlinkSync(imgPath);
                // Удалить пустую папку
                const dir = path.dirname(imgPath);
                if (fs.existsSync(dir) && fs.readdirSync(dir).length === 0) {
                    fs.rmdirSync(dir);
                }
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    // API: Удалить папку карточки
    if (req.method === 'POST' && url.pathname === '/api/delete-folder') {
        try {
            const data = await parseBody(req);
            const folder = data.folder;
            
            if (folder) {
                const folderPath = path.join(SCREENSHOTS_DIR, folder);
                
                if (fs.existsSync(folderPath)) {
                    // Рекурсивное удаление папки со всем содержимым
                    function deleteFolderRecursive(dirPath) {
                        if (fs.existsSync(dirPath)) {
                            fs.readdirSync(dirPath).forEach(file => {
                                const filePath = path.join(dirPath, file);
                                if (fs.statSync(filePath).isDirectory()) {
                                    deleteFolderRecursive(filePath);
                                } else {
                                    fs.unlinkSync(filePath);
                                }
                            });
                            fs.rmdirSync(dirPath);
                        }
                    }
                    deleteFolderRecursive(folderPath);
                }
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        } catch (err) {
            console.error('Ошибка при удалении папки:', err);
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: err.message }));
        }
        return;
    }

    // Статика
    let filePath = url.pathname === '/' ? path.join(__dirname, 'admin.html') : path.join(__dirname, url.pathname);
    
    // Редирект docs/screenshots/ -> screenshots/ для совместимости
    if (url.pathname.startsWith('/docs/screenshots/')) {
        filePath = path.join(__dirname, url.pathname.replace('/docs/screenshots/', '/screenshots/'));
    }
    
    if (!fs.existsSync(filePath)) {
        res.writeHead(404);
        res.end('Not found');
        return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    
    try {
        const content = fs.readFileSync(filePath);
        res.writeHead(200, { 
            'Content-Type': contentType,
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        });
        res.end(content);
    } catch (err) {
        res.writeHead(500);
        res.end('Server error');
    }
});

server.listen(PORT, () => {
    console.log(`
╔════════════════════════════════════════════════════════════╗
║   Цифровой двойник карьера - Документация                 ║
╠════════════════════════════════════════════════════════════╣
║   Просмотр:        http://localhost:${PORT}                   ║
║   Редактирование:  http://localhost:${PORT}/admin.html        ║
╚════════════════════════════════════════════════════════════╝
`);
});
