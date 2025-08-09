# 🚀 Job Application Tracker

A comprehensive, AI-powered job tracking system for the German job market with intelligent analysis and CV matching. Works seamlessly on **Windows**, **macOS**, and **Linux**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![Cross-Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/)

## ✨ Key Features

🤖 **AI-Powered Analysis** - Local Ollama integration for intelligent job categorization  
📊 **Multi-Platform Scraping** - LinkedIn, Indeed, StepStone, Xing, and more  
🔍 **Advanced Filtering** - Remote work, location, skills, and salary filters  
📈 **Data Visualization** - Interactive charts and insights  
🔒 **Privacy-First** - All data processed locally, no external data sharing  
🌍 **Cross-Platform** - Works on Windows, macOS, and Linux

## 🏗️ Repository Structure

```
job-tracker/
├── streamlit-app/           # 🎯 Main Streamlit Application
│   ├── src/                 # Core application code
│   ├── docker-compose.yml  # Streamlit deployment
│   ├── Dockerfile          # Streamlit container
│   └── requirements.txt    # Python dependencies
│
├── web-app/                 # 🌐 Modern Web Interface
│   ├── flask-backend/       # Flask API backend
│   ├── django-backend/      # Django API backend (alternative)
│   ├── react-frontend/      # React.js frontend
│   ├── nginx/              # Nginx configuration
│   └── docker-compose.yml  # Web app deployment
│
├── shared/                  # 📁 Shared Resources
│   ├── data/               # Job data and databases
│   ├── logs/               # Application logs
│   ├── cv/                 # CV files for matching
│   ├── postgres-init/      # Database initialization
│   └── visualizations/     # Generated charts and graphs
│
├── docs/                    # 📚 Documentation
│   ├── README.md           # Main documentation
│   ├── CHANGELOG.md        # Version history
│   └── *.md               # Feature guides and setup docs
│
└── scripts/                 # 🔧 Utility Scripts
    ├── *.py                # Python utilities
    ├── *.sh                # Shell scripts
    └── debug/              # Debug and testing tools
```

## 🚀 Quick Start

### 🖥️ For Windows Users
```cmd
# Download and run the setup script
setup.bat
```

### 🐧 For Linux/macOS Users
```bash
# Make setup script executable and run
chmod +x setup.sh
./setup.sh
```

### 🐳 Manual Docker Setup (All Platforms)
```bash
# 1. Clone the repository
git clone <your-repo-url>
cd track_jobapplications

# 2. Create environment file
cp app/env.template .env
# Edit .env with your LinkedIn credentials

# 3. Start the application
cd app
docker-compose up -d --build

# 4. Access the application
# Open http://localhost:8501 in your browser
```

## 📋 Prerequisites

### Required (All Platforms)
- **Docker Desktop** ([Windows](https://docs.docker.com/desktop/windows/), [macOS](https://docs.docker.com/desktop/mac/), [Linux](https://docs.docker.com/engine/install/))
- **Git** ([Download](https://git-scm.com/downloads))
- **4GB+ RAM** (8GB+ recommended for AI features)

### Optional (For AI Features)
- **Ollama** ([Download](https://ollama.ai/)) - Runs on your host machine (not in Docker)
- **8GB+ RAM** - For running AI models on your local machine

## 🎯 Interface Comparison

| Feature | Streamlit App | Web App |
|---------|---------------|---------|
| **UI Style** | Data-focused dashboard | Modern web interface |
| **Setup** | Single command | Multi-service stack |
| **Performance** | Optimized for analysis | Scalable architecture |
| **APIs** | Built-in | RESTful APIs |
| **Database** | Direct PostgreSQL | API abstraction |
| **Best Use** | Personal use, analysis | Team use, integration |

## 🔧 Configuration

### 📄 Environment Setup
Copy `app/env.template` to `.env` and configure:

```bash
# Required: LinkedIn Authentication
LINKEDIN_LI_AT="your_linkedin_cookie_here"

# Database (Docker defaults work)
POSTGRES_HOST=postgres
POSTGRES_DB=jobtracker
POSTGRES_USER=jobtracker
POSTGRES_PASSWORD=secure_password_2024

# AI Features (Ollama runs on host machine)
OLLAMA_HOST=http://host.docker.internal:11434

# Other services
FLARESOLVERR_URL=http://flaresolverr-balancer:8190/v1
REDIS_HOST=redis
```

### 📁 Directory Structure
- **📊 Data**: `shared/data/` - Job data and exports
- **📝 Logs**: `shared/logs/` - Application logs  
- **📄 CVs**: `shared/cv/` - Your resume files
- **🗄️ Database**: PostgreSQL container storage
- **⚡ Cache**: Redis container storage

### 🔑 Getting LinkedIn Cookie
1. Login to LinkedIn in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage → Cookies → https://www.linkedin.com
4. Copy the `li_at` cookie value
5. Paste it in your `.env` file

### 🔧 Supported Job Platforms
- **LinkedIn** - Professional network with remote job filtering
- **Indeed** - Popular job board with German market focus  
- **StepStone** - German job platform with work-from-home filters
- **Xing** - German professional network
- **Monster** - International job board
- **Stellenanzeigen.de** - German job listings
- **MeineStadt.de** - Local German jobs
- **JobRapido** - Job aggregation platform

### 🚀 Performance Features
- **Multi-FlareSolverr Support** - Load balancing across multiple Cloudflare bypass instances
- **Redis Caching** - Fast data retrieval and reduced database load
- **Parallel Scraping** - Concurrent searches across multiple platforms
- **Smart Rate Limiting** - Avoids being blocked by job sites

## 📊 Features

### 🤖 AI-Powered Features (Ollama Integration)
- 🧠 **Intelligent Job Analysis**: Automatic job categorization and skill extraction
- 🎯 **Smart CV Scoring**: AI-driven job matching with detailed breakdown
- 💡 **Application Insights**: Personalized application strategies and tips
- 📝 **Cover Letter Guidance**: AI-generated key points to highlight
- 🎤 **Interview Preparation**: Focus areas and questions to ask
- ⚠️ **Red Flag Detection**: Identify potential concerns in job postings
- ✅ **Quality Assessment**: Job quality scoring and positive indicators
- 🔒 **Privacy-First**: All AI processing happens locally on your host machine (Ollama)

### Core Functionality (Both Interfaces)
- ✅ Multi-platform job scraping (Indeed, LinkedIn, Xing, etc.)
- ✅ German location filtering
- ✅ CV-based job matching
- ✅ Duplicate detection
- ✅ FlareSolverr Cloudflare bypass
- ✅ PostgreSQL data storage

### Streamlit-Specific
- 📈 Interactive data visualizations
- 🎯 Real-time job filtering
- 📋 Comprehensive dashboard
- 🔍 Advanced search and analysis

### Web App-Specific
- 🌐 RESTful API endpoints
- ⚛️ React.js modern frontend
- 🔄 Real-time updates
- 👥 Multi-user support
- 🔒 Authentication ready

## 🔍 Job Search Sources

The application supports multiple job search platforms with specialized scraping capabilities:

### Supported Platforms

| Platform | Base URL | Search URL | Special Features |
|----------|----------|------------|------------------|
| **LinkedIn** | `https://www.linkedin.com` | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?` | Remote job filtering, AI-powered analysis |
| **Indeed** | `https://de.indeed.com` | `https://de.indeed.com/jobs?` | Remote work filter, German market focus |
| **StepStone** | `https://www.stepstone.de` | `https://www.stepstone.de/jobs/` | Work-from-home filter, language detection |
| **Xing** | `https://www.xing.com` | `https://www.xing.com/jobs/search?` | German professional network |
| **Monster** | `https://www.monster.de` | `https://www.monster.de/jobs/search?` | International job board |
| **Stellenanzeigen** | `https://www.stellenanzeigen.de` | `https://www.stellenanzeigen.de/suche/?` | German job listings |
| **MeineStadt** | `https://jobs.meinestadt.de` | `https://jobs.meinestadt.de/jobs?` | Local job focus |
| **JobRapido** | `https://de.jobrapido.com` | `https://de.jobrapido.com/?` | Job aggregation platform |

### Key Features
- **Remote Job Support**: LinkedIn, Indeed, and StepStone have special handling for remote positions
- **Language Filtering**: Most platforms support English/German language filtering
- **Anti-bot Protection**: FlareSolverr integration for bypassing protection mechanisms
- **Rate Limiting**: Intelligent delays between requests to avoid being blocked
- **Parallel Processing**: Optimized for concurrent scraping across multiple platforms

### Search Parameters
Each platform uses specific parameters for job searches:
- **Keywords**: Job title, skills, or company names
- **Location**: Geographic location or "Remote" for remote positions
- **Pagination**: Page-based or offset-based navigation
- **Filters**: Date range, radius, language, work type (remote/onsite)

### Example Search URLs

#### Standard Search (Essen)
When searching for "IT system" jobs in "Essen", the following URLs are generated:

| Platform | Example Search URL |
|----------|-------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=IT+system&location=Essen&f_TPR=r604800&sortBy=DD&start=0` |
| **Indeed** | `https://de.indeed.com/jobs?q=IT+system&l=Essen&start=0&sort=date&fromage=3&radius=35` |
| **StepStone** | `https://www.stepstone.de/jobs/it-system?sort=2&action=sort_publish&location=Essen` |
| **Xing** | `https://www.xing.com/jobs/search?keywords=IT+system&page=1&location=Essen` |
| **Monster** | `https://www.monster.de/jobs/search?q=IT+system&where=Essen&page=1&lang=de` |
| **Stellenanzeigen** | `https://www.stellenanzeigen.de/suche/?fulltext=IT+system&locationIds=12345` |
| **MeineStadt** | `https://jobs.meinestadt.de/jobs?was=IT+system&seite=1&wo=Essen` |
| **JobRapido** | `https://de.jobrapido.com/?q=IT+system&p=1&l=Essen` |

#### Remote Job Search
When searching for "IT system" remote jobs:

| Platform | Example Remote Search URL |
|----------|---------------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=IT+system&location=Germany&f_TPR=r604800&sortBy=DD&start=0&f_WT=2&geoId=101282230&distance=25` |
| **Indeed** | `https://de.indeed.com/jobs?q=IT+system&l=germany&start=0&sort=date&fromage=3&radius=35&sc=0kf%3Aattr%28DSQF7%29%3B` |
| **StepStone** | `https://www.stepstone.de/jobs/it-system?sort=2&action=sort_publish&location=germany&wfh=1&radius=30&action=facet_selected%3bworkFromHome%3b1` |
| **Stellenanzeigen** | `https://www.stellenanzeigen.de/suche/?fulltext=IT+system&locationIds=X-HO-100` |

#### English-Only Search
When searching for "IT system" jobs in English only:

| Platform | Example English-Only Search URL |
|----------|--------------------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=IT+system&location=Essen&f_TPR=r604800&sortBy=DD&start=0` |
| **Indeed** | `https://de.indeed.com/jobs?q=IT+system&l=Essen&start=0&sort=date&fromage=3&radius=35&lang=en` |
| **StepStone** | `https://www.stepstone.de/jobs/it-system?sort=2&action=sort_publish&fdl=en` |

**Notes**: 
- **Stellenanzeigen** uses location IDs instead of text names
- **LinkedIn, Xing, Stellenanzeigen, MeineStadt, JobRapido** handle language filtering in post-processing
- **Remote jobs** on LinkedIn, Indeed, and StepStone use special filter parameters
- Some platforms include additional anti-bot protection parameters

## 🛠️ Common Commands

### Application Management
```bash
# Start application
docker-compose up -d

# Stop application  
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart job-tracker

# Update application
git pull
docker-compose up -d --build
```

### Troubleshooting
```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats

# Clean up (WARNING: removes all data)
docker-compose down -v
docker system prune -a
```

### Development Mode
```bash
# Edit source files in app/src/
# Restart container to see changes
docker-compose restart job-tracker

# Monitor logs for debugging
docker-compose logs -f job-tracker
```

## 📚 Documentation

- **AI Integration**: `docs/OLLAMA_INTEGRATION_GUIDE.md`
- **Setup Guides**: `docs/`
- **API Documentation**: `web-app/*/README.md`
- **Troubleshooting**: `docs/WEB_TEST_TROUBLESHOOTING.md`
- **Performance Tuning**: `docs/SPEED_OPTIMIZATION_GUIDE.md`

## 🤖 AI Setup (Optional)

The AI features use **Ollama running on your host machine** (not in Docker).

### Install Ollama on Your Host Machine
```bash
# Windows: Download from https://ollama.ai/
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# Download AI model (runs on your machine)
ollama pull llama3.2:latest

# Start Ollama service (keep running)
ollama serve
```

### AI Requirements (Host Machine)
- **RAM**: 8GB+ recommended for `llama3.2:latest`
- **Storage**: ~5GB for the AI model on your local machine
- **CPU**: Multi-core recommended for faster analysis
- **Internet**: Required for initial model download only

**Note**: Ollama runs on your host machine at `localhost:11434`, and the Docker containers connect to it via `host.docker.internal:11434`.

## 🛡️ Privacy & Security

- **🔒 Local Processing**: All data stays on your machine
- **🚫 No Data Sharing**: No personal information sent to external services
- **🔐 Secure Storage**: Credentials stored in local environment files only
- **⚠️ Responsible Scraping**: Respects website terms of service and rate limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes in `app/src/`
4. Test with Docker: `docker-compose up -d --build`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## ⚠️ Disclaimer

This tool is for personal use to track job applications. Users are responsible for:
- Complying with website terms of service
- Respecting rate limits and robots.txt files  
- Using scraped data in accordance with applicable laws
- Not violating any platform's terms of use

## 💬 Support

- 🐛 **Bug Reports**: Open an issue with detailed reproduction steps
- 💡 **Feature Requests**: Open an issue with your enhancement proposal
- 📖 **Documentation**: Check the `docs/` directory for detailed guides
- 🤔 **Questions**: Start a discussion in the repository

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Streamlit for the amazing web framework
- Docker for containerization
- Ollama for local AI capabilities (runs on host machine)
- All the open-source libraries that make this project possible 