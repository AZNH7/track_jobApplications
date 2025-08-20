# 🚀 Job Application Tracker

A comprehensive, AI-powered job tracking system for the German job market with intelligent analysis. Works seamlessly on **Windows**, **macOS**, and **Linux**.

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
├── app/                    # 🎯 Main Application
│   ├── src/                # Core application code
│   ├── docker-compose.yml  # Docker deployment
│   ├── Dockerfile          # Application container
│   └── requirements.txt    # Python dependencies
│
├── shared/                 # 📁 Shared Resources
│   ├── data/               # Job data and databases
│   ├── logs/               # Application logs

│   └── postgres-init/      # Database initialization
│
├── docs/                   # 📚 Documentation (Future)
│
└── scripts/                # 🔧 Utility Scripts
```

To get started with the Job Tracker application, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-url.com/job-tracker.git
    cd job-tracker
    ```

2.  **Run the start script:**
    This will configure the environment and launch the application.
    ```bash
    ./start.sh
    ```

3.  **Access the application:**
    Open your web browser and go to `http://localhost:8501`.

### Manual Docker-Compose

If you prefer to run the application manually, you can use `docker-compose`:

```bash
docker-compose -f app/docker-compose.yml up --build
```

## 📋 Prerequisites

### Required (All Platforms)
- **Docker Desktop** ([Windows](https://docs.docker.com/desktop/windows/), [macOS](https://docs.docker.com/desktop/mac/), [Linux](https://docs.docker.com/engine/install/))
- **Git** ([Download](https://git-scm.com/downloads))
- **4GB+ RAM** (8GB+ recommended for AI features)

### Optional (For AI Features)
- **Ollama** ([Download](https://ollama.ai/)) - Runs on your host machine (not in Docker)
- **8GB+ RAM** - For running AI models on your local machine

## 🔧 Configuration

### 📄 Environment Setup
Copy `app/env.template` to `.env` and configure:

```bash
# Required: LinkedIn Authentication
LINKEDIN_LI_AT="your_linkedin_cookie_here"

# AI Features (Ollama runs on host machine)
OLLAMA_HOST="http://host.docker.internal:11434"
```

### 📁 Directory Structure
- **📊 Data**: `shared/data/` - Job data and exports
- **📝 Logs**: `shared/logs/` - Application logs  

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

- 💡 **Application Insights**: Personalized application strategies and tips
- ✅ **Quality Assessment**: Job quality scoring and positive indicators
- 🔒 **Privacy-First**: All AI processing happens locally on your host machine (Ollama)

### Core Functionality
- ✅ Multi-platform job scraping (Indeed, LinkedIn, Xing, etc.)
- ✅ German location filtering

- ✅ Duplicate detection
- ✅ FlareSolverr Cloudflare bypass
- ✅ PostgreSQL data storage

### Streamlit-Specific
- 📈 Interactive data visualizations
- 🎯 Real-time job filtering
- 📋 Comprehensive dashboard
- 🔍 Advanced search and analysis

## 🔍 Job Search Sources

The application supports multiple job search platforms with specialized scraping capabilities:

### Supported Platforms

| Platform | Base URL | Search URL | Special Features |
|----------|----------|------------|------------------|
| **LinkedIn** | `https://www.linkedin.com` | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?` | Remote job filtering, AI-powered analysis |
| **Indeed** | `https://de.indeed.com` | `https://de.indeed.com/jobs?` | Remote work filter, German market focus |
| **StepStone** | `https://www.stepstone.de` | `https://www.stepstone.de/jobs/` | Work-from-home filter, language detection |
| **Xing** | `https://www.xing.com` | `https://www.xing.com/jobs/search?` | German professional network |
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
When searching for "Backend Developer" jobs in "Berlin", the following URLs are generated:

| Platform | Example Search URL |
|----------|-------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Backend+Developer&location=Berlin&f_TPR=r604800&sortBy=DD&start=0` |
| **Indeed** | `https://de.indeed.com/jobs?q=Backend+Developer&l=Berlin&start=0&sort=date&fromage=3&radius=35` |
| **StepStone** | `https://www.stepstone.de/jobs/backend-developer?sort=2&action=sort_publish&location=Berlin` |
| **Xing** | `https://www.xing.com/jobs/search?keywords=Backend+Developer&page=1&location=Berlin` |
| **Stellenanzeigen** | `https://www.stellenanzeigen.de/suche/?fulltext=Backend+Developer&locationIds=12345` |
| **MeineStadt** | `https://jobs.meinestadt.de/jobs?was=Backend+Developer&seite=1&wo=Berlin` |
| **JobRapido** | `https://de.jobrapido.com/?q=Backend+Developer&p=1&l=Berlin` |

#### Remote Job Search
When searching for "Backend Developer" remote jobs:

| Platform | Example Remote Search URL |
|----------|---------------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Backend+Developer&location=Germany&f_TPR=r604800&sortBy=DD&start=0&f_WT=2&geoId=101282230&distance=25` |
| **Indeed** | `https://de.indeed.com/jobs?q=Backend+Developer&l=germany&start=0&sort=date&fromage=3&radius=35&sc=0kf%3Aattr%28DSQF7%29%3B` |
| **StepStone** | `https://www.stepstone.de/jobs/backend-developer?sort=2&action=sort_publish&location=germany&wfh=1&radius=30&action=facet_selected%3bworkFromHome%3b1` |
| **Stellenanzeigen** | `https://www.stellenanzeigen.de/suche/?fulltext=Backend+Developer&locationIds=X-HO-100` |

#### English-Only Search
When searching for "Backend Developer" jobs in English only:

| Platform | Example English-Only Search URL |
|----------|--------------------------------|
| **LinkedIn** | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=Backend+Developer&location=Essen&f_TPR=r604800&sortBy=DD&start=0` |
| **Indeed** | `https://de.indeed.com/jobs?q=Backend+Developer&l=Essen&start=0&sort=date&fromage=3&radius=35&lang=en` |
| **StepStone** | `https://www.stepstone.de/jobs/backend-developer?sort=2&action=sort_publish&fdl=en` |

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

### Available AI Models

The application supports various AI models through Ollama. You can configure your preferred model in the Streamlit settings or environment variables:

#### Recommended Models (Best Performance)
- **`llama3.2:latest`** - Latest Llama 3.2 model (default, best overall performance)
- **`llama3:8b`** - Llama 3 8B parameter model (faster, lower resource usage)
- **`qwen2.5:14b`** - Qwen 2.5 14B model (excellent for career analysis)
- **`gpt-oss:latest`** - Open source GPT model (good general performance)
- **`deepseek-r1:latest`** - DeepSeek R1 model (excellent reasoning capabilities)

#### Alternative Models
- **`mistral:7b`** - Mistral 7B model (good balance of speed and quality)
- **`codellama:7b`** - Code-focused model (excellent for technical job analysis)
- **`gemma:7b`** - Google's Gemma 7B model (efficient and reliable)
- **`phi:latest`** - Microsoft's Phi model (fast inference)

#### Model Selection
You can change the AI model in several ways:
1. **Streamlit Settings**: Go to Settings → LLM Configuration → Ollama Model
2. **Environment Variable**: Set `OLLAMA_MODEL=your_model_name` in `.env`
3. **Configuration File**: Edit `app/job_tracker_config.json`

#### Model Download Commands
```bash
# Download recommended models
ollama pull llama3.2:latest
ollama pull llama3:8b
ollama pull qwen2.5:14b
ollama pull gpt-oss:latest
ollama pull deepseek-r1:latest

# Download alternative models
ollama pull mistral:7b
ollama pull codellama:7b
ollama pull gemma:7b
ollama pull phi:latest
```

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

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Streamlit for the amazing web framework
- Docker for containerization
- Ollama for local AI capabilities (runs on host machine)