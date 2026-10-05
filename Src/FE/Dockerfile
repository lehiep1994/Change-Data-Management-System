FROM node:24-alpine

WORKDIR /app

# Copy file cấu hình và cài đặt thư viện Node.js
COPY package*.json ./
RUN npm install

# Copy toàn bộ mã nguồn Frontend vào container
COPY . .

EXPOSE 3000

CMD ["node", "server.js"]