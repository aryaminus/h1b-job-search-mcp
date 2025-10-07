#!/usr/bin/env python3
import os
import pandas as pd
import requests
from io import StringIO
from typing import List, Dict, Optional
from datetime import datetime
from fastmcp import FastMCP

mcp = FastMCP("H1B Job Search MCP Server")

DATA_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data_cache")
os.makedirs(DATA_CACHE_DIR, exist_ok=True)

class H1BDataManager:
    def __init__(self):
        self.df = None
        self.last_loaded = None
        self.current_file = None
        
    def get_data_url(self, year: int, quarter: int) -> str:
        """Generate URL for LCA data download"""
        return f"https://www.flcdatacenter.com/download/LCA_{year}Q{quarter}.xlsx"
    
    def load_data(self, year: int = 2024, quarter: int = 4, force_download: bool = False) -> bool:
        """Load LCA data from cache or download if needed"""
        cache_file = os.path.join(DATA_CACHE_DIR, f"LCA_{year}Q{quarter}.pkl")
        
        if not force_download and os.path.exists(cache_file):
            try:
                self.df = pd.read_pickle(cache_file)
                self.current_file = cache_file
                self.last_loaded = datetime.now()
                return True
            except Exception as e:
                print(f"Error loading cached data: {e}")
        
        try:
            url = self.get_data_url(year, quarter)
            print(f"Downloading LCA data for {year} Q{quarter}...")
            
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            excel_file = os.path.join(DATA_CACHE_DIR, f"LCA_{year}Q{quarter}.xlsx")
            with open(excel_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.df = pd.read_excel(excel_file, nrows=100000)
            
            self.df.to_pickle(cache_file)
            self.current_file = cache_file
            self.last_loaded = datetime.now()
            
            if os.path.exists(excel_file):
                os.remove(excel_file)
            
            return True
            
        except Exception as e:
            print(f"Error downloading/loading data: {e}")
            return False
    
    def is_loaded(self) -> bool:
        return self.df is not None

data_manager = H1BDataManager()

@mcp.tool(description="Download and load H-1B LCA disclosure data from the U.S. Department of Labor")
def load_h1b_data(year: int = 2024, quarter: int = 4, force_download: bool = False) -> Dict:
    """
    Load H-1B LCA data for analysis.
    
    Args:
        year: Fiscal year (default: 2024)
        quarter: Quarter 1-4 (default: 4)
        force_download: Force re-download even if cached (default: False)
    
    Returns:
        Status and statistics about the loaded data
    """
    success = data_manager.load_data(year, quarter, force_download)
    
    if success:
        return {
            "status": "success",
            "records_loaded": len(data_manager.df),
            "columns": list(data_manager.df.columns)[:20],
            "year": year,
            "quarter": quarter,
            "cache_file": data_manager.current_file
        }
    else:
        return {
            "status": "error",
            "message": "Failed to load data. Check year/quarter or try again."
        }

@mcp.tool(description="Search H-1B sponsoring companies by job role and location")
def search_h1b_jobs(
    job_role: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    min_wage: Optional[float] = None,
    max_results: int = 50,
    skip_agencies: bool = True
) -> Dict:
    """
    Search for H-1B sponsoring companies.
    
    Args:
        job_role: Job title to search for (partial match)
        city: Work city (optional)
        state: Work state code (optional)
        min_wage: Minimum wage filter (optional)
        max_results: Maximum results to return (default: 50)
        skip_agencies: Skip staffing agencies (default: True)
    
    Returns:
        List of matching employers with details
    """
    if not data_manager.is_loaded():
        return {"error": "Data not loaded. Please run load_h1b_data first."}
    
    df = data_manager.df.copy()
    
    job_columns = ['JOB_TITLE', 'SOC_TITLE', 'JOB_TITLE_CLEAN']
    job_col = None
    for col in job_columns:
        if col in df.columns:
            job_col = col
            break
    
    if job_col:
        df = df[df[job_col].str.contains(job_role, case=False, na=False)]
    
    if city and 'WORKSITE_CITY' in df.columns:
        df = df[df['WORKSITE_CITY'].str.contains(city, case=False, na=False)]
    elif city and 'EMPLOYER_CITY' in df.columns:
        df = df[df['EMPLOYER_CITY'].str.contains(city, case=False, na=False)]
    
    if state:
        if 'WORKSITE_STATE' in df.columns:
            df = df[df['WORKSITE_STATE'].str.upper() == state.upper()]
        elif 'EMPLOYER_STATE' in df.columns:
            df = df[df['EMPLOYER_STATE'].str.upper() == state.upper()]
    
    wage_col = None
    for col in ['WAGE_RATE_OF_PAY_FROM', 'PREVAILING_WAGE', 'WAGE_RATE_OF_PAY']:
        if col in df.columns:
            wage_col = col
            break
    
    if min_wage and wage_col:
        df[wage_col] = pd.to_numeric(df[wage_col], errors='coerce')
        df = df[df[wage_col] >= min_wage]
    
    if skip_agencies and 'EMPLOYER_NAME' in df.columns:
        agency_keywords = [
            'staffing', 'consulting', 'agency', 'infosys', 'tcs', 
            'wipro', 'cognizant', 'hcl', 'tech mahindra', 'accenture'
        ]
        mask = ~df['EMPLOYER_NAME'].str.contains('|'.join(agency_keywords), case=False, na=False)
        df = df[mask]
    
    status_col = 'CASE_STATUS' if 'CASE_STATUS' in df.columns else None
    if status_col:
        df = df[df[status_col] == 'CERTIFIED']
    
    employer_col = 'EMPLOYER_NAME' if 'EMPLOYER_NAME' in df.columns else 'EMPLOYER_BUSINESS_DBA'
    
    results = []
    for _, row in df.head(max_results).iterrows():
        result = {
            "employer": row.get(employer_col, "Unknown"),
            "job_title": row.get(job_col, "Unknown"),
            "city": row.get('WORKSITE_CITY', row.get('EMPLOYER_CITY', "Unknown")),
            "state": row.get('WORKSITE_STATE', row.get('EMPLOYER_STATE', "Unknown")),
        }
        
        if wage_col:
            result["wage"] = row.get(wage_col, "N/A")
        
        contact_fields = ['EMPLOYER_POC_EMAIL', 'CONTACT_EMAIL', 'EMPLOYER_PHONE']
        for field in contact_fields:
            if field in row and pd.notna(row[field]):
                result["contact"] = row[field]
                break
        
        results.append(result)
    
    return {
        "total_matches": len(df),
        "returned": len(results),
        "results": results
    }

@mcp.tool(description="Get statistics about H-1B sponsorships by company")
def get_company_stats(company_name: str) -> Dict:
    """
    Get detailed H-1B sponsorship statistics for a specific company.
    
    Args:
        company_name: Company name to search for
    
    Returns:
        Statistics including sponsorship count, job titles, wages
    """
    if not data_manager.is_loaded():
        return {"error": "Data not loaded. Please run load_h1b_data first."}
    
    df = data_manager.df.copy()
    
    employer_col = 'EMPLOYER_NAME' if 'EMPLOYER_NAME' in df.columns else 'EMPLOYER_BUSINESS_DBA'
    df = df[df[employer_col].str.contains(company_name, case=False, na=False)]
    
    if len(df) == 0:
        return {"message": f"No records found for {company_name}"}
    
    job_col = None
    for col in ['JOB_TITLE', 'SOC_TITLE', 'JOB_TITLE_CLEAN']:
        if col in df.columns:
            job_col = col
            break
    
    wage_col = None
    for col in ['WAGE_RATE_OF_PAY_FROM', 'PREVAILING_WAGE', 'WAGE_RATE_OF_PAY']:
        if col in df.columns:
            wage_col = col
            df[wage_col] = pd.to_numeric(df[wage_col], errors='coerce')
            break
    
    stats = {
        "company": df[employer_col].iloc[0],
        "total_applications": len(df),
        "certified": len(df[df.get('CASE_STATUS', '') == 'CERTIFIED']) if 'CASE_STATUS' in df.columns else "N/A",
    }
    
    if job_col:
        top_jobs = df[job_col].value_counts().head(10).to_dict()
        stats["top_job_titles"] = top_jobs
    
    if wage_col:
        stats["wage_stats"] = {
            "min": df[wage_col].min(),
            "max": df[wage_col].max(),
            "mean": df[wage_col].mean(),
            "median": df[wage_col].median()
        }
    
    if 'WORKSITE_STATE' in df.columns:
        top_states = df['WORKSITE_STATE'].value_counts().head(5).to_dict()
        stats["top_states"] = top_states
    
    return stats

@mcp.tool(description="Export filtered H-1B data to CSV file")
def export_results(
    job_role: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    filename: str = "h1b_results.csv",
    max_results: int = 1000
) -> Dict:
    """
    Export filtered H-1B results to a CSV file.
    
    Args:
        job_role: Job title to filter
        city: City filter (optional)
        state: State filter (optional)
        filename: Output filename (default: h1b_results.csv)
        max_results: Maximum results to export (default: 1000)
    
    Returns:
        File path and export statistics
    """
    if not data_manager.is_loaded():
        return {"error": "Data not loaded. Please run load_h1b_data first."}
    
    search_results = search_h1b_jobs(
        job_role=job_role,
        city=city,
        state=state,
        max_results=max_results,
        skip_agencies=True
    )
    
    if "error" in search_results:
        return search_results
    
    df_export = pd.DataFrame(search_results["results"])
    
    export_path = os.path.join(DATA_CACHE_DIR, filename)
    df_export.to_csv(export_path, index=False)
    
    return {
        "status": "success",
        "file_path": export_path,
        "records_exported": len(df_export),
        "total_matches": search_results["total_matches"]
    }

@mcp.tool(description="List top H-1B sponsoring companies by volume")
def get_top_sponsors(limit: int = 20, exclude_agencies: bool = True) -> Dict:
    """
    Get top H-1B sponsoring companies by application volume.
    
    Args:
        limit: Number of companies to return (default: 20)
        exclude_agencies: Exclude staffing agencies (default: True)
    
    Returns:
        List of top sponsoring companies with statistics
    """
    if not data_manager.is_loaded():
        return {"error": "Data not loaded. Please run load_h1b_data first."}
    
    df = data_manager.df.copy()
    
    employer_col = 'EMPLOYER_NAME' if 'EMPLOYER_NAME' in df.columns else 'EMPLOYER_BUSINESS_DBA'
    
    if exclude_agencies:
        agency_keywords = [
            'staffing', 'consulting', 'agency', 'infosys', 'tcs',
            'wipro', 'cognizant', 'hcl', 'tech mahindra', 'accenture'
        ]
        mask = ~df[employer_col].str.contains('|'.join(agency_keywords), case=False, na=False)
        df = df[mask]
    
    top_companies = df[employer_col].value_counts().head(limit)
    
    results = []
    for company, count in top_companies.items():
        company_df = df[df[employer_col] == company]
        
        wage_col = None
        for col in ['WAGE_RATE_OF_PAY_FROM', 'PREVAILING_WAGE', 'WAGE_RATE_OF_PAY']:
            if col in df.columns:
                wage_col = col
                company_df[wage_col] = pd.to_numeric(company_df[wage_col], errors='coerce')
                break
        
        result = {
            "company": company,
            "total_applications": count,
            "certified": len(company_df[company_df.get('CASE_STATUS', '') == 'CERTIFIED']) if 'CASE_STATUS' in company_df.columns else count,
        }
        
        if wage_col:
            result["avg_wage"] = company_df[wage_col].mean()
        
        if 'WORKSITE_STATE' in company_df.columns:
            result["primary_state"] = company_df['WORKSITE_STATE'].mode()[0] if len(company_df['WORKSITE_STATE'].mode()) > 0 else "N/A"
        
        results.append(result)
    
    return {
        "top_sponsors": results,
        "total_companies": df[employer_col].nunique()
    }

@mcp.tool(description="Talk to the H-1B search in simple words - I'll figure out what you want")
def ask(prompt: str) -> Dict:
    """Natural language interface for H-1B job search.
    
    Examples:
    - "Load the latest H-1B data"
    - "Find software engineer jobs in California"
    - "Show me data scientist positions paying over 150k"
    - "Tell me about Google's H-1B sponsorships"
    - "Who are the top H-1B sponsors?"
    - "Export software engineer jobs to a file"
    """
    import re
    
    text = prompt.strip().lower()
    original_prompt = prompt.strip()
    
    # Helper function to extract numbers
    def extract_number(pattern: str, text: str, default: Optional[int] = None) -> Optional[int]:
        match = re.search(pattern, text)
        if match:
            # Remove commas and $ signs, convert to int
            num_str = match.group(1).replace(',', '').replace('$', '').replace('k', '000')
            try:
                return int(float(num_str))
            except:
                pass
        return default
    
    # Helper to extract year and quarter
    def extract_year_quarter(text: str) -> tuple:
        year = extract_number(r'\b(20\d{2})\b', text, 2024) or 2024
        quarter_val = extract_number(r'\bq(\d)\b', text)
        if quarter_val is None:
            quarter_val = extract_number(r'quarter\s+(\d)', text)
        quarter = quarter_val or 4
        return year, quarter
    
    # 1. LOAD DATA
    if any(word in text for word in ['load', 'download', 'get', 'fetch']) and \
       any(word in text for word in ['data', 'h-1b', 'h1b', 'lca', 'records']):
        year, quarter = extract_year_quarter(text)
        force = 'fresh' in text or 'force' in text or 'new' in text
        result = load_h1b_data(year=year, quarter=quarter, force_download=force)
        return {
            "action": "load_h1b_data",
            "message": f"Loading H-1B data for {year} Q{quarter}...",
            "result": result,
            "suggestions": [
                "Find software engineer jobs",
                "Show me top H-1B sponsors",
                "Search for data scientist positions in California"
            ]
        }
    
    # 2. SEARCH JOBS
    if any(word in text for word in ['find', 'search', 'show', 'look', 'want', 'need']) and \
       any(word in text for word in ['job', 'position', 'role', 'opportunity', 'engineer', 'developer', 
                                      'scientist', 'analyst', 'manager', 'designer', 'architect']):
        
        # Extract job role - common patterns
        job_patterns = [
            (r'software\s+engineer', 'Software Engineer'),
            (r'data\s+scientist', 'Data Scientist'),
            (r'data\s+engineer', 'Data Engineer'),
            (r'data\s+analyst', 'Data Analyst'),
            (r'product\s+manager', 'Product Manager'),
            (r'ml\s+engineer|machine\s+learning\s+engineer', 'Machine Learning Engineer'),
            (r'devops|dev\s+ops', 'DevOps Engineer'),
            (r'backend\s+engineer', 'Backend Engineer'),
            (r'frontend\s+engineer', 'Frontend Engineer'),
            (r'fullstack|full\s+stack', 'Full Stack Developer'),
            (r'ios\s+developer', 'iOS Developer'),
            (r'android\s+developer', 'Android Developer'),
            (r'qa\s+engineer|test\s+engineer', 'QA Engineer'),
            (r'business\s+analyst', 'Business Analyst'),
            (r'project\s+manager', 'Project Manager'),
            (r'ux\s+designer|ui\s+designer', 'UX Designer'),
            (r'cloud\s+engineer', 'Cloud Engineer'),
            (r'security\s+engineer', 'Security Engineer'),
            (r'database\s+admin|dba', 'Database Administrator'),
            (r'network\s+engineer', 'Network Engineer'),
            (r'python\s+developer', 'Python Developer'),
            (r'java\s+developer', 'Java Developer'),
            (r'javascript\s+developer|js\s+developer', 'JavaScript Developer'),
            (r'programmer|developer|engineer', 'Software Engineer'),  # Generic fallback
        ]
        
        job_role = None
        for pattern, title in job_patterns:
            if re.search(pattern, text):
                job_role = title
                break
        
        if not job_role:
            # Try to extract any word before "jobs", "positions", "roles"
            match = re.search(r'(\w+(?:\s+\w+)?)\s+(?:jobs?|positions?|roles?)', text)
            if match:
                job_role = match.group(1).title()
            else:
                job_role = "Software Engineer"  # Default
        
        # Extract location - city and/or state
        city = None
        state = None
        
        # Common city patterns
        city_patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,?\s*([A-Z]{2})',  # City, State
            r'(?:in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # City name
        ]
        
        # Check for city, state pattern first
        match = re.search(r'in\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*,?\s*([A-Z]{2})', original_prompt)
        if match:
            city = match.group(1)
            state = match.group(2)
        else:
            # State codes
            state_match = re.search(r'\b([A-Z]{2})\b', original_prompt)
            if state_match:
                state = state_match.group(1)
            
            # City names
            cities = ['San Francisco', 'New York', 'Los Angeles', 'Seattle', 'Austin', 
                     'Boston', 'Chicago', 'Denver', 'Atlanta', 'Dallas', 'Houston',
                     'San Jose', 'Mountain View', 'Cupertino', 'Redmond', 'Bellevue']
            for c in cities:
                if c.lower() in text:
                    city = c
                    break
        
        # Extract salary
        min_wage = None
        salary_patterns = [
            r'(?:over|above|minimum|at\s+least|paying)\s+\$?(\d+)k',
            r'(?:over|above|minimum|at\s+least|paying)\s+\$?(\d{3,})',
            r'\$(\d+)k',
            r'\$(\d{3,})',
        ]
        for pattern in salary_patterns:
            match = re.search(pattern, text)
            if match:
                num_str = match.group(1)
                if 'k' in text[match.start():match.end()]:
                    min_wage = float(num_str) * 1000
                else:
                    min_wage = float(num_str)
                break
        
        # Check for agency exclusion
        skip_agencies = any(word in text for word in ['no agency', 'no agencies', 'direct hire', 
                                                       'skip agencies', 'not agency', 'no consultancy',
                                                       'no staffing', 'exclude agencies'])
        
        # Determine max results
        max_results = 50
        if 'all' in text:
            max_results = 200
        elif 'top' in text:
            match = re.search(r'top\s+(\d+)', text)
            if match:
                max_results = int(match.group(1))
        
        result = search_h1b_jobs(
            job_role=job_role,
            city=city,
            state=state,
            min_wage=min_wage,
            max_results=max_results,
            skip_agencies=skip_agencies
        )
        
        return {
            "action": "search_h1b_jobs",
            "search_params": {
                "job_role": job_role,
                "city": city,
                "state": state,
                "min_wage": min_wage,
                "skip_agencies": skip_agencies
            },
            "result": result,
            "suggestions": [
                f"Tell me more about {result['results'][0]['employer']}" if result.get('results') else None,
                "Export these results to CSV",
                "Show me different job roles"
            ]
        }
    
    # 3. COMPANY STATS
    if any(word in text for word in ['tell', 'about', 'statistics', 'stats', 'info', 'information']) and \
       any(word in text for word in ['company', 'employer', 'google', 'microsoft', 'amazon', 'apple', 
                                      'meta', 'facebook', 'netflix', 'tesla', 'uber']):
        
        # Extract company name - look for known companies or capitalized words
        company = None
        known_companies = ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Facebook', 
                          'Netflix', 'Tesla', 'Uber', 'Airbnb', 'Twitter', 'LinkedIn',
                          'Oracle', 'Salesforce', 'Adobe', 'Intel', 'Nvidia', 'AMD',
                          'IBM', 'Cisco', 'Dell', 'HP', 'VMware', 'Qualcomm']
        
        for c in known_companies:
            if c.lower() in text:
                company = c
                break
        
        if not company:
            # Try to find a capitalized company name
            match = re.search(r"about\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)'?s?", original_prompt)
            if match:
                company = match.group(1)
        
        if company:
            result = get_company_stats(company_name=company)
            return {
                "action": "get_company_stats",
                "company": company,
                "result": result,
                "suggestions": [
                    f"Search for jobs at {company}",
                    "Show me top H-1B sponsors",
                    "Compare with other companies"
                ]
            }
    
    # 4. TOP SPONSORS
    if any(word in text for word in ['top', 'best', 'leading', 'biggest', 'most']) and \
       any(word in text for word in ['sponsor', 'company', 'employer', 'h-1b', 'h1b']):
        
        limit = 20
        match = re.search(r'top\s+(\d+)', text)
        if match:
            limit = int(match.group(1))
        
        exclude_agencies = 'no agency' in text or 'no agencies' in text or 'exclude agencies' in text
        if not exclude_agencies:
            exclude_agencies = True  # Default to excluding agencies
        
        result = get_top_sponsors(limit=limit, exclude_agencies=exclude_agencies)
        return {
            "action": "get_top_sponsors",
            "limit": limit,
            "result": result,
            "suggestions": [
                "Tell me more about the top company",
                "Search for specific job roles",
                "Show me sponsors including agencies"
            ]
        }
    
    # 5. EXPORT RESULTS
    if any(word in text for word in ['export', 'save', 'download', 'csv', 'excel', 'file', 'spreadsheet']):
        
        # Try to extract job role for export
        job_role = "Software Engineer"  # Default
        for pattern, title in [
            (r'software\s+engineer', 'Software Engineer'),
            (r'data\s+scientist', 'Data Scientist'),
            (r'data\s+engineer', 'Data Engineer'),
            (r'product\s+manager', 'Product Manager'),
        ]:
            if re.search(pattern, text):
                job_role = title
                break
        
        # Extract location if mentioned
        city = None
        state = None
        state_match = re.search(r'\b([A-Z]{2})\b', original_prompt)
        if state_match:
            state = state_match.group(1)
        
        # Generate filename
        filename_parts = [job_role.lower().replace(' ', '_')]
        if city:
            filename_parts.append(city.lower().replace(' ', '_'))
        if state:
            filename_parts.append(state.lower())
        filename = '_'.join(filename_parts) + '_h1b.csv'
        
        result = export_results(
            job_role=job_role,
            city=city,
            state=state,
            filename=filename
        )
        
        return {
            "action": "export_results",
            "filename": filename,
            "result": result,
            "suggestions": [
                "Search for different roles",
                "Filter by location",
                "Show me top sponsors"
            ]
        }
    
    # 6. CHECK AVAILABLE DATA
    if any(word in text for word in ['available', 'check', 'what', 'which']) and \
       any(word in text for word in ['data', 'year', 'quarter', 'period']):
        
        result = get_available_data()
        return {
            "action": "get_available_data",
            "result": result,
            "suggestions": [
                f"Load data for {result['current_period']['year']} Q{result['current_period']['quarter']}",
                "Search for jobs",
                "Show me top sponsors"
            ]
        }
    
    # DEFAULT: Show helpful suggestions
    return {
        "action": "help",
        "message": "I can help you search for H-1B sponsoring companies! Here's what you can ask:",
        "examples": [
            "Load the latest H-1B data",
            "Find software engineer jobs in California",
            "Show me data scientist positions paying over 150k",
            "Tell me about Google's H-1B sponsorships",
            "Who are the top 20 H-1B sponsors?",
            "Export Python developer jobs to CSV"
        ],
        "suggestions": [
            "Load H-1B data for 2024 Q4",
            "Search for your dream job",
            "Check top H-1B sponsors"
        ]
    }

@mcp.tool(description="Get available LCA data years and quarters")
def get_available_data() -> Dict:
    """
    List available LCA data periods and cached files.
    
    Returns:
        Available years, quarters, and cached files
    """
    cached_files = []
    if os.path.exists(DATA_CACHE_DIR):
        for file in os.listdir(DATA_CACHE_DIR):
            if file.endswith('.pkl'):
                cached_files.append(file)
    
    current_year = datetime.now().year
    current_quarter = (datetime.now().month - 1) // 3 + 1
    
    return {
        "current_period": {
            "year": current_year,
            "quarter": current_quarter
        },
        "available_years": list(range(2020, current_year + 1)),
        "available_quarters": [1, 2, 3, 4],
        "cached_files": cached_files,
        "cache_directory": DATA_CACHE_DIR,
        "note": "LCA data is typically available with a 1-quarter delay"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"Starting H1B Job Search MCP Server on {host}:{port}")
    print("Available tools:")
    print("- load_h1b_data: Download and load LCA data")
    print("- search_h1b_jobs: Search for H-1B sponsoring companies")
    print("- get_company_stats: Get company sponsorship statistics")
    print("- get_top_sponsors: List top H-1B sponsors")
    print("- export_results: Export search results to CSV")
    print("- get_available_data: Check available data periods")
    
    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )