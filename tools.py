from crewai_tools import SerperDevTool
from groq import Groq
from playwright.async_api import async_playwright
import os
import json
from typing import Dict, List
import asyncio
from fpdf import FPDF

class JobSearchTools:
    def __init__(self):
        self.serper_tool = SerperDevTool(
            api_key=os.getenv("SERPER_API_KEY"),
            n_results=5,
            search_type="search"
        )
        
        self.groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

    async def search_jobs(self, position: str, experience_level: str) -> List[Dict]:
        """Search for jobs using Serper"""
        query = f"site:job-boards.greenhouse.io {position} {experience_level}"
        results = await self.serper_tool.search(query)
        
        jobs = []
        for result in results:
            jobs.append({
                "title": result.get("title"),
                "link": result.get("link"),
                "company": result.get("company", "Unknown"),
                "posted_date": result.get("date")
            })
        return jobs

    async def fetch_job_description(self, url: str) -> str:
        """Fetch job description using Playwright"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            
            # Wait for the job description to load
            await page.wait_for_selector(".job-description", timeout=10000)
            
            # Extract the job description
            description = await page.inner_text(".job-description")
            await browser.close()
            return description

    async def tailor_resume(self, resume: Dict, job_description: str) -> Dict:
        """Tailor resume using Groq LLM"""
        prompt = f"""
        Given this job description:
        {job_description}
        
        And this resume:
        {json.dumps(resume, indent=2)}
        
        Tailor the resume to highlight relevant experience and skills for this job.
        Return the modified resume as a JSON object with the same structure.
        """
        
        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.7,
        )
        
        return json.loads(response.choices[0].message.content)

    async def generate_pdf_resume(self, resume_data: Dict) -> bytes:
        """Generate ATS-compatible PDF resume"""
        pdf = FPDF()
        pdf.add_page()
        
        # Add content to PDF
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, resume_data["name"], ln=True)
        
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, resume_data["summary"])
        
        # Add experience
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Experience", ln=True)
        pdf.set_font("Arial", "", 12)
        for exp in resume_data["experience"]:
            pdf.multi_cell(0, 10, f"{exp['title']} at {exp['company']}")
            pdf.multi_cell(0, 10, exp['description'])
        
        return pdf.output(dest='S').encode('latin-1')

# Create a singleton instance
tools = JobSearchTools()