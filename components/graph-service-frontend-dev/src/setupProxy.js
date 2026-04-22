const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND_URL = 'http://graph-service-backend:5000';

module.exports = function(app) {
  // Общий прокси для API и WebSocket
  const proxy = createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    ws: true,
    logLevel: 'debug',
    onError: (err, req, res) => {
      console.error('Proxy Error:', err.message);
    }
  });

  // Прокси для API запросов
  app.use('/api', proxy);
  
  // Прокси для WebSocket
  app.use('/ws', proxy);
};






