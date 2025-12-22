from __future__ import annotations
from typing import TypedDict, NotRequired, Optional, Literal, List, Dict, Any, Set, cast, Tuple
from lxml import html as lxml_html
import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

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

def extract_form_fields_from_dom_html(dom_html: str) -> List[FormField]:
    """
    Deterministically parse DOM HTML and return FormField[].
    - Handles native input/textarea/select
    - Treats ARIA combobox widgets (React-Select) as input_type="select"
    - options only extracted for native <select> (static HTML)
    """
    doc = lxml_html.fromstring(dom_html)
    root = _pick_form_scope(doc)
    logger.info(f"Form scope selected: {root.tag}")

    candidates = root.cssselect("input, textarea, select")
    logger.info(f"Found {len(candidates)} candidate form elements.")

    out: List[FormField] = []
    seen: Set[str] = set()
    fallback_idx = 0

    for el in candidates:
        logger.info(f"Processing element: {lxml_html.tostring(el, pretty_print=True).decode('utf-8').strip()}")
        if _should_skip_control(el):
            logger.info("Skipping control element.")
            continue

        input_type = _infer_input_type(el)
        sig = _signature_for(el, fallback_idx)
        fallback_idx += 1

        if not sig or sig in seen:
            logger.info(f"Skipping element with duplicate or empty signature: {sig}")
            continue
        seen.add(sig)

        label = _label_for(root, el) or sig
        required = _is_required(root, el)
        selector = _selector_for(el)

        field: FormField = {
            "question_signature": sig,
            "label": label,
            "input_type": input_type,
            "required": required,
        }
        if selector:
            field["selector"] = selector

        opts = _options_for(el, input_type)
        if opts is not None:
            field["options"] = opts
        
        logger.info(f"Extracted field: {field}")
        out.append(field)

    return out


def _pick_form_scope(doc):
    scope = doc.cssselect("form#application-form")
    return scope[0] if scope else doc

def _should_skip_control(el) -> bool:
    tag = (getattr(el, "tag", "") or "").lower()
    input_type = (el.get("type") or "").lower()

    aria_hidden = (el.get("aria-hidden") or "").lower() == "true"
    tabindex = (el.get("tabindex") or "").strip()

    # 1) Non-user controls (framework internals, hidden validation inputs, etc.)
    # This catches react-select/remix "requiredInput" artifacts across many sites.
    if aria_hidden or tabindex == "-1":
        return True

    # 2) Hidden inputs
    if tag == "input" and input_type == "hidden":
        return True

    # 3) Buttons / submits
    if tag == "input" and input_type in {"submit", "button", "reset", "image"}:
        return True

    # 4) Dropdown "search" inputs used internally by UI widgets (e.g., intl-tel-input, select libraries)
    # Heuristic: type=search + placeholder "Search" + appears to control a listbox
    if tag == "input" and input_type == "search":
        placeholder = (el.get("placeholder") or "").strip().lower()
        aria_controls = (el.get("aria-controls") or "").strip().lower()
        role = (el.get("role") or "").strip().lower()
        if placeholder == "search" and (role in {"combobox", "searchbox"} or "listbox" in aria_controls):
            return True

    return False


def _norm_text(s: Optional[str]) -> str:
    return " ".join((s or "").replace("\xa0", " ").split()).strip()


def _label_for(root, el) -> str:
    el_id = el.get("id")

    # 1) <label for="...">
    if el_id:
        labs = root.cssselect(f'label[for="{el_id}"]')
        if labs:
            txt = _norm_text(labs[0].text_content()).replace("*", "").strip()
            if txt:
                return txt

    # 2) aria-label
    aria_label = el.get("aria-label")
    if aria_label:
        return _norm_text(aria_label)

    # 3) aria-labelledby
    labelledby = el.get("aria-labelledby")
    if labelledby:
        parts: List[str] = []
        for rid in labelledby.split():
            refs = root.cssselect(f"#{rid}")
            if refs:
                t = _norm_text(refs[0].text_content())
                if t:
                    parts.append(t)
        if parts:
            return _norm_text(" ".join(parts))

    # 4) ancestor label wrapper
    anc = el.getparent()
    while anc is not None:
        if (getattr(anc, "tag", "") or "").lower() == "label":
            txt = _norm_text(anc.text_content()).replace("*", "").strip()
            if txt:
                return txt
        anc = anc.getparent()

    return ""


def _is_required(root, el) -> bool:
    # Strong, direct signals only (works across job boards)
    if (el.get("aria-required") or "").lower() == "true":
        return True

    if el.get("required") is not None:
        return True

    # Star in label text (common on many forms)
    el_id = el.get("id")
    if el_id:
        labs = root.cssselect(f'label[for="{el_id}"]')
        if labs and "*" in (labs[0].text_content() or ""):
            return True

    return False


def _selector_for(el) -> str:
    el_id = el.get("id")
    if el_id:
        return f"#{el_id}"
    name = el.get("name")
    if name:
        return f'[name="{name}"]'
    return ""


def _signature_for(el, fallback_idx: int) -> str:
    return el.get("id") or el.get("name") or f"field_{fallback_idx}"


def _infer_input_type(el) -> "InputType":
    tag = (getattr(el, "tag", "") or "").lower()
    if tag == "textarea":
        return "textarea"
    if tag == "select":
        return "select"
    if tag != "input":
        return "unknown"

    # React-select / ARIA combobox behaves like select
    role = (el.get("role") or "").lower()
    if role == "combobox" or (el.get("aria-autocomplete") == "list"):
        return "select"

    t = (el.get("type") or "text").lower()
    if t in {
        "text",
        "date",
        "number",
        "email",
        "password",
        "file",
        "tel",
        "url",
        "hidden",
        "radio",
        "checkbox",
    }:
        return cast("InputType", t)
    return "unknown"


def _options_for(el, input_type: "InputType") -> Optional[List[str]]:
    tag = (getattr(el, "tag", "") or "").lower()
    if input_type == "select" and tag == "select":
        opts = [_norm_text(o.text_content()) for o in el.cssselect("option")]
        opts = [o for o in opts if o]
        return opts
    return None

