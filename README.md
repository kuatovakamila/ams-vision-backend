# AMS Backend - Access Management System

A scalable FastAPI backend for an Access Management System that serves a React frontend dashboard. The system is completely self-contained and runnable locally with Docker Compose.

## Features

- **FastAPI Framework**: Modern async/await Python web framework
- **PostgreSQL Database**: Reliable relational database with async support
- **Redis Caching**: Fast in-memory caching and session storage
- **JWT Authentication**: Secure token-based authentication
- **File Upload**: Local file storage with organized directory structure
- **Docker Compose**: Single-command deployment
- **Auto-generated API Documentation**: OpenAPI/Swagger docs
- **Russian Language Support**: Full Unicode support for Russian text
- **Role-based Access Control**: Admin, Operator, and Viewer roles

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ams-vision/backend
   ```

2. **Start the application**
   ```bash
   docker-compose up -d
   ```

3. **Wait for services to be healthy** (about 30-60 seconds)
   ```bash
   docker-compose ps
   ```

4. **Seed the database with sample data**
   ```bash
   docker-compose exec fastapi python seed_db.py
   ```

5. **Access the application**
   - API Documentation: http://localhost:8000/api/v1/docs
   - Health Check: http://localhost:8000/health
   - API Base: http://localhost:8000/api/v1

## Default Credentials

After seeding the database, you can use these accounts:

- **Admin**: admin@ams.local / admin123
- **Operator**: operator@ams.local / operator123  
- **Viewer**: viewer@ams.local / viewer123

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/register` - Register new user
- `GET /api/v1/auth/me` - Get current user profile
- `PUT /api/v1/auth/me` - Update current user profile

### Users (Admin only)
- `GET /api/v1/users` - List users with pagination & filtering
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{id}` - Get user details
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `PUT /api/v1/users/{id}/role` - Update user role

### Cameras
- `GET /api/v1/cameras` - List cameras with search & filtering
- `POST /api/v1/cameras` - Add new camera (Operator/Admin)
- `GET /api/v1/cameras/{id}` - Get camera details
- `PUT /api/v1/cameras/{id}` - Update camera (Operator/Admin)
- `DELETE /api/v1/cameras/{id}` - Delete camera (Operator/Admin)
- `PUT /api/v1/cameras/{id}/status` - Update camera status
- `GET /api/v1/cameras/count` - Get camera statistics

### Incidents
- `GET /api/v1/incidents` - List incidents with filtering
- `POST /api/v1/incidents` - Create incident (Operator/Admin)
- `GET /api/v1/incidents/{id}` - Get incident details
- `PUT /api/v1/incidents/{id}` - Update incident (Operator/Admin)
- `DELETE /api/v1/incidents/{id}` - Delete incident (Operator/Admin)
- `GET /api/v1/incidents/types` - Get incident types
- `GET /api/v1/incidents/export` - Export incidents data

### Files
- `GET /api/v1/files` - List files with pagination
- `POST /api/v1/files/upload` - Upload file to local storage
- `GET /api/v1/files/{id}` - Download file
- `DELETE /api/v1/files/{id}` - Delete file
- `GET /api/v1/files/{id}/metadata` - Get file metadata

### Dashboard
- `GET /api/v1/dashboard/stats` - Overall system statistics
- `GET /api/v1/dashboard/incidents/summary` - Incident summaries
- `GET /api/v1/dashboard/cameras/summary` - Camera status summary
- `GET /api/v1/dashboard/employees/summary` - Employee statistics

## Development

### Local Development Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start database and Redis**
   ```bash
   docker-compose up -d postgres redis
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Seed database**
   ```bash
   python seed_db.py
   ```

7. **Start development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

### Project Structure

```
backend/
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # FastAPI app container
├── requirements.txt            # Python dependencies
├── alembic.ini                # Alembic configuration
├── seed_db.py                 # Database seeding script
├── .env.example               # Environment variables template
├── app/
│   ├── main.py               # FastAPI application entry point
│   ├── api/                  # API route handlers
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── users.py         # User management endpoints
│   │   ├── cameras.py       # Camera management endpoints
│   │   ├── incidents.py     # Incident management endpoints
│   │   ├── files.py         # File management endpoints
│   │   └── dashboard.py     # Dashboard endpoints
│   ├── core/                # Core application logic
│   │   ├── config.py        # Application configuration
│   │   ├── security.py      # Authentication & security
│   │   ├── database.py      # Database connection
│   │   └── redis.py         # Redis connection
│   ├── models/              # SQLAlchemy database models
│   │   ├── user.py         # User model
│   │   ├── camera.py       # Camera model
│   │   ├── incident.py     # Incident model
│   │   └── file.py         # File model
│   └── schemas/             # Pydantic schemas for API
│       ├── user.py         # User schemas
│       ├── camera.py       # Camera schemas
│       ├── incident.py     # Incident schemas
│       ├── file.py         # File schemas
│       └── dashboard.py    # Dashboard schemas
├── alembic/                # Database migration files
└── uploads/                # Local file storage directory
```

## Configuration

Environment variables can be set in `.env` file:

```env
# Database
DATABASE_URL=postgresql://ams_user:ams_password@localhost:5432/ams_db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]

# File Upload
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"]
```

## Security Features

- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Password Hashing**: bcrypt for secure password storage
- **Role-based Access Control**: Three roles with different permissions
- **Input Validation**: Pydantic schemas for request/response validation
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configurable cross-origin resource sharing
- **File Upload Security**: File type and size validation

## Sample Data

The seeding script creates:

### Users
- Admin user with full system access
- Operator user with camera and incident management
- Viewer user with read-only access

### Cameras
- 10 sample cameras with Russian names
- Mix of active and inactive statuses
- Example IP addresses and stream URLs

### Incidents
- Sample security incidents
- Various types and priorities
- Linked to cameras and users

## Docker Services

- **fastapi**: Main application server (Port 8000)
- **postgres**: PostgreSQL database (Port 5432)
- **redis**: Redis cache (Port 6379)

All services include health checks and restart policies.

## Production Deployment

For production deployment:

1. **Update environment variables**
   - Change SECRET_KEY to a secure random string
   - Update database credentials
   - Set DEBUG=false
   - Configure CORS_ORIGINS for your domain

2. **Use production database**
   - External PostgreSQL instance
   - Database connection pooling
   - Regular backups

3. **Security considerations**
   - Use HTTPS/TLS
   - Implement rate limiting
   - Set up monitoring and logging
   - Regular security updates

4. **Scaling**
   - Multiple FastAPI instances behind load balancer
   - Separate Redis cluster
   - CDN for file serving

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

## Troubleshooting

### Common Issues

1. **Port conflicts**
   - Change ports in docker-compose.yml if 8000, 5432, or 6379 are in use

2. **Database connection errors**
   - Ensure PostgreSQL container is healthy
   - Check database credentials in .env

3. **Permission denied on uploads**
   - Ensure uploads directory has proper permissions
   - Check Docker volume mounts

4. **CORS errors**
   - Update CORS_ORIGINS in environment variables
   - Check frontend URL configuration

### Logs

View application logs:
```bash
docker-compose logs fastapi
docker-compose logs postgres
docker-compose logs redis
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
