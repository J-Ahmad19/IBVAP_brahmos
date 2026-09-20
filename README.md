# IBVAP - Intelligent Border Video Analytics Platform

## Developer Environment (Phase 1A)

Welcome to the IBVAP developer environment. This repository provides a reproducible, CPU-first, local setup for developing and testing the IBVAP platform.

### Prerequisites

You must have the following installed on your host machine:
- Python 3.11
- Node.js LTS & npm
- Docker
- Docker Compose
- Git

*Note: This prototype is strictly CPU-first. Do not install or configure GPU-only infrastructure (DeepStream, TensorRT, etc.) for this environment.*

### Initial Setup

1. **Clone the repository and prepare the environment:**
   ```bash
   cp .env.example .env
   ```

2. **Available Makefile Commands:**
   The `Makefile` abstracts common development tasks:

   - `make up`: Start the full Docker Compose stack in the background.
   - `make down`: Stop the stack and remove volumes.
   - `make logs`: View logs for all running services.
   - `make test`: Run automated tests across the API and Inference Worker.
   - `make lint`: Run linters for the backend and frontend.
   - `make seed`: Seed the database and watchlists with sample data.
   - `make migrate`: Run database migrations via Alembic.
   - `make reset`: Completely wipe containers and volumes, then restart the stack.

### Getting Started

To spin up the local development environment:
```bash
make up
```

Once running, the React dashboard will be accessible locally, and the FastAPI documentation will be available at the API endpoint.

---
*For detailed architecture documentation, please see `docs/architecture.md` and the other architecture markdown files in this repository.*
