import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException

from backend.services.extraction import extract_invoice
from backend.services.validation import validate_invoice


app = FastAPI(
    title="DocuFlow AI",
    description="AI-powered document processing and workflow automation.",
    version="0.1.0",
)


UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {
        "name": "DocuFlow AI",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/documents/process")
async def process_document(file: UploadFile = File(...)):
    allowed_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type.",
        )

    document_id = str(uuid.uuid4())

    extension = Path(file.filename).suffix.lower()
    file_path = UPLOAD_DIR / f"{document_id}{extension}"

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        invoice = extract_invoice(str(file_path))
        validation = validate_invoice(invoice)

        return {
            "document_id": document_id,
            "filename": file.filename,
            "invoice": invoice,
            "validation": validation,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
    
@app.post("/documents/validate")
async def validate_document(invoice: dict):
    try:
        validation = validate_invoice(invoice)

        return {
            "invoice": invoice,
            "validation": validation,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
    
@app.post("/integrations/mock-erp")
async def send_to_mock_erp(invoice: dict):
    invoice_number = invoice.get("invoice_number")

    if not invoice_number:
        raise HTTPException(
            status_code=400,
            detail="Invoice number is required.",
        )

    return {
        "status": "success",
        "message": "Invoice successfully imported into the ERP.",
        "erp_record_id": f"ERP-{invoice_number}",
        "invoice_number": invoice_number,
    }