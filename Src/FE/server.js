const express = require('express');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = 3000;

const PYTHON_BE_URL = process.env.PYTHON_BE_URL || 'http://localhost:8000';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

async function forwardToBackend(req, res, method, endpoint) {
    try {
        const url = `${PYTHON_BE_URL}${endpoint}`;
        const response = await axios({
            method: method,
            url: url,
            data: req.body
        });
        res.status(response.status).json(response.data);
    } catch (error) {
        console.error(`Lỗi gọi Backend (${url}):`, error.message);
        res.status(500).json({ status: 'error', message: 'Không thể kết nối đến Python Backend' });
    }
}

app.post('/api/auth/validate', (req, res) => forwardToBackend(req, res, 'POST', '/api/auth/validate'));
app.post('/api/tenant/datasource', (req, res) => forwardToBackend(req, res, 'POST', '/api/tenant/datasource'));
app.post('/api/tenant/schedule', (req, res) => forwardToBackend(req, res, 'POST', '/api/tenant/schedule'));
app.post('/api/worker/control', (req, res) => forwardToBackend(req, res, 'POST', '/api/worker/control'));

// Gateway định tuyến dữ liệu Sync
app.post('/api/sync/vietful', (req, res) => forwardToBackend(req, res, 'POST', '/api/sync/vietful'));
app.post('/api/sync/shopify', (req, res) => forwardToBackend(req, res, 'POST', '/api/sync/shopify'));

app.get('/api/worker/status', (req, res) => forwardToBackend(req, res, 'GET', '/api/worker/status'));
app.get('/api/worker/metrics', (req, res) => forwardToBackend(req, res, 'GET', '/api/worker/metrics'));

app.listen(PORT, () => {
    console.log(`[API Gateway] CDMS FrontEnd đang chạy tại http://localhost:${PORT}`);
    console.log(`[API Gateway] Đang trỏ Backend về địa chỉ: ${PYTHON_BE_URL}`);
});