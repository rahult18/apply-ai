import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '''..''', '''..''')))

from langgraph.graph import StateGraph, START, END
from app.models import AutofillAgentInput, AutofillAgentOutput
from app.dag_utils import FormField, FormFieldAnswer, AutofillPlanJSON, RunStatus, AutofillPlanSummary, build_autofill_plan, summarize_autofill_plan, LLMAnswersResponse
from typing import TypedDict, List, Dict, Any, Optional
from app.services.llm import LLM
from app.services.supabase import Supabase
import logging
import re
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
        Converts pre-extracted fields from JavaScript DOMParser to FormField format.
        """
        logger.debug("Executing extract_form_fields_node")
        try:
            input_data = state.get("input_data", {})
            extracted_fields = input_data.get("extracted_fields")

            if not extracted_fields:
                logger.error("extract_form_fields_node: no extracted_fields provided")
                return {
                    "errors": state.get("errors", []) + ["No extracted_fields provided"],
                    "form_fields": []
                }

            logger.info("Converting pre-extracted fields from extension")
            from app.dag_utils import convert_js_fields_to_form_fields
            form_fields = convert_js_fields_to_form_fields(extracted_fields)
            logger.info(f"Converted {len(form_fields)} pre-extracted fields")

            if form_fields:
                field_labels = [
                    f"{f.get('question_signature')}|{f.get('label')}"
                    for f in form_fields
                ]
                logger.info("Form fields: %s", field_labels)

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

            # Send full resume context to improve answer quality.
            resume_profile = input_data.get("resume_profile")
            resume_ctx = None
            try:
                # resume_profile might be Pydantic model or dict
                if resume_profile:
                    if hasattr(resume_profile, "model_dump"):
                        rp = resume_profile.model_dump()
                    else:
                        rp = resume_profile
                    resume_ctx = rp
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
                "task": f"Generate answers for ALL {len(fields_spec)} job application form fields. You MUST provide an answer for EVERY field.",
                "critical_rules": [
                    f"MANDATORY: Return exactly {len(fields_spec)} answers - one for each field in form_fields. No field can be omitted.",
                    "MANDATORY: Set action='autofill' for ALL fields. Never use 'skip' or 'suggest'.",
                    "If you don't know an answer, still use action='autofill' with value='' and confidence between 0.0-0.3.",
                ],
                "value_rules": [
                    "For select/radio/checkbox with options: return EXACTLY one option string from the provided list (case-sensitive match).",
                    "For select/radio with no perfect match: pick the closest option, set action='autofill' with lower confidence.",
                    "For text/textarea: provide your best answer using user_ctx, resume_ctx, or job_ctx data.",
                    "For missing demographic/EEO info: use value='' with confidence=0.1 (still action='autofill').",
                    "Never invent sensitive data (SSN, bank details). Use empty string if truly unknown.",
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
                            "value": "string|number|boolean|''",
                            "action": "autofill",
                            "confidence": "0.0-1.0",
                            "source": "profile|resume|jd|llm|unknown",
                        }
                    }
                },
                "final_reminder": f"You MUST return exactly {len(fields_spec)} answer objects. Every field gets action='autofill'.",
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

            def _norm_option_text(text: Any) -> str:
                text = "" if text is None else str(text)
                text = text.strip().lower()
                text = re.sub(r"\s+", " ", text)
                text = re.sub(r"[^a-z0-9 ]+", "", text)
                return text

            def _match_option(value: Any, options: List[str]) -> Optional[str]:
                if value is None:
                    return None
                target = _norm_option_text(value)
                if not target:
                    return None
                for opt in options:
                    if _norm_option_text(opt) == target:
                        return opt
                best = None
                best_len = 0
                for opt in options:
                    norm_opt = _norm_option_text(opt)
                    if not norm_opt:
                        continue
                    if target in norm_opt or norm_opt in target:
                        if len(norm_opt) > best_len:
                            best = opt
                            best_len = len(norm_opt)
                return best

            # Normalize to your FormFieldAnswer schema
            for f in form_fields:
                sig = f.get("question_signature")
                input_type = f.get("input_type")

                # File inputs: auto-assign resume upload, bypass LLM
                if input_type == "file":
                    label_lower = (f.get("label") or "").lower()
                    if any(kw in label_lower for kw in ("cover letter", "cover_letter", "coverletter")):
                        answers_out[sig] = {
                            "value": "cover_letter",
                            "source": "profile",
                            "confidence": 0.0,
                            "action": "skip",
                        }
                    else:
                        answers_out[sig] = {
                            "value": "resume",
                            "source": "profile",
                            "confidence": 1.0,
                            "action": "autofill",
                        }
                    continue

                item = validated.answers.get(sig)

                if not item:
                    answers_out[sig] = {
                        "value": None,
                        "source": "unknown",
                        "confidence": 0.0,
                        "action": "autofill",
                    }
                    continue

                # clamp confidence defensively
                conf = float(item.confidence or 0.0)
                conf = max(0.0, min(1.0, conf))

                input_type = f.get("input_type")
                value = item.value
                options = f.get("options") or []
                if input_type in {"select", "radio", "checkbox"} and options:
                    match = _match_option(value, options)
                    if match is not None:
                        value = match

                answers_out[sig] = {
                    "value": value,
                    "source": item.source or "llm",
                    "confidence": conf,
                    "action": item.action,
                }

            logger.info("Generated answers for %d fields.", len(answers_out))
            logger.info("Generated answers for fields: %s", list(answers_out.keys()))
            action_counts = {"autofill": 0, "suggest": 0, "skip": 0}
            for ans in answers_out.values():
                action = ans.get("action")
                if action in action_counts:
                    action_counts[action] += 1
            logger.info("Answer action counts: %s", action_counts)
            logger.info(
                "Autofill fields: %s",
                [sig for sig, ans in answers_out.items() if ans.get("action") == "autofill"],
            )
            logger.info(
                "Suggested fields: %s",
                [sig for sig, ans in answers_out.items() if ans.get("action") == "suggest"],
            )
            logger.info(
                "Skipped fields: %s",
                [sig for sig, ans in answers_out.items() if ans.get("action") == "skip"],
            )
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
            with supabase.get_raw_cursor() as cursor:
                cursor.execute(
                    "UPDATE public.autofill_runs SET plan_json=%s, plan_summary=%s, status=%s, updated_at=NOW() WHERE id=%s",
                    (json.dumps(plan_json), json.dumps(plan_summary), status, run_id),
                )
                if cursor.rowcount == 0:
                    logger.error("No autofill_run row updated for run_id=%s", run_id)
                else:
                    logger.info("Updated autofill_run row for run_id=%s", run_id)
                pass  # commit handled by get_raw_cursor context manager
        except Exception as e:
            logger.error("Failed to update autofill_run for run_id=%s: %s", run_id, str(e))
            errors.append(f"Error in assemble_autofill_plan_node: {str(e)}")
            status = "failed"

        return {
            "plan_json": plan_json,
            "plan_summary": plan_summary,
            "status": status,
            "errors": errors,
        }
