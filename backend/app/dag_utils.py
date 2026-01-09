from __future__ import annotations
from typing import TypedDict, NotRequired, Optional, Literal, List, Dict, Any, Set
import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

# Standard country list for enriching country fields
STANDARD_COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
    "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria",
    "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada",
    "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros",
    "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic", "Czechia",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
    "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia", "Germany", "Ghana",
    "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana", "Haiti",
    "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia",
    "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi",
    "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
    "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco",
    "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand",
    "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa",
    "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
    "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands",
    "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka",
    "Sudan", "Suriname", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
    "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago",
    "Tunisia", "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe"
]

# enums for various state variables
InputType = Literal["text", "textarea", "select", "radio", "checkbox", "date", "number", "email", "password", "file", "tel", "url", "hidden", "unknown"]
AnswerAction = Literal["autofill", "suggest", "skip"]
RunStatus = Literal["running", "completed", "failed"]

# classes for DAG state representation
class FormField(TypedDict):
    # this is the per-field id (useful for mapping)
    question_signature: str
    label: str
    input_type: InputType
    # only for select, radio, checkbox
    options: NotRequired[List[str]]
    # target selector in the DOM
    selector: NotRequired[str]
    required: bool

class FormFieldAnswer(TypedDict):
    value: Any
    source: NotRequired[Literal["profile", "resume", "jd", "llm", "unknown"]]
    confidence: float  # 0.0 to 1.0
    action: AnswerAction

class PlanField(TypedDict):
    question_signature: str
    label: str
    input_type: InputType
    required: bool
    action: AnswerAction
    value: Any
    confidence: float
    selector: NotRequired[str]
    options: NotRequired[List[str]]

class AutofillPlanJSON(TypedDict):
    run_id: str
    page_url: str
    fields: List[PlanField]

class AutofillPlanSummary(TypedDict):
    total_fields: int
    autofilled_fields: int
    suggested_fields: int
    skipped_fields: int

class LLMAnswerItem(BaseModel):
    value: Any = None
    action: Literal["autofill", "suggest", "skip"] = "skip"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source: Optional[Literal["profile", "resume", "jd", "llm", "unknown"]] = "llm"


class LLMAnswersResponse(BaseModel):
    answers: Dict[str, LLMAnswerItem]

class LLMAnswerItem(BaseModel):
    value: Any = None
    action: Literal["autofill", "suggest", "skip"] = "skip"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source: Optional[Literal["profile", "resume", "jd", "llm", "unknown"]] = "llm"


class LLMAnswersResponse(BaseModel):
    answers: Dict[str, LLMAnswerItem]


# Helper functions

def convert_js_fields_to_form_fields(js_fields: List[Dict[str, Any]]) -> List[FormField]:
    """
    Convert JavaScript DOMParser extracted fields to FormField format.

    Args:
        js_fields: List of field objects from browser extension

    Returns:
        List[FormField] compatible with existing DAG pipeline
    """
    out: List[FormField] = []
    seen: Set[str] = set()

    for idx, js_field in enumerate(js_fields):
        # Generate question_signature
        sig = js_field.get("id") or js_field.get("name")
        if not sig:
            # Fallback: use selector or generate from index
            selector = js_field.get("selector", "")
            sig = selector.replace("#", "").replace("[name=\"", "").replace("\"]", "")
            if not sig:
                sig = f"field_{idx}"

        # Skip duplicates
        if sig in seen:
            continue
        seen.add(sig)

        # Use label as-is (NO cleaning or transformation)
        label = js_field.get("label") or sig

        # Map input type (JS uses camelCase, Python uses snake_case literals)
        js_input_type = js_field.get("inputType", "text")
        input_type_map = {
            "text": "text",
            "email": "email",
            "tel": "tel",
            "file": "file",
            "textarea": "textarea",
            "select": "select",
            "radio": "radio",
            "checkbox": "checkbox",
            "date": "date",
            "number": "number",
            "password": "password",
            "url": "url",
            "search": "text",  # Treat search as text
        }

        # If isCombobox is true, treat as select
        if js_field.get("isCombobox"):
            input_type = "select"
        else:
            input_type = input_type_map.get(js_input_type, "text")

        # Extract options (convert from [{value, label}] to [value])
        js_options = js_field.get("options", [])
        options = []
        if isinstance(js_options, list):
            for opt in js_options:
                if isinstance(opt, dict):
                    val = opt.get("value") or opt.get("label")
                    if val:
                        options.append(str(val))
                elif isinstance(opt, str):
                    options.append(opt)

        # Build FormField
        field: FormField = {
            "question_signature": sig,
            "label": label,
            "input_type": input_type,
            "required": js_field.get("required", False),
        }

        # Optional fields
        if js_field.get("selector"):
            field["selector"] = js_field["selector"]

        if options:
            field["options"] = options

        out.append(field)

    # Post-process: enrich country fields (reuse existing logic)
    out = _enrich_country_fields(out)

    return out


def build_autofill_plan(
    form_fields: List[FormField],
    answers: Dict[str, FormFieldAnswer],
    run_id: str,
    page_url: str,
) -> AutofillPlanJSON:
    fields: List[PlanField] = []
    for f in form_fields:
        sig = f.get("question_signature")
        answer = _normalize_answer(answers.get(sig))
        plan_field: PlanField = {
            "question_signature": sig,
            "label": f.get("label"),
            "input_type": f.get("input_type"),
            "required": f.get("required"),
            "action": answer["action"],
            "value": answer["value"],
            "confidence": answer["confidence"],
        }
        selector = f.get("selector")
        if selector:
            plan_field["selector"] = selector
        options = f.get("options")
        if options:
            plan_field["options"] = options
        fields.append(plan_field)

    return {
        "run_id": run_id,
        "page_url": page_url,
        "fields": fields,
    }


def summarize_autofill_plan(plan_json: AutofillPlanJSON) -> AutofillPlanSummary:
    total = len(plan_json.get("fields", []))
    autofilled = 0
    suggested = 0
    skipped = 0
    for f in plan_json.get("fields", []):
        action = f.get("action")
        if action == "autofill":
            autofilled += 1
        elif action == "suggest":
            suggested += 1
        else:
            skipped += 1
    return {
        "total_fields": total,
        "autofilled_fields": autofilled,
        "suggested_fields": suggested,
        "skipped_fields": skipped,
    }


def _enrich_country_fields(fields: List[FormField]) -> List[FormField]:
    """
    Enrich select fields that appear to be country selectors with standard country options.
    This helps when the DOM doesn't have the listbox expanded (React Select, etc.)
    """
    for field in fields:
        # Check if this is a select field without options
        if field.get("input_type") == "select" and not field.get("options"):
            label = field.get("label", "").lower()
            sig = field.get("question_signature", "").lower()

            # Check if label or signature indicates this is a country field
            country_keywords = ["country", "nationality", "citizenship"]
            if any(keyword in label or keyword in sig for keyword in country_keywords):
                logger.info(f"Enriching country field '{field.get('label')}' with standard country list")
                field["options"] = STANDARD_COUNTRIES.copy()

    return fields


def _normalize_answer(answer: Optional[FormFieldAnswer]) -> FormFieldAnswer:
    if not answer:
        return {
            "value": None,
            "source": "unknown",
            "confidence": 0.0,
            "action": "skip",
        }
    action = answer.get("action")
    if action not in {"autofill", "suggest", "skip"}:
        action = "skip"
    if action == "suggest":
        action = "autofill"
    conf = float(answer.get("confidence") or 0.0)
    conf = max(0.0, min(1.0, conf))
    return {
        "value": answer.get("value"),
        "source": answer.get("source") or "unknown",
        "confidence": conf,
        "action": action,
    }
