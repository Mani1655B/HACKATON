# Docker Build Process Guide

## 📦 Dockerization Process

Your fraud detection backend is now containerized! Here's what was created:

---

## 🔧 Files Created

### 1. **Dockerfile** (Multi-stage build)
- **Stage 1 (builder)**: Installs all dependencies (including heavy ML models)
- **Stage 2 (final)**: Lean runtime image with only necessary files
- **Result**: ~1.5GB image (vs 3GB+ single-stage)

### 2. **docker-compose.yml**
- Orchestrates container startup
- Mounts database and logs
- Auto-restart on failure
- Health checks enabled

### 3. **.gitignore** (already created)
- Prevents committing large model files
- Excludes container data

---

## ⚙️ Build & Run Process

### **Step 1: Build Image**
```bash
docker build -t fraud-detector:latest .
```
Expected output:
```
[+] Building 120.5s (11/11) FINISHED
=> fraud-detector:latest
```

Time: **2-5 minutes** (first time, downloads models)

---

### **Step 2a: Run with Docker (Simple)**
```bash
docker run -p 8000:8000 fraud-detector:latest
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### **Step 2b: Run with Docker Compose (Recommended)**
```bash
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f fraud-detector-api
```

Stop:
```bash
docker-compose down
```

---

## 🧪 Test the Container

### Once running, test API:

```bash
# Health check
curl http://localhost:8000/

# Analyze message
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"message": "बधाई हो! आपने लॉटरी जीती है। फीस भेजें।"}'

# Get logs
curl http://localhost:8000/api/logs?limit=10

# Get stats
curl http://localhost:8000/api/stats
```

---

## 📊 Image Details

| Aspect | Value |
|--------|-------|
| **Base Image** | python:3.11-slim |
| **Size** | ~1.5 GB |
| **Build Time** | 2-5 min (first), <1 min (cached) |
| **Runtime** | Uvicorn on port 8000 |
| **Health Check** | Every 30s |
| **Auto-restart** | Yes (unless-stopped) |

---

## 🚀 Advanced Options

### Build with custom name/tag:
```bash
docker build -t mycompany/fraud-detector:v1.0 .
```

### Run with GPU support (if available):
```bash
docker run --gpus all -p 8000:8000 fraud-detector:latest
```

### Run in production mode (detached):
```bash
docker-compose up -d --scale fraud-detector-api=3
```

---

## 📁 Volume Mounts

The `docker-compose.yml` mounts:
- `fraud_detection.db` - SQLite database (persistent)
- `fraud_detection.log` - Detector logs (persistent)
- `api.log` - API logs (persistent)

Data survives container restart! ✅

---

## ✅ Verification Checklist

After running:
- [ ] Container is running: `docker ps`
- [ ] API responds: `curl http://localhost:8000/`
- [ ] Database created: `ls -la fraud_detection.db`
- [ ] Logs visible: `docker-compose logs`
- [ ] Models loaded: Check logs for "[OK]"

---

## 🔧 Troubleshooting

### Port 8000 already in use:
```bash
docker-compose.yml - Change ports: ["8001:8000"]
```

### Out of disk space:
```bash
docker system prune -a  # Remove unused images
docker rmi fraud-detector:latest  # Remove specific image
```

### Logs not showing:
```bash
docker-compose logs --follow fraud-detector-api
```

### Container won't start:
```bash
docker run -it fraud-detector:latest /bin/bash
```

---

## 📦 Push to Registry (Optional)

### Docker Hub:
```bash
docker tag fraud-detector:latest yourusername/fraud-detector:latest
docker push yourusername/fraud-detector:latest
```

### Local Registry:
```bash
docker tag fraud-detector:latest localhost:5000/fraud-detector:latest
docker push localhost:5000/fraud-detector:latest
```

---

## 🎯 Next Steps

1. **Build**: `docker build -t fraud-detector:latest .`
2. **Run**: `docker-compose up -d`
3. **Test**: `curl http://localhost:8000/`
4. **Deploy**: Push to Docker Hub / AWS ECR / Azure ACR

Your backend is now **production-ready for containerized deployment!** 🚀
