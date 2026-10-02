import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in the .env file.")

client = genai.Client(api_key=api_key)


EXTRACTION_PROMPT = """
You are an intelligent document processing system.

Analyze the uploaded invoice and extract the information into JSON.

Return ONLY valid JSON. Do not include markdown, explanations, or code fences.

Use exactly this structure:

{
    "vendor": "",
    "invoice_number": "",
    "invoice_date": "",
    "due_date": "",
    "currency": "",
    "subtotal": 0,
    "tax": 0,
    "total": 0,
    "line_items": [
        {
            "description": "",
            "quantity": 0,
            "unit_price": 0,
            "amount": 0
        }
    ]
}

Rules:
- Do not guess information that is not present.
- Use null when a field cannot be determined.
- Convert numeric financial values to numbers, not strings.
- Preserve the currency exactly when it is identifiable.
- Extract every visible line item.
- Make sure subtotal, tax, and total are extracted separately.
"""


def extract_invoice(file_path: str) -> dict:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    mime_type = get_mime_type(path)

    with open(path, "rb") as file:
        document_data = file.read()

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            types.Part.from_bytes(
                data=document_data,
                mime_type=mime_type,
            ),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini returned invalid JSON:\n{response.text}"
        ) from exc


def get_mime_type(path: Path) -> str:
    extension = path.suffix.lower()

    mime_types = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    mime_type = mime_types.get(extension)

    if not mime_type:
        raise ValueError(
            "Unsupported file type. Use PDF, PNG, JPG, JPEG, or WEBP."
        )

    return mime_type