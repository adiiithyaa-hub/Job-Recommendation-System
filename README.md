# AI Job Matcher

An AI-powered application that analyzes resumes and matches candidates with suitable job opportunities using TheirStack's job database and Claude's AI capabilities.

## Features

- Resume analysis using Claude AI
- Job matching against TheirStack's database
- Match score calculation based on skills and requirements
- Interactive visualization of job matches
- Filter jobs by various criteria

## Installation

1. Clone the repository:
git clone https://github.com/yourusername/ai-job-matcher.git
cd ai-job-matcher

2. Create a virtual environment and install dependencies:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

3. Set up API keys:
- Create a `.env` file in the root directory
- Add your API keys:
  ```
  ANTHROPIC_API_KEY=your_claude_api_key
  THEIRSTACK_API_KEY=your_theirstack_api_key
  ```

## Usage

Run the Streamlit app:
streamlit run app/main.py

The app will open in your default web browser, where you can:
1. Upload your resume (PDF, DOCX, or TXT format)
2. Set job preferences
3. Search for matching jobs
4. View and filter job matches

## Requirements

- Python 3.8+
- Streamlit
- Anthropic's Claude API key
- TheirStack API key

See `requirements.txt` for the complete list of dependencies.
