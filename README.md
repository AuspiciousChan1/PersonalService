# PersonalService

一个基于Django的服务器，使用PostgreSQL数据库。任何来源都可以通过一个外网地址访问这个服务器。

A Django-based server using PostgreSQL database that can be accessed from any external network address.

## Features

- Django 6.0 web framework
- PostgreSQL database
- Configurable via environment variables
- Docker Compose support for easy database setup
- External network access enabled

## Requirements

- Python 3.8+
- PostgreSQL 15+
- Docker and Docker Compose (optional, for running PostgreSQL)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/AuspiciousChan1/PersonalService.git
cd PersonalService
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file and modify as needed:

```bash
cp .env.example .env
```

Edit `.env` file with your database credentials and settings.

### 4. Start PostgreSQL database

#### Option A: Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

#### Option B: Using local PostgreSQL

Install PostgreSQL locally and create a database:

```sql
CREATE DATABASE personalservice;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE personalservice TO postgres;
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver 0.0.0.0:8000
```

The server will be accessible at `http://your-server-ip:8000` from any external network.

## Configuration

The following environment variables can be configured in the `.env` file:

- `SECRET_KEY`: Django secret key (keep it secret in production)
- `DEBUG`: Debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts (* allows all)
- `DB_ENGINE`: Database engine (default: django.db.backends.postgresql)
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port

## Production Deployment

For production deployment:

1. Set `DEBUG=False` in your `.env` file
2. Generate a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS` with your actual domain names
4. Use a production-ready web server like Gunicorn with Nginx
5. Enable HTTPS/SSL
6. Set up proper database backups

## License

MIT
