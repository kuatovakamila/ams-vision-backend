## Updated Prompt for Claude Sonnet 4

```
Create a scalable FastAPI backend for an Access Management System (AMS) that serves a React frontend dashboard. The system must be completely self-contained, runnable locally with Docker Compose, and require NO external API keys or third-party services.

## Core Requirements

### System Architecture
- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL (containerized)
- **Authentication**: JWT-based auth with refresh tokens (no external auth services)
- **Caching**: Redis (containerized)
- **File Storage**: Local file system storage with organized directory structure
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Health Checks**: Docker Compose health checks
- **Logging**: Structured JSON logging
- **Configuration**: Environment-based config with sensible defaults

### Docker Compose Setup Requirements
- Single `docker-compose.yml` file to run entire stack
- No external dependencies or API keys required
- Services: FastAPI app, PostgreSQL, Redis
- Volume mounts for persistent data and file storage
- Network configuration for service communication
- Development-friendly with hot reload

### API Endpoints Required

#### Authentication & Users
```
POST   /auth/login
POST   /auth/logout  
POST   /auth/refresh
POST   /auth/register
GET    /auth/me
PUT    /auth/me

GET    /users              # List users with pagination & filtering
POST   /users              # Create user
GET    /users/{id}         # Get user details
PUT    /users/{id}         # Update user
DELETE /users/{id}         # Delete user
PUT    /users/{id}/role    # Update user role
```

#### Dashboard Analytics
```
GET    /dashboard/stats    # Overall system statistics
GET    /dashboard/incidents/summary  # Incident summaries
GET    /dashboard/cameras/summary    # Camera status summary
GET    /dashboard/employees/summary  # Employee statistics
```

#### Camera Management (Based on CamerasClean.tsx)
```
GET    /cameras           # List cameras with search & filtering by name/location
POST   /cameras           # Add new camera
GET    /cameras/{id}      # Get camera details
PUT    /cameras/{id}      # Update camera
DELETE /cameras/{id}      # Delete camera
PUT    /cameras/{id}/status  # Update camera status (active/inactive)
GET    /cameras/count     # Get total and active camera counts
```

#### Incident Management
```
GET    /incidents         # List incidents with filtering
POST   /incidents         # Create incident
GET    /incidents/{id}    # Get incident details
PUT    /incidents/{id}    # Update incident
DELETE /incidents/{id}    # Delete incident
GET    /incidents/types   # Get incident types
GET    /incidents/export  # Export incidents data
```

#### File Management (Local Storage)
```
GET    /files             # List files with pagination
POST   /files/upload      # Upload file to local storage
GET    /files/{id}        # Download file
DELETE /files/{id}        # Delete file
GET    /files/{id}/metadata  # Get file metadata
```

### Data Models

#### Camera Model (Matching Frontend)
```python
class Camera(SQLAlchemyBase):
    id: int
    name: str           # "Камера 1", "Камера 2", etc.
    location: str       # "Локация 1", "Локация 2", etc.
    description: str    # Camera description
    status: str         # "active" or "inactive"
    ip_address: Optional[str]
    stream_url: Optional[str]
    created_at: datetime
    updated_at: datetime
```

#### User Model
```python
class User(SQLAlchemyBase):
    id: int
    email: str
    password_hash: str
    first_name: str
    last_name: str
    role: str  # "admin", "operator", "viewer"
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

#### Incident & File Models (similar structure)

### Docker Compose Requirements

#### Complete docker-compose.yml Structure
```yaml
version: '3.8'
services:
  fastapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/ams_db
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=your-secret-key-here
    volumes:
      - ./uploads:/app/uploads
      - ./app:/app/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=ams_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d ams_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### File Structure with Docker Support
```
backend/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── cameras.py
│   │   ├── incidents.py
│   │   ├── files.py
│   │   └── dashboard.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── database.py
│   │   └── redis.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── camera.py
│   │   ├── incident.py
│   │   └── file.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── camera.py
│   │   ├── incident.py
│   │   └── file.py
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py
│       ├── user_service.py
│       ├── camera_service.py
│       └── file_service.py
├── uploads/          # Local file storage
└── alembic/          # Database migrations
```

### Local Development Features
- Hot reload for development
- Database seeding with sample data (including Russian camera names/locations)
- Local file storage with proper directory structure
- No external API dependencies
- Simple environment configuration
- Development-friendly logging
- CORS configuration for frontend integration

### Security Features (No External Dependencies)
- Local JWT token generation and validation
- bcrypt password hashing
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention
- Rate limiting with Redis

### Sample Data for Development
Include database seeding with sample cameras matching the frontend:
```python
sample_cameras = [
    {"name": "Камера 1", "location": "Локация 1", "description": "Описание......", "status": "active"},
    {"name": "Камера 2", "location": "Локация 2", "description": "Описание......", "status": "active"},
    {"name": "Камера 3", "location": "Локация 3", "description": "Описание......", "status": "inactive"},
    # ... rest of cameras from frontend
]
```

### Required Files to Generate
1. Complete FastAPI application code
2. docker-compose.yml with health checks
3. Dockerfile with multi-stage build
4. requirements.txt with all dependencies
5. .env.example with default configurations
6. Database migration files
7. README.md with setup instructions
8. Sample data seeding script

### Success Criteria
- Single command setup: `docker-compose up -d`
- No API keys or external service configuration required
- Backend serves all endpoints needed by the React frontend
- Persistent data storage
- Development-friendly with hot reload
- Production-ready architecture that can be scaled later

Please provide complete, production-ready code with comprehensive error handling, Russian language support, and detailed setup documentation.
```

This updated prompt ensures the backend will be completely self-contained and easily runnable locally with Docker Compose, matching exactly what your frontend needs while requiring no external dependencies or API keys.This updated prompt ensures the backend will be completely self-contained and easily runnable locally with Docker Compose, matching exactly what your frontend needs while requiring no external dependencies or API keys.