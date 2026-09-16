FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
ENV NEXT_PUBLIC_BASE_PATH=/eidolon
RUN npm run build
EXPOSE 80
CMD ["npx", "serve", "-s", "out"]