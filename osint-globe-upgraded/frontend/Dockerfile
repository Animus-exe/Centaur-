FROM node:20-alpine
WORKDIR /app
COPY package.json ./
COPY vite.config.js ./
COPY scripts ./scripts
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
