FROM node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY frontend/public ./public
COPY frontend/src ./src
COPY frontend/tailwind.config.js ./
RUN REACT_APP_API_URL=/api GENERATE_SOURCEMAP=false npm run build

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY core ./core
COPY db ./db
COPY packaging/macos/desktop.py .
COPY --from=frontend /frontend/build ./web
ENV MEDORA_DESKTOP=1
EXPOSE 8080
CMD ["uvicorn", "desktop:app", "--host", "0.0.0.0", "--port", "8080"]
