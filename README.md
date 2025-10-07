# H1B Job Search MCP Server

An MCP (Model Context Protocol) server that automates H-1B job searching using U.S. Department of Labor LCA disclosure data. Built with [FastMCP](https://github.com/jlowin/fastmcp).

🚀 **Live Server**: https://h1b-job-search-mcp.onrender.com/mcp

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/aryaminus/h1b-job-search-mcp)

## Features

- 📊 **Download LCA Data**: Automatically downloads and caches H-1B LCA disclosure data from the Department of Labor
- 🔍 **Smart Search**: Filter H-1B sponsoring companies by job role, location, and wage
- 🏢 **Company Analytics**: Get detailed sponsorship statistics for specific companies
- 📈 **Top Sponsors**: List top H-1B sponsoring companies by volume
- 🚫 **Agency Filtering**: Automatically filter out staffing agencies to find direct employers
- 📁 **Export Results**: Export filtered results to CSV for easy outreach
- 💾 **Data Caching**: Intelligent caching to avoid re-downloading large datasets
- 🤖 **Multi-LLM Support**: Works with Claude, ChatGPT, Gemini, Cursor, and Poke

## 📖 How to Use

For detailed usage examples and natural language prompts, see the **[Usage Guide](USAGE_GUIDE.md)**.

### Quick Examples
Just talk naturally! The `ask` tool understands plain English:
- "Load the latest H-1B data"
- "Find software engineer jobs in California paying over 150k"
- "Tell me about Google's H-1B sponsorships"
- "Export data scientist positions to CSV"

## Available MCP Tools

### 1. `load_h1b_data`
Download and load H-1B LCA data from the Department of Labor.
- **Parameters**:
  - `year`: Fiscal year (default: 2024)
  - `quarter`: Quarter 1-4 (default: 4)
  - `force_download`: Force re-download even if cached

### 2. `search_h1b_jobs`
Search for H-1B sponsoring companies by job role and location.
- **Parameters**:
  - `job_role`: Job title to search (e.g., "Software Engineer")
  - `city`: Work city (optional)
  - `state`: Work state code (optional, e.g., "CA")
  - `min_wage`: Minimum wage filter (optional)
  - `max_results`: Maximum results to return
  - `skip_agencies`: Skip staffing agencies (default: true)

### 3. `get_company_stats`
Get detailed H-1B sponsorship statistics for a specific company.
- **Parameters**:
  - `company_name`: Company name to analyze

### 4. `get_top_sponsors`
List top H-1B sponsoring companies by application volume.
- **Parameters**:
  - `limit`: Number of companies to return
  - `exclude_agencies`: Exclude staffing agencies

### 5. `export_results`
Export filtered H-1B results to a CSV file.
- **Parameters**:
  - `job_role`: Job title to filter
  - `city`: City filter (optional)
  - `state`: State filter (optional)
  - `filename`: Output filename
  - `max_results`: Maximum results to export

### 6. `get_available_data`
Check available LCA data periods and cached files.

### 7. `ask` (Natural Language Interface) 🎯
Talk to the H-1B search in simple English!
- **Usage**: Just describe what you want in plain language
- **Examples**:
  - "I'm a software engineer looking for jobs in the Bay Area"
  - "Show me data scientist positions paying over 180k"
  - "Which companies sponsor the most H-1B visas?"
  - "Tell me about Microsoft's H-1B program"

## Local Development

### Setup

```bash
git clone <your-repo-url>
cd mcp-server-template
conda create -n h1b-mcp python=3.13
conda activate h1b-mcp
pip install -r requirements.txt
```

### Test with MCP Inspector

```bash
# Terminal 1: Start the server
python src/server.py

# Terminal 2: Run the inspector
npx @modelcontextprotocol/inspector
```

Open http://localhost:3000 and connect to `http://localhost:8000/mcp` using "Streamable HTTP" transport.

### Example Usage Flow

1. **Load the data**:
   ```
   Tool: load_h1b_data
   Parameters: {"year": 2024, "quarter": 4}
   ```

2. **Search for jobs**:
   ```
   Tool: search_h1b_jobs
   Parameters: {
     "job_role": "Software Engineer",
     "state": "CA",
     "min_wage": 120000,
     "skip_agencies": true
   }
   ```

3. **Get company details**:
   ```
   Tool: get_company_stats
   Parameters: {"company_name": "Google"}
   ```

4. **Export results**:
   ```
   Tool: export_results
   Parameters: {
     "job_role": "Data Scientist",
     "state": "NY",
     "filename": "ny_data_scientists.csv"
   }
   ```

## Deployment

### Option 1: Deploy to Render
Click the "Deploy to Render" button above.

### Option 2: Manual Deployment
1. Fork this repository
2. Connect your GitHub account to Render
3. Create a new Web Service on Render
4. Connect your forked repository
5. Render will automatically detect the `render.yaml` configuration

Your server will be available at `https://your-service-name.onrender.com/mcp`

Current deployment: `https://h1b-job-search-mcp.onrender.com/mcp`

## Multi-LLM Support

This MCP server works with multiple LLM platforms. For detailed integration instructions, see [docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md).

### Quick Setup by Platform

#### Claude Desktop
```json
{
  "mcpServers": {
    "h1b-search": {
      "command": "python",
      "args": ["/path/to/src/server.py"]
    }
  }
}
```

#### ChatGPT/OpenAI
Run server with `PORT=8000 python src/server.py` and use the OpenAPI schema in [config/openai_config.json](config/openai_config.json).

#### Google Gemini
Configure with function declarations using [config/gemini_config.json](config/gemini_config.json).

#### Cursor IDE
Place [config/cursor_config.json](config/cursor_config.json) in `.cursor/mcp-config.json` and reload.

#### Interaction Poke
Use [config/poke_config.json](config/poke_config.json) in Poke settings.

See [docs/LLM_INTEGRATION.md](docs/LLM_INTEGRATION.md) for complete setup guides, testing procedures, and troubleshooting.

## Data Source

This tool uses publicly available LCA disclosure data from the U.S. Department of Labor's Foreign Labor Certification Data Center. The data includes:
- Employer information
- Job titles and wages
- Work locations
- Case status
- Contact information (when available)

**Note**: This data shows historical H-1B sponsorship patterns. Always verify current sponsorship policies with employers directly.

## Privacy & Legal

- All data used is publicly available from the U.S. Department of Labor
- No private or confidential information is accessed
- Use responsibly and professionally when contacting employers
- Respect company communication preferences

## Customization

Add custom filtering logic or additional tools by modifying `src/server.py`:

```python
@mcp.tool
def custom_analysis(parameter: str) -> dict:
    """Your custom H-1B data analysis."""
    # Your implementation here
    pass
```

## Troubleshooting

- **Data not loading**: Check your internet connection and verify the year/quarter exists
- **No results found**: Try broader search terms or check different quarters
- **Memory issues**: The full dataset can be large; consider using `nrows` parameter in pandas
- **Cache issues**: Delete the `data_cache` directory to force fresh downloads

## Contributing

Feel free to submit issues and pull requests to improve this tool!

## License

MIT