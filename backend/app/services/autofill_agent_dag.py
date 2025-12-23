import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '''..''', '''..''')))

from langgraph.graph import StateGraph, START, END
from app.models import AutofillAgentInput, AutofillAgentOutput
from app.dag_utils import FormField, FormFieldAnswer, AutofillPlanJSON, RunStatus, AutofillPlanSummary, extract_form_fields_from_dom_html, build_autofill_plan, summarize_autofill_plan, LLMAnswersResponse, LLMAnswerItem
from typing import TypedDict, List, Dict, Any, Optional
from app.services.llm import LLM
from app.services.supabase import Supabase
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DAG state representation
class AutofillAgentState(TypedDict):
    # The original input to the graph
    input_data: dict

    run_id: str
    page_url: str
    #derived from DOM
    form_fields: List[FormField]
    #derived from (form_fields + AutofillAgentInput)
    answers: Dict[str, FormFieldAnswer]
    plan_json: Optional[AutofillPlanJSON]
    plan_summary: Optional[AutofillPlanSummary]
    status: RunStatus
    errors: List[str]

class DAG():
    def __init__(self):
        self.graph = StateGraph(AutofillAgentState)
        self.graph.add_node("initialize", self.initialize_node)
        self.graph.add_node("extract_form_fields", self.extract_form_fields_node)
        self.graph.add_node("generate_answers", self.generate_answers_node)
        self.graph.add_node("assemble_autofill_plan", self.assemble_autofill_plan_node)
        self.graph.add_edge(START, "initialize")
        self.graph.add_edge("initialize", "extract_form_fields")
        self.graph.add_edge("extract_form_fields", "generate_answers")
        self.graph.add_edge("generate_answers", "assemble_autofill_plan")
        self.graph.add_edge("assemble_autofill_plan", END)
        self.app = self.graph.compile()

    def initialize_node(self, state: AutofillAgentState) -> dict:
        """Initializes the DAG state with input data."""
        input_data = state['input_data']
        logger.info(f"Initializing DAG for run_id: {input_data['run_id']}")
        return {
            "run_id": input_data['run_id'],
            "page_url": input_data['page_url'],
            "form_fields": [],
            "answers": {},
            "plan_json": None,
            "plan_summary": None,
            "status": "running",
            "errors": []
        }

    def extract_form_fields_node(self, state: AutofillAgentState) -> dict:
        """
        Extracts form fields from the DOM HTML.
        """
        logger.debug("Executing extract_form_fields_node")
        try:
            dom_html = state["input_data"].get("dom_html")
            if not dom_html:
                logger.warning("extract_form_fields_node: input.dom_html is empty")
                return {
                    "errors": state.get("errors", []) + ["extract_form_fields_node: input.dom_html is empty"],
                    "form_fields": []
                }

            form_fields = extract_form_fields_from_dom_html(dom_html)
            logger.info(f"Extracted {len(form_fields)} form fields.")
            logger.debug("Extracted form fields: %s", form_fields)
            return {"form_fields": form_fields}
        except Exception as e:
            logger.error(f"Error in extract_form_fields_node: {str(e)}", exc_info=True)
            return {"errors": state.get("errors", []) + [f"Error in extract_form_fields_node: {str(e)}"]}
    
    def generate_answers_node(self, state: AutofillAgentState) -> dict:
        """
        Generates answers for the extracted form fields using LLM and user data.
        Logs the prompt and the LLM response (JSON).
        """
        logger.debug("Executing generate_answers_node")
        try:
            form_fields: List[FormField] = state.get("form_fields", []) or []
            input_data = state.get("input_data", {}) or {}

            if not form_fields:
                logger.warning("generate_answers_node: no form_fields found")
                return {"answers": {}}

            # Minimal user + job context for LLM (avoid dumping entire dom_html)
            user_ctx = {
                "full_name": input_data.get("full_name"),
                "first_name": input_data.get("first_name"),
                "last_name": input_data.get("last_name"),
                "email": input_data.get("email"),
                "phone_number": input_data.get("phone_number"),
                "linkedin_url": input_data.get("linkedin_url"),
                "github_url": input_data.get("github_url"),
                "portfolio_url": input_data.get("portfolio_url"),
                "other_url": input_data.get("other_url"),
                "address": input_data.get("address"),
                "city": input_data.get("city"),
                "state": input_data.get("state"),
                "zip_code": input_data.get("zip_code"),
                "country": input_data.get("country"),
                "authorized_to_work_in_us": input_data.get("authorized_to_work_in_us"),
                "visa_sponsorship": input_data.get("visa_sponsorship"),
                "visa_sponsorship_type": input_data.get("visa_sponsorship_type"),
                "desired_salary": input_data.get("desired_salary"),
                "desired_location": input_data.get("desired_location"),
                "gender": input_data.get("gender"),
                "race": input_data.get("race"),
                "veteran_status": input_data.get("veteran_status"),
                "disability_status": input_data.get("disability_status"),
            }

            job_ctx = {
                "job_title": input_data.get("job_title"),
                "company": input_data.get("company"),
                "job_posted": input_data.get("job_posted"),
                "job_description": input_data.get("job_description"),
                "required_skills": input_data.get("required_skills"),
                "preferred_skills": input_data.get("preferred_skills"),
                "education_requirements": input_data.get("education_requirements"),
                "experience_requirements": input_data.get("experience_requirements"),
                "keywords": input_data.get("keywords"),
                "open_to_visa_sponsorship": input_data.get("open_to_visa_sponsorship"),
                "job_site_type": input_data.get("job_site_type"),
            }

            # Keep resume_profile minimal (summary + skills). Avoid huge dumps for now.
            resume_profile = input_data.get("resume_profile")
            resume_ctx = None
            try:
                # resume_profile might be Pydantic model or dict
                if resume_profile:
                    if hasattr(resume_profile, "model_dump"):
                        rp = resume_profile.model_dump()
                    else:
                        rp = resume_profile
                    resume_ctx = {
                        "summary": rp.get("summary"),
                        "skills": rp.get("skills"),
                    }
            except Exception:
                resume_ctx = None

            # Provide a concise field spec list
            fields_spec = [
                {
                    "question_signature": f.get("question_signature"),
                    "label": f.get("label"),
                    "input_type": f.get("input_type"),
                    "required": f.get("required"),
                    "options": f.get("options", []),
                }
                for f in form_fields
            ]

            prompt_obj = {
                "task": "Generate answers for job application form fields.",
                "rules": [
                    "Return JSON only, matching the provided JSON schema.",
                    "Use user_ctx for identity/contact/demographics when applicable.",
                    "For select/radio/checkbox: return the exact option text when options are provided; otherwise suggest a short best guess.",
                    "If you are not confident, set action='suggest' or 'skip' with low confidence.",
                    "Do not invent personally sensitive info. If missing, use action='suggest' and value=null.",
                ],
                "context": {
                    "page_url": input_data.get("page_url"),
                    "user_ctx": user_ctx,
                    "job_ctx": job_ctx,
                    "resume_ctx": resume_ctx,
                },
                "form_fields": fields_spec,
                "output_format": {
                    "answers": {
                        "<question_signature>": {
                            "value": "string|number|boolean|null",
                            "action": "autofill|suggest|skip",
                            "confidence": 0.0,
                            "source": "profile|resume|jd|llm|unknown",
                        }
                    }
                },
            }

            prompt = json.dumps(prompt_obj, ensure_ascii=False)

            logger.debug("LLM prompt (generate_answers_node): %s", prompt)

            llm = LLM()
            response = llm.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": LLMAnswersResponse.model_json_schema(),
                },
            )

            # Extract text robustly across SDK variants
            resp_text = None
            if hasattr(response, "text") and response.text:
                resp_text = response.text
            else:
                # fallback for other response shapes
                try:
                    resp_text = response.candidates[0].content.parts[0].text
                except Exception:
                    resp_text = str(response)

            logger.debug("LLM raw response (generate_answers_node): %s", resp_text)

            parsed = json.loads(resp_text)
            validated = LLMAnswersResponse.model_validate(parsed)

            answers_out: Dict[str, FormFieldAnswer] = {}

            # Normalize to your FormFieldAnswer schema
            for f in form_fields:
                sig = f.get("question_signature")
                item = validated.answers.get(sig)

                if not item:
                    answers_out[sig] = {
                        "value": None,
                        "source": "unknown",
                        "confidence": 0.0,
                        "action": "skip",
                    }
                    continue

                # clamp confidence defensively
                conf = float(item.confidence or 0.0)
                conf = max(0.0, min(1.0, conf))

                answers_out[sig] = {
                    "value": item.value,
                    "source": item.source or "llm",
                    "confidence": conf,
                    "action": item.action,
                }

            logger.info("Generated answers for %d fields.", len(answers_out))
            logger.debug("Generated answers (normalized): %s", json.dumps(answers_out, ensure_ascii=False))

            return {"answers": answers_out}

        except Exception as e:
            logger.error(f"Error in generate_answers_node: {str(e)}", exc_info=True)
            return {"errors": state.get("errors", []) + [f"Error in generate_answers_node: {str(e)}"]}

    
    def assemble_autofill_plan_node(self, state: AutofillAgentState) -> dict:
        """
        Assembles the final autofill plan JSON and summary.
        """
        run_id = state.get("run_id") or state.get("input_data", {}).get("run_id")
        page_url = state.get("page_url") or state.get("input_data", {}).get("page_url")
        form_fields: List[FormField] = state.get("form_fields", []) or []
        answers: Dict[str, FormFieldAnswer] = state.get("answers", {}) or {}
        errors = list(state.get("errors", []) or [])

        if not run_id or not page_url:
            errors.append("assemble_autofill_plan_node: missing run_id or page_url")
            return {"errors": errors, "status": "failed"}

        plan_json = build_autofill_plan(form_fields, answers, run_id, page_url)
        plan_summary = summarize_autofill_plan(plan_json)
        status: RunStatus = "failed" if errors else "completed"

        try:
            supabase = Supabase()
            with supabase.db_connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE public.autofill_runs SET plan_json=%s, plan_summary=%s, status=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(plan_json), json.dumps(plan_summary), status, run_id),
                )
                supabase.db_connection.commit()
        except Exception as e:
            errors.append(f"Error in assemble_autofill_plan_node: {str(e)}")
            status = "failed"

        return {
            "plan_json": plan_json,
            "plan_summary": plan_summary,
            "status": status,
            "errors": errors,
        }
    
if __name__ == "__main__":
    dag = DAG()
    supabase = Supabase()
    dom_contents = ""
    with open("/Users/rahul/Desktop/Projects/application-tracker/dom.txt", "r") as f:
        dom_contents = f.read()
    input = AutofillAgentInput(
        run_id="00000000-0000-0000-0000-000000000001",
        job_application_id="233",
        user_id="user_456",
        page_url="https://job-boards.greenhouse.io/anthropic/jobs/5042025008",
        dom_html = dom_contents,
        job_title="Software Engineer, Growth",
        company="Anthropic",
        job_posted="2024-05-01",
        job_description="We are looking for a Software Engineer, Growth to join our team...",
        required_skills=["Python", "Django", "REST APIs"],
        preferred_skills=["AWS", "Docker"],
        education_requirements=["Bachelor's degree in Computer Science or related field"],
        experience_requirements=["3+ years of experience in software development"],
        keywords=["software engineer", "growth", "backend"],
        open_to_visa_sponsorship=True,
        job_site_type="company_website",
        email="rahul.talatala@gmail.com",
        full_name="Rahul Talatala",
        first_name="Rahul",
        last_name="Talatala",
        phone_number="+1234567890",
        linkedin_url="https://www.linkedin.com/in/rahul-talatala/",
        github_url="https://www.github.com/rahultalatala",
        portfolio_url="https://www.rahultalatala.com",
        other_url="https://www.medium.com/@rahultalatala",
        resume_file_path="/Users/rahul/Downloads/Resumes/Rahul_Reddy_Talatala_Resume.pdf",
        resume_profile={
            "skills": [
                "LangGraph",
                "LangChain",
                "CrewAI",
                "RAG",
                "PyTorch",
                "TensorFlow",
                "Google ADK",
                "MCP",
                "A2A",
                "Ray",
                "ONNX",
                "MLflow",
                "NVIDIA Triton",
                "LangSmith",
                "LangFuse",
                "Kubeflow",
                "W&B",
                "Axolotl",
                "Spark",
                "Airflow",
                "Kafka",
                "dbt",
                "Snowflake",
                "TimescaleDB",
                "ETL/ELT",
                "Data Warehousing",
                "Data Modeling",
                "AWS",
                "GCP",
                "Azure",
                "Kubernetes",
                "Terraform",
                "Docker",
                "Run:AI",
                "ArgoCD",
                "Github Actions",
                "CI/CD",
                "Python",
                "SQL",
                "Java",
                "TypeScript/JavaScript",
                "FastAPI",
                "Spring Boot",
                "Node.js",
                "React",
                "REST APIs"
            ],
            "summary": "Software Engineer specializing in GenAI and ML infrastructure. At Verizon (via Infinite), built multi-agent and graph-based triage systems that automated 60% of network troubleshooting and saved $1.8M+/year. At Apple, developed an MCP-powered Kubernetes debugger and GPU observability stack that cut triage time 60% and saved $1.5M+/year.",
            "projects": [],
            "education": [
                {
                "degree": "MS",
                "end_date": "",
                "start_date": "",
                "description": "GPA: 3.8/4",
                "institution": "University at Buffalo, The State University of New York",
                "field_of_study": "Computer Science"
                },
                {
                "degree": "BTech",
                "end_date": "",
                "start_date": "",
                "description": "GPA: 3.9/4",
                "institution": "Vellore Institute of Technology, Chennai",
                "field_of_study": "Computer Science"
                }
            ],
            "experience": [
                {
                "company": "Infinite Computer Solutions (Client: Verizon)",
                "end_date": "",
                "position": "GenAI Engineer",
                "start_date": "2025-08-01",
                "description": "Led the RAN Troubleshooting Multi-Agent system using LangGraph with FastAPI, coordinating 8 domain agents for KPI correlation, outage detection, and fault analysis — automated 60% of network triage and saved $1.8M+/year as measured by tickets handled without human review, by parallelizing agent routing and supervisor decisions. Built the Out-of-Service (OoS) diagnostic agent, a graph-based AI system that analyzed vendor logs (Samsung, Ericsson, Nokia) by parsing AMOS/CSR/RRH outputs and generating automated root-cause reports — saved 47K+ engineer hours/year ($282K) as measured by auto-resolved tickets. Orchestrated retrieval-augmented analysis across agents with Elastic Vector DB + Cohere Rerank—improved context precision 35% and eliminated 2K+ false alerts/day, by indexing vendor manuals/EMS guides and enforcing tool-use guards. Introduced observability using LangFuse and LangGraph checkpointers — shortened debugging cycles 30% through end-to-end transaction tracing, state replay, and confidence scoring. Created a SQL Migration Agent that translated 35+ SingleStore schemas to Oracle—reduced migration time 70% by adding schema introspection, automated DDL conversion, and CI validation."
                },
                {
                "company": "Apple Inc., Data Platform Efficiency",
                "end_date": "2025-08-01",
                "position": "Software Engineer — GenAI Infra (Contract)",
                "start_date": "2025-04-01",
                "description": "Developed a Kubernetes Debugger with MCP and NVIDIA Triton serving a fine-tuned Qwen-1.5B model—cut triage time 60% by enabling natural-language diagnostics and real-time gRPC cluster checks. Engineered GPU Observability Pipelines using Spark, Lambda, and SQS for 5M+ CloudWatch datapoints/day—reduced latency 55% by storing metrics in TimescaleDB for fast SQL queries. Improved GPU utilization 60% and minimized idle compute 45% using Run:AI fractional scheduling for Ray workloads. Delivered $1.5M+/year in cost savings via Datadog CCM dashboards and $325K/year through automated S3 lifecycle policies. Enabled $17M/month cloud cost transparency by producing SKU-level Spark dashboards and forecasts."
                },
                {
                "company": "University at Buffalo",
                "end_date": "2024-05-01",
                "position": "ML Research Assistant",
                "start_date": "2024-01-01",
                "description": "Trained lightweight GPT-2 variants using quantization and distillation — reduced inference energy use 20% while maintaining model accuracy within 1.5%. Benchmarked compressed models for edge deployment — cut carbon emissions 45% by optimizing model storage and training efficiency."
                },
                {
                "company": "Eminent Services Corporation",
                "end_date": "2025-04-01",
                "position": "Software Engineer",
                "start_date": "2024-05-01",
                "description": "Migrated legacy VB6 systems to a modular MERN platform — boosted scalability 35% and lowered maintenance 40%. Automated CI/CD pipelines with Azure DevOps — sped up deployments 30% through build and App Service integration."
                }
            ],
            "certifications": [
                {
                "name": "AWS Certified Developer – Associate",
                "issue_date": "2024-01-01",
                "credential_id": "",
                "credential_url": "",
                "expiration_date": "",
                "issuing_organization": "AWS"
                },
                {
                "name": "Oracle Database Design & Programming with SQL",
                "issue_date": "2020-01-01",
                "credential_id": "",
                "credential_url": "",
                "expiration_date": "",
                "issuing_organization": "Oracle"
                }
            ]
            },
        address="123 Main St, Cityville",
        city="Cityville",
        state="CA",
        zip_code="12345",
        country="USA",
        authorized_to_work_in_us=True,
        visa_sponsorship=False,
        visa_sponsorship_type="H1B",
        desired_salary="12000000",
        desired_location=["San Francisco, CA", "Remote"],
        gender="Male",
        race="Asian",
        veteran_status="Not a Veteran",
        disability_status="Not Disabled"
        )
    result = dag.app.invoke({"input_data": input.model_dump()})
    logger.info("AutofillAgentOutput.status: %s", result.get("status"))
    logger.debug("AutofillAgentOutput.plan_json: %s", json.dumps(result.get("plan_json")))
    logger.info("AutofillAgentOutput.plan_summary: %s", json.dumps(result.get("plan_summary")))
