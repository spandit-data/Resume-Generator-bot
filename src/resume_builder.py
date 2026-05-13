"""Google Gemini integration for structuring resume data."""

import json
import logging
import os
import re

from google import genai

logger = logging.getLogger(__name__)


def get_gemini_client():
    """Get Gemini client with API key from environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    return genai.Client(api_key=api_key)


DONT_KNOW_PATTERNS = [
    r"pata nahi",
    r"nahi pata",
    r"pata nahi hai",
    r"don't know",
    r"dont know",
    r"no idea",
    r"not sure",
    r"याद नहीं",
    r"याद नही",
    r"मालूम नहीं",
    r"मालूम नही",
    r"नहीं पता",
    r"nahi pta",
    r"no pta",
]


def is_dont_know(text: str) -> bool:
    """Check if text indicates user doesn't know the answer."""
    text_lower = text.lower().strip()
    for pattern in DONT_KNOW_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def format_education(education: str) -> str:
    """Format education to proper case (e.g., ITI, 10th, B.A., B.COM)."""
    if not education:
        return ""

    education = education.strip()

    # Words to always uppercase
    uppercase_words = ["iti", "ba", "bcom", "bba", "bca", "ma", "mcom", "mba", "mca", "12th", "10th", "phd"]

    result = []
    for word in education.split():
        word_lower = word.lower()
        # Check if it matches uppercase patterns (with or without dot)
        matched = False
        for up_word in uppercase_words:
            if word_lower.replace(".", "") == up_word:
                # Keep original case style but uppercase
                result.append(word.upper())
                matched = True
                break
        if not matched:
            # Capitalize first letter of other words
            result.append(word.capitalize())

    return " ".join(result)


EXPERIENCED_SYSTEM_PROMPT = """You are a resume data extractor. The user's answers may be in Hindi,
Hinglish, or broken text from voice transcription.
Extract and structure the data into clean JSON.
Return ONLY valid JSON, no explanation, no markdown.

JSON format:
{
  "name": "",
  "age": "",
  "city": "",
  "job_target": "",
  "previous_company": "",
  "previous_role": "",
  "experience_duration": "",
  "vehicle": "",
  "education": "",
  "education_year": "",
  "phone": "",
  "objective": "",
  "work_bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "skills": ["skill 1", "skill 2", "skill 3"]
}

If a field is not mentioned or unclear, use empty string.

For objective: Generate a single line like "Seeking a {job_target} position where I can contribute my skills and experience effectively."

For work_bullets: Generate EXACTLY 4 professional bullet points (1 line each) describing work done.

For skills: Generate EXACTLY 3 skills relevant to the job_target (e.g. for Delivery: route knowledge, time management, customer handling). Combine with general traits if needed.

For education_year: If user said they don't know (like "pata nahi", "don't know", etc.), return empty string "". Otherwise extract just the year (e.g., "2018", "2020").

Clean up names and cities to proper capitalization.
For job_target, normalize to one of: Delivery Executive, Field Sales Executive, Warehouse Picker, General Labour, Other"""

FRESHER_SYSTEM_PROMPT = """You are a resume data extractor. The user is a FRESHER with no prior work experience.
The user's answers may be in Hindi, Hinglish, or broken text from voice transcription.
Extract and structure the data into clean JSON.
Return ONLY valid JSON, no explanation, no markdown.

JSON format:
{
  "name": "",
  "age": "",
  "city": "",
  "job_target": "",
  "vehicle": "",
  "education": "",
  "education_year": "",
  "phone": "",
  "objective": "",
  "work_bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "skills": ["skill 1", "skill 2", "skill 3"]
}

NOTE: For fresher, do NOT include previous_company, previous_role, or experience_duration fields - leave them empty.

If a field is not mentioned or unclear, use empty string.

For objective: Generate a single line like "Motivated fresher seeking a {job_target} position to learn and contribute effectively."

For work_bullets: Generate EXACTLY 4 professional bullet points highlighting eagerness to learn, any internships, projects, volunteer work, or relevant skills. Focus on potential and willingness to work hard.

For skills: Generate EXACTLY 3 skills relevant to the job_target (e.g. for Delivery: time management, basic smartphone navigation, willingness to learn). Include general positive traits if needed.

For education_year: If user said they don't know (like "pata nahi", "don't know", etc.), return empty string "". Otherwise extract just the year (e.g., "2018", "2020").

Clean up names and cities to proper capitalization.
For job_target, normalize to one of: Delivery Executive, Field Sales Executive, Warehouse Picker, General Labour, Other"""


def format_answers_for_prompt(answers: dict[int, str], is_fresher: bool) -> str:
    """Format collected answers into a numbered list for Gemini."""
    if is_fresher:
        questions = [
            "Name",
            "Age",
            "City",
            "Job Target",
            "Vehicle",
            "Education",
            "Education Year",
            "Phone",
        ]
    else:
        questions = [
            "Name",
            "Age",
            "City",
            "Job Target",
            "Previous Work",
            "Experience Duration",
            "Vehicle",
            "Education",
            "Education Year",
            "Phone",
        ]

    lines = []
    for i, q in enumerate(questions):
        ans = answers.get(i, "")
        lines.append(f"Q{i + 1} ({q}): {ans}")

    return "\n".join(lines)


def structure_resume_data(answers: dict[int, str], is_fresher: bool = False) -> dict:
    """Send answers to Gemini and get structured JSON resume data."""
    client = get_gemini_client()
    formatted_answers = format_answers_for_prompt(answers, is_fresher)

    system_prompt = FRESHER_SYSTEM_PROMPT if is_fresher else EXPERIENCED_SYSTEM_PROMPT

    prompt = f"""{system_prompt}

Extract resume data from these answers:
{formatted_answers}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    response_text = response.text.strip()

    try:
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response_text = "\n".join(lines)

        data = json.loads(response_text)

        # Format education properly
        if data.get("education"):
            data["education"] = format_education(data["education"])

        # Check if education_year should be empty (user said don't know)
        # For fresher: answer index 6 corresponds to education year (0=name,1=age,2=city,3=job,4=vehicle,5=education,6=year,7=phone)
        # For experienced: answer index 8 corresponds to education year
        education_year_index = 6 if is_fresher else 8
        if is_dont_know(answers.get(education_year_index, "")):
            data["education_year"] = ""

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response: {e}\nResponse: {response_text}")
        raise