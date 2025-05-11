import streamlit as st
import os
import json
import anthropic
import pandas as pd
import PyPDF2
import docx
import requests
from typing import Dict, List, Any, Tuple
import matplotlib.pyplot as plt

# Constants
THEIRSTACK_API_URL = "https://api.theirstack.com"

def test_theirstack_api(api_key):
    """
    Test the TheirStack API with a minimal query to verify connectivity
    
    Returns:
        tuple: (success, message)
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Create minimal valid query with required filters
    test_query = {
        "posted_at_max_age_days": 30  # One of the required filters
    }
    
    try:
        response = requests.post(
            f"{THEIRSTACK_API_URL}/jobs/search",
            headers=headers,
            json=test_query
        )
        
        if response.status_code == 200:
            return True, "API connection successful"
        else:
            return False, f"API Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

class ResumeAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def analyze_resume(self, resume_text: str) -> Dict:
        """Analyze resume using Claude to extract skills and experience"""
        system_prompt = """
        You are an expert resume analyzer. Extract the following information from the resume:
        1. Technical skills
        2. Soft skills
        3. Years of experience
        4. Education
        5. Key achievements
        
        Return the analysis in this JSON format:
        {
            "technical_skills": [],
            "soft_skills": [],
            "years_experience": number,
            "education": [],
            "achievements": [],
            "seniority_level": "entry/mid/senior"
        }
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": resume_text}]
            )
            return json.loads(response.content[0].text)
        except Exception as e:
            st.error(f"Error analyzing resume: {e}")
            return None

class JobMatcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def search_jobs(self, query: Dict) -> List[Dict]:
        """Search jobs using TheirStack API"""
        # Translate our internal query format to the API's expected format
        api_query = self._format_search_query(query)
        
        try:
            # Log the query for debugging
            print(f"Sending search query: {json.dumps(api_query)}")
            
            response = requests.post(
                f"{THEIRSTACK_API_URL}/jobs/search",
                headers=self.headers,
                json=api_query
            )
            
            # If there's an error, print more details
            if response.status_code != 200:
                print(f"API Response: {response.status_code} - {response.text}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Error searching jobs: {e}")
            return []
    
    def _format_search_query(self, query: Dict) -> Dict:
        """Format the query according to TheirStack API expectations"""
        # Build a properly formatted query with required fields
        formatted_query = {}
        
        # IMPORTANT: At least one of these filters is REQUIRED
        # Map date_posted to API format and convert to required filter
        date_posted = query.get("date_posted")
        if date_posted == "Last 24 hours":
            formatted_query["posted_at_max_age_days"] = 1
        elif date_posted == "Last 7 days":
            formatted_query["posted_at_max_age_days"] = 7
        elif date_posted == "Last 30 days":
            formatted_query["posted_at_max_age_days"] = 30
        else:
            # Default to 90 days if no specific time frame is selected
            formatted_query["posted_at_max_age_days"] = 90
        
        # Add company name filter if provided (this is one of the required filters)
        if query.get("company"):
            formatted_query["company_name_or"] = [query.get("company")]
        
        # Add other optional filters
        if query.get("title"):
            formatted_query["job_title_contains_any"] = [query.get("title")]
        
        if query.get("location"):
            formatted_query["location_contains_any"] = [query.get("location")]
        
        # Remote work filter
        if query.get("remote") is True:
            formatted_query["remote_contains_any"] = ["true"]
        
        # Add skills if available - using the appropriate API field name
        if query.get("skills"):
            skills = query.get("skills")
            if isinstance(skills, list) and skills:
                formatted_query["technologies_contains_any"] = skills
        
        # Add experience level if available
        if query.get("experience_level"):
            level = query.get("experience_level").lower()
            if level in ["entry", "mid", "senior"]:
                formatted_query["seniority_contains_any"] = [level]
        
        return formatted_query
    
    def calculate_match_score(self, job: Dict, candidate_skills: List[str]) -> float:
        """Calculate match score between job and candidate skills"""
        required_skills = set(job.get("required_skills", []))
        candidate_skills = set(candidate_skills)
        
        if not required_skills:
            return 0.0
        
        matches = required_skills.intersection(candidate_skills)
        score = len(matches) / len(required_skills) * 100
        return round(score, 2)

def process_uploaded_file(uploaded_file):
    """Extract text from uploaded resume file"""
    if uploaded_file is None:
        return None
    
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
            
        elif file_extension == 'docx':
            doc = docx.Document(uploaded_file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
            
        elif file_extension == 'txt':
            return uploaded_file.read().decode('utf-8')
            
        else:
            st.error(f"Unsupported file format: {file_extension}")
            return None
            
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None

def create_match_visualization(jobs: List[Dict]):
    """Create visualization of job matches"""
    if not jobs:
        return None
    
    # Create bar chart of top matches
    companies = [f"{job['company']} - {job['title']}" for job in jobs[:10]]
    scores = [job['match_score'] for job in jobs[:10]]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(companies, scores, color='skyblue')
    
    ax.set_xlabel('Match Score (%)')
    ax.set_title('Top Job Matches')
    
    # Add score labels
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2,
                f'{scores[i]}%', ha='left', va='center')
    
    plt.tight_layout()
    return fig

def main():
    st.set_page_config(page_title="AI Job Matcher", layout="wide")
    
    # Initialize session state
    if "step" not in st.session_state:
        st.session_state.step = 1
    
    # Add custom styling
    st.markdown("""
        <style>
        .main-title { font-size: 2.5em; color: #1E88E5; text-align: center; margin-bottom: 1em; }
        .step-title { font-size: 1.8em; color: #0D47A1; margin-bottom: 0.5em; }
        .match-score { font-size: 1.5em; font-weight: bold; color: #2E7D32; }
        .job-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            background-color: white;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 class='main-title'>AI Job Matcher</h1>", unsafe_allow_html=True)
    
    # Sidebar for API keys
    with st.sidebar:
        st.title("⚙️ Settings")
        claude_api_key = st.text_input("Claude API Key", type="password")
        theirstack_api_key = st.text_input("TheirStack API Key", type="password")
        
        if claude_api_key:
            os.environ["ANTHROPIC_API_KEY"] = claude_api_key
        if theirstack_api_key:
            os.environ["THEIRSTACK_API_KEY"] = theirstack_api_key
            
        # Add API test button
        if theirstack_api_key and st.button("Test TheirStack API"):
            with st.spinner("Testing API connection..."):
                success, message = test_theirstack_api(theirstack_api_key)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    # Step 1: Upload and Analyze CV
    if st.session_state.step == 1:
        st.markdown("<h2 class='step-title'>Step 1: Upload Your CV</h2>", unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Upload your CV", type=["pdf", "docx", "txt"])
        
        if uploaded_file:
            with st.spinner("Processing your CV..."):
                resume_text = process_uploaded_file(uploaded_file)
                if resume_text:
                    if not claude_api_key:
                        st.error("Please enter your Claude API key in the sidebar")
                    else:
                        analyzer = ResumeAnalyzer(claude_api_key)
                        analysis = analyzer.analyze_resume(resume_text)
                        
                        if analysis:
                            st.success("CV analyzed successfully!")
                            st.session_state.resume_analysis = analysis
                            
                            # Display extracted information
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("Technical Skills")
                                st.write(", ".join(analysis["technical_skills"]))
                                
                                st.subheader("Experience")
                                st.write(f"Years: {analysis['years_experience']}")
                                st.write(f"Level: {analysis['seniority_level']}")
                            
                            with col2:
                                st.subheader("Education")
                                for edu in analysis["education"]:
                                    st.write(f"• {edu}")
                                
                                st.subheader("Key Achievements")
                                for achievement in analysis["achievements"]:
                                    st.write(f"• {achievement}")
                            
                            if st.button("Continue to Job Preferences"):
                                st.session_state.step = 2
                                st.rerun()
    
    # Step 2: Set Job Preferences
    elif st.session_state.step == 2:
        st.markdown("<h2 class='step-title'>Step 2: Set Job Preferences</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            job_title = st.text_input("Desired Job Title", placeholder="e.g., Software Engineer")
            location = st.text_input("Location", placeholder="e.g., New York")
            company = st.text_input("Company Name (Optional)", placeholder="e.g., Google")
        
        with col2:
            date_posted = st.selectbox("Date Posted", 
                ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days"])
            remote_preference = st.selectbox("Remote Work Preference",
                ["Any", "Remote only", "Hybrid", "In-office"])
        
        if st.button("Search Jobs"):
            if not job_title and not company:
                st.error("Please enter either a job title or company name")
            else:
                st.session_state.job_preferences = {
                    "title": job_title,
                    "location": location,
                    "company": company,
                    "date_posted": date_posted,
                    "remote": remote_preference
                }
                st.session_state.step = 3
                st.rerun()
    
    # Step 3: Search Jobs
    elif st.session_state.step == 3:
        st.markdown("<h2 class='step-title'>Step 3: Searching for Jobs</h2>", unsafe_allow_html=True)
        
        if not theirstack_api_key:
            st.error("Please enter your TheirStack API key in the sidebar")
        else:
            with st.spinner("Searching for matching jobs..."):
                matcher = JobMatcher(theirstack_api_key)
                
                # Prepare search query
                analysis = st.session_state.get("resume_analysis", {})
                preferences = st.session_state.get("job_preferences", {})
                
                # Create a query that meets the API requirements
                search_query = {
                    "title": preferences.get("title", ""),
                    "location": preferences.get("location", ""),
                    "company": preferences.get("company", ""),
                    "remote": preferences.get("remote") == "Remote only",
                    "date_posted": preferences.get("date_posted", "Last 30 days"),
                    "skills": analysis.get("technical_skills", []),
                    "experience_level": analysis.get("seniority_level", "")
                }
                
                # For debugging
                st.write("Debug - Search Query:", search_query)
                
                try:
                    jobs = matcher.search_jobs(search_query)
                    
                    if jobs:
                        st.session_state.jobs = jobs
                        st.session_state.step = 4
                        st.rerun()
                    else:
                        st.warning("No jobs found matching your criteria. Try broadening your search.")
                        
                        # Add a button to go back to preferences
                        if st.button("Adjust Preferences"):
                            st.session_state.step = 2
                            st.rerun()
                except Exception as e:
                    st.error(f"Error during job search: {str(e)}")
                    st.info("Try simplifying your search criteria or check your API key.")
                    
                    # Add error details for debugging
                    with st.expander("Error Details"):
                        st.code(str(e))
    
    # Step 4: Display Results
    elif st.session_state.step == 4:
        st.markdown("<h2 class='step-title'>Step 4: Your Job Matches</h2>", unsafe_allow_html=True)
        
        jobs = st.session_state.get("jobs", [])
        analysis = st.session_state.get("resume_analysis", {})
        
        if not jobs:
            st.error("No job matches found")
            return
        
        # Calculate match scores
        matcher = JobMatcher(theirstack_api_key)
        candidate_skills = analysis.get("technical_skills", [])
        
        for job in jobs:
            job["match_score"] = matcher.calculate_match_score(job, candidate_skills)
        
        # Sort by match score
        jobs.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Create visualization
        fig = create_match_visualization(jobs)
        if fig:
            st.pyplot(fig)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_score = st.slider("Minimum Match Score", 0, 100, 50)
        with col2:
            location_filter = st.multiselect("Location", 
                list(set(job.get("location", "") for job in jobs)))
        with col3:
            remote_filter = st.multiselect("Remote Type",
                list(set(job.get("remote_type", "") for job in jobs if "remote_type" in job)))
        
        # Apply filters
        filtered_jobs = [
            job for job in jobs
            if job["match_score"] >= min_score
            and (not location_filter or job.get("location", "") in location_filter)
            and (not remote_filter or job.get("remote_type", "") in remote_filter)
        ]
        
        # Display jobs
        for job in filtered_jobs:
            with st.container():
                st.markdown(f"""
                <div class="job-card">
                    <h3>{job.get('title', 'Untitled')} at {job.get('company', 'Unknown')}</h3>
                    <p>Location: {job.get('location', 'Not specified')}</p>
                    <p>Match Score: <span class="match-score">{job['match_score']}%</span></p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("View Details"):
                    st.markdown("### Job Description")
                    st.write(job.get("description", "No description available"))
                    
                    st.markdown("### Required Skills")
                    if "required_skills" in job and job["required_skills"]:
                        st.write(", ".join(job["required_skills"]))
                    else:
                        st.write("No specific skills listed")
                    
                    st.markdown("### Your Matching Skills")
                    matching_skills = set(job.get("required_skills", [])) & set(candidate_skills)
                    if matching_skills:
                        st.write(", ".join(matching_skills))
                    else:
                        st.write("No direct skill matches")
                    
                    if "apply_url" in job:
                        st.markdown(f"[Apply Now]({job['apply_url']})")
        
        # Button to start over
        if st.button("Start Over"):
            st.session_state.step = 1
            st.rerun()

if __name__ == "__main__":
    main()