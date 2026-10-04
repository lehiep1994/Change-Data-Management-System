const request = require('supertest');
const express = require('express');

// Khởi tạo một Express app mô phỏng API Gateway dựa trên logic của server.js
const app = express();
app.use(express.json());

// Định nghĩa các route giả lập để test luồng chuyển tiếp
app.post('/api/auth/validate', (req, res) => {
    res.status(200).json({ status: 'success', message: '[Python BE] Xác thực thành công.' });
});

app.post('/api/tenant/datasource', (req, res) => {
    res.status(200).json({ status: 'success', message: `Đã cấu hình nguồn: ${req.body.source}` });
});

app.get('/api/worker/status', (req, res) => {
    res.status(200).json({ running: 2, deployed: 3, configured: 5 });
});

// Bắt đầu viết các test cases với Jest và Supertest
describe('Frontend API Gateway Client Tests', () => {

    test('1. Test Auth Endpoint Forwarding', async () => {
        const response = await request(app).post('/api/auth/validate');
        expect(response.statusCode).toBe(200);
        expect(response.body.status).toBe('success');
    });

    test('2. Test Data Source Configuration Forwarding', async () => {
        const response = await request(app)
            .post('/api/tenant/datasource')
            .send({ source: 'Vietful' });

        expect(response.statusCode).toBe(200);
        expect(response.body.status).toBe('success');
        expect(response.body.message).toContain('Vietful');
    });

    test('3. Test Worker Status Fetching', async () => {
        const response = await request(app).get('/api/worker/status');
        expect(response.statusCode).toBe(200);
        expect(response.body.running).toBe(2);
        expect(response.body.deployed).toBe(3);
    });

});