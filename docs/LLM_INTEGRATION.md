# Multi-LLM Integration Guide for H-1B Job Search MCP Server

This guide provides detailed instructions for integrating the H-1B Job Search MCP Server with various Large Language Model platforms.

## Table of Contents
- [Overview](#overview)
- [Platform Integration Guides](#platform-integration-guides)
  - [Claude Desktop](#claude-desktop)
  - [ChatGPT/OpenAI](#chatgptopenai)
  - [Google Gemini](#google-gemini)
  - [Cursor IDE](#cursor-ide)
  - [Interaction Poke](#interaction-poke)
- [Testing Your Integration](#testing-your-integration)
- [Troubleshooting](#troubleshooting)

## Overview

The H-1B Job Search MCP Server supports multiple transport protocols:
- **stdio**: For direct process communication (Claude Desktop, Cursor)
- **HTTP**: For API-based integration (ChatGPT, Gemini, Poke)

All platforms have access to the same set of tools:
- `load_h1b_data`: Download and load H-1B LCA disclosure data
- `search_h1b_jobs`: Search for H-1B sponsoring companies
- `get_company_stats`: Get detailed sponsorship statistics
- `get_top_sponsors`: List top H-1B sponsors by volume
- `export_results`: Export search results to CSV
- `get_available_data`: Check available data periods

## Platform Integration Guides

### Claude Desktop

Claude Desktop has native MCP support, making integration straightforward.

#### Setup Steps:

1. **Install the server dependencies:**
```bash
pip install fastmcp pandas requests openpyxl
```

2. **Configure Claude Desktop:**
Edit your Claude Desktop configuration file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add the server configuration:
```json
{
  "mcpServers": {
    "h1b-search": {
      "command": "python",
      "args": ["/path/to/mcp-server-template/src/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/mcp-server-template"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Verify integration:**
Type in Claude: "Can you load the H-1B data for 2024 Q4?"

### ChatGPT/OpenAI

ChatGPT integration requires running the server in HTTP mode and using function calling.

#### Setup Steps:

1. **Deploy the server:**

Option A - Local deployment:
```bash
# Install dependencies
pip install fastmcp pandas requests openpyxl

# Run the server
PORT=8000 python src/server.py
```

Option B - Cloud deployment (Render):
```bash
# Deploy using the provided render.yaml
# The server will be available at your Render URL
```

2. **Create Custom GPT or use API:**

For Custom GPT:
- Go to ChatGPT → Explore GPTs → Create
- Add the following action schema:

```yaml
openapi: 3.0.0
info:
  title: H-1B Job Search API
  version: 1.0.0
servers:
  - url: http://your-server-url:8000

paths:
  /tool/load_h1b_data:
    post:
      summary: Load H-1B LCA data
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                year:
                  type: integer
                  default: 2024
                quarter:
                  type: integer
                  default: 4
                force_download:
                  type: boolean
                  default: false
      responses:
        200:
          description: Data loaded successfully

  /tool/search_h1b_jobs:
    post:
      summary: Search H-1B jobs
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_role
              properties:
                job_role:
                  type: string
                city:
                  type: string
                state:
                  type: string
                min_wage:
                  type: number
                max_results:
                  type: integer
                  default: 50
                skip_agencies:
                  type: boolean
                  default: true
      responses:
        200:
          description: Search results

  /tool/get_company_stats:
    post:
      summary: Get company H-1B statistics
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - company_name
              properties:
                company_name:
                  type: string
      responses:
        200:
          description: Company statistics

  /tool/get_top_sponsors:
    post:
      summary: Get top H-1B sponsors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                limit:
                  type: integer
                  default: 20
                exclude_agencies:
                  type: boolean
                  default: true
      responses:
        200:
          description: Top sponsors list

  /tool/export_results:
    post:
      summary: Export search results to CSV
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - job_role
              properties:
                job_role:
                  type: string
                city:
                  type: string
                state:
                  type: string
                filename:
                  type: string
                  default: h1b_results.csv
                max_results:
                  type: integer
                  default: 1000
      responses:
        200:
          description: Export successful
```

For API usage:
```python
import openai

client = openai.OpenAI(api_key="your-api-key")

# Define the function schemas
functions = [
    {
        "name": "load_h1b_data",
        "description": "Load H-1B LCA disclosure data",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "default": 2024},
                "quarter": {"type": "integer", "default": 4},
                "force_download": {"type": "boolean", "default": False}
            }
        }
    },
    {
        "name": "search_h1b_jobs",
        "description": "Search for H-1B sponsoring companies",
        "parameters": {
            "type": "object",
            "properties": {
                "job_role": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "min_wage": {"type": "number"},
                "max_results": {"type": "integer", "default": 50}
            },
            "required": ["job_role"]
        }
    }
]

# Use in conversation
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Find software engineer jobs in California"}
    ],
    functions=functions,
    function_call="auto"
)
```

### Google Gemini

Gemini integration through Google AI Studio or Vertex AI.

#### Setup Steps:

1. **Deploy the server with public URL** (required for Gemini)

2. **Configure in Google AI Studio:**

```python
import google.generativeai as genai

genai.configure(api_key="your-api-key")

# Define function declarations
load_h1b_data = genai.FunctionDeclaration(
    name="load_h1b_data",
    description="Load H-1B LCA disclosure data",
    parameters={
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "quarter": {"type": "integer"},
            "force_download": {"type": "boolean"}
        }
    }
)

search_h1b_jobs = genai.FunctionDeclaration(
    name="search_h1b_jobs",
    description="Search for H-1B sponsoring companies",
    parameters={
        "type": "object",
        "properties": {
            "job_role": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
            "min_wage": {"type": "number"},
            "max_results": {"type": "integer"}
        },
        "required": ["job_role"]
    }
)

# Create model with functions
model = genai.GenerativeModel(
    model_name="gemini-pro",
    tools=[load_h1b_data, search_h1b_jobs]
)

# Use in conversation
chat = model.start_chat()
response = chat.send_message("Find data scientist jobs in New York")
```

3. **Configure API endpoint mapping:**
```python
import requests

def execute_tool(function_call):
    tool_name = function_call.name
    args = function_call.args
    
    response = requests.post(
        f"http://your-server-url:8000/tool/{tool_name}",
        json=args
    )
    return response.json()
```

### Cursor IDE

Cursor supports MCP through its extension system.

#### Setup Steps:

1. **Install the MCP extension in Cursor:**
   - Open Cursor
   - Go to Extensions (Cmd/Ctrl + Shift + X)
   - Search for "MCP" or "Model Context Protocol"
   - Install the extension

2. **Configure the extension:**
Create `.cursor/mcp-config.json` in your project:

```json
{
  "servers": {
    "h1b-search": {
      "command": "python",
      "args": ["src/server.py"],
      "cwd": "/path/to/mcp-server-template",
      "env": {
        "PYTHONPATH": "/path/to/mcp-server-template"
      },
      "transport": "stdio"
    }
  }
}
```

3. **Activate in Cursor:**
   - Open Command Palette (Cmd/Ctrl + Shift + P)
   - Run "MCP: Reload Servers"
   - The H-1B tools should now be available in Cursor AI

### Interaction Poke

Poke supports direct MCP protocol integration.

#### Setup Steps:

1. **Configure Poke settings:**
Open Poke and navigate to Settings → MCP Servers

2. **Add server configuration:**
```json
{
  "h1b-search": {
    "type": "http",
    "url": "http://your-server-url:8000",
    "auth": {
      "type": "none"
    },
    "tools": [
      "load_h1b_data",
      "search_h1b_jobs",
      "get_company_stats",
      "get_top_sponsors",
      "export_results",
      "get_available_data"
    ]
  }
}
```

3. **Test the connection:**
   - Go to Tools → MCP Tools
   - You should see all H-1B tools listed
   - Test with "Load H-1B data for 2024 Q4"

## Testing Your Integration

Use these test queries to verify your integration:

### Basic Data Loading
```
"Load the H-1B data for 2024 Q4"
Expected: Success message with record count
```

### Job Search
```
"Find software engineer positions in California with minimum wage of $100,000"
Expected: List of companies sponsoring software engineers in CA
```

### Company Analysis
```
"Get H-1B statistics for Google"
Expected: Detailed stats including job titles, wages, and locations
```

### Top Sponsors
```
"Show me the top 10 H-1B sponsors excluding staffing agencies"
Expected: List of top companies with application counts
```

### Data Export
```
"Export data scientist jobs in New York to a CSV file"
Expected: Success message with file path
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Server Not Responding
- **Check:** Is the server running? (`ps aux | grep server.py`)
- **Solution:** Restart the server with proper environment variables
- **For HTTP:** Ensure PORT is set: `PORT=8000 python src/server.py`

#### 2. Authentication Errors
- **Check:** API keys and tokens are correctly configured
- **Solution:** Verify credentials in platform-specific config files

#### 3. Data Loading Fails
- **Check:** Internet connection and disk space
- **Solution:** 
  - Ensure sufficient disk space (>2GB) in data_cache directory
  - Check firewall settings for flcdatacenter.com access
  - Try with `force_download=True` parameter

#### 4. Tools Not Available
- **Check:** Server logs for initialization errors
- **Solution:** 
  - Verify all Python dependencies are installed
  - Check PYTHONPATH includes the project directory
  - For stdio transport: Ensure proper command path in config

#### 5. Empty Results
- **Check:** Data is loaded before searching
- **Solution:** Always call `load_h1b_data` first in a new session

### Debug Mode

Enable verbose logging by setting environment variable:
```bash
export MCP_DEBUG=true
python src/server.py
```

### Platform-Specific Issues

**Claude Desktop:**
- Config file syntax errors: Validate JSON with `jq . claude_desktop_config.json`
- Permission issues: Ensure Python script is executable

**ChatGPT:**
- CORS errors: Configure server with proper CORS headers
- Rate limiting: Implement caching for frequent requests

**Gemini:**
- Function calling errors: Ensure parameter types match schema exactly
- Timeout issues: Increase timeout in API client configuration

**Cursor:**
- Extension not loading: Check Cursor version compatibility
- Path issues: Use absolute paths in configuration

**Poke:**
- Connection refused: Verify server URL and port
- Tool discovery fails: Manually specify tool list in config

## Support

For additional help:
- Check server logs in the console where server.py is running
- Review the main README.md for general usage
- File issues at: [GitHub Repository](https://github.com/your-repo/h1b-mcp-server)