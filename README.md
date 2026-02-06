# Cargo Tracker

Monorepo containing a FastAPI backend and a Next.js frontend for cargo tracking.

## Structure
- `backend/`: FastAPI service with Playwright-based web scraping drivers
- `frontend/`: Next.js UI for tracking cargo shipments

---

## 🐳 Docker Deployment (Recommended)

Docker provides a consistent environment across Mac and Windows, eliminating Python/Playwright compatibility issues.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Docker Hub account (for pushing/pulling images)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd cargoo-tracker
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Docker Hub Deployment

#### Push Images to Docker Hub

1. **Build the images**
   ```bash
   docker-compose build
   ```

2. **Tag the images** (replace `YOUR_USERNAME` with your Docker Hub username)
   ```bash
   docker tag cargoo-tracker-backend YOUR_USERNAME/cargoo-tracker-backend:latest
   docker tag cargoo-tracker-frontend YOUR_USERNAME/cargoo-tracker-frontend:latest
   ```

3. **Login to Docker Hub**
   ```bash
   docker login
   ```

4. **Push to Docker Hub**
   ```bash
   docker push YOUR_USERNAME/cargoo-tracker-backend:latest
   docker push YOUR_USERNAME/cargoo-tracker-frontend:latest
   ```

#### Pull and Run on Another Machine (e.g., Windows)

1. **Update docker-compose.yml** to use your Docker Hub images:
   ```yaml
   services:
     backend:
       image: YOUR_USERNAME/cargoo-tracker-backend:latest
       # Remove the 'build' section
     
     frontend:
       image: YOUR_USERNAME/cargoo-tracker-frontend:latest
       # Remove the 'build' section
   ```

2. **Pull and run**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

### Docker Commands Reference

```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# View running containers
docker ps

# Access backend container shell
docker exec -it cargoo-tracker-backend bash

# Access frontend container shell
docker exec -it cargoo-tracker-frontend sh
```

---

## 💻 Local Development (Without Docker)

### Backend Setup

1. **Create and activate virtual environment**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Set up environment variables**
   ```bash
   # Create .env.local
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

3. **Run the development server**
   ```bash
   npm run dev
   ```

---

## 🔧 Troubleshooting

### Playwright Issues on Windows
If you encounter Playwright/Python compatibility issues on Windows, **use Docker** instead. The Docker setup includes all necessary browser dependencies and runs in a Linux environment.

### Port Already in Use
If ports 3000 or 8000 are already in use, modify the port mappings in `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Frontend on port 3001
  - "8001:8000"  # Backend on port 8001
```

### Environment Variables Not Loading
Make sure your `.env` file is in the project root directory and contains all required variables. Check `docker-compose logs` for any errors.

---

## 📝 Notes

- The backend uses `headless=False` for Playwright browsers but runs them on a virtual display (Xvfb) inside Docker
- Screenshots and debug files are saved to `/tmp/` inside the backend container (mounted as a volume)
- Health checks ensure services are ready before accepting traffic
