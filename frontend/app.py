import hashlib
import io
import json

import fitz
import requests
import streamlit as st


API_URL = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="DocuFlow AI",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def render_html(content):
    st.html(content)


def render_pdf_preview(pdf_bytes):
    """
    Render the first PDF page as an image.

    This avoids embedding a PDF inside an iframe, which Chrome
    can block when the PDF is supplied as a data URL.
    """
    try:
        document = fitz.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

        if document.page_count == 0:
            st.warning("The PDF does not contain any pages.")
            document.close()
            return

        page = document.load_page(0)

        # Render at a reasonable resolution for the UI.
        matrix = fitz.Matrix(1.5, 1.5)
        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image_bytes = pixmap.tobytes("png")

        document.close()

        st.image(
            image_bytes,
            use_container_width=True,
        )

    except Exception as exc:
        st.error(
            f"Could not generate the document preview: {exc}"
        )


def process_document(file):
    try:
        response = requests.post(
            f"{API_URL}/documents/process",
            files={
                "file": (
                    file.name,
                    file.getvalue(),
                    file.type,
                )
            },
            timeout=120,
        )

        if response.ok:
            return response.json()

        try:
            detail = response.json().get(
                "detail",
                "Unknown error",
            )
        except Exception:
            detail = response.text

        st.error(
            f"Document processing failed: {detail}"
        )

    except requests.exceptions.ConnectionError:
        st.error(
            "Could not connect to DocuFlow. "
            "Make sure the FastAPI server is running."
        )

    except requests.exceptions.Timeout:
        st.error(
            "The document took too long to process. "
            "Please try again."
        )

    except requests.RequestException as exc:
        st.error(
            f"Request failed: {exc}"
        )

    return None


def revalidate_invoice(invoice):
    try:
        response = requests.post(
            f"{API_URL}/documents/validate",
            json=invoice,
            timeout=30,
        )

        if response.ok:
            return response.json()

        try:
            detail = response.json().get(
                "detail",
                "Unknown error",
            )
        except Exception:
            detail = response.text

        st.error(
            f"Validation failed: {detail}"
        )

    except requests.RequestException as exc:
        st.error(
            f"Validation failed: {exc}"
        )

    return None


def send_to_erp(invoice):
    try:
        response = requests.post(
            f"{API_URL}/integrations/mock-erp",
            json=invoice,
            timeout=30,
        )

        if response.ok:
            return response.json()

        try:
            detail = response.json().get(
                "detail",
                "Unknown error",
            )
        except Exception:
            detail = response.text

        st.error(
            f"ERP integration failed: {detail}"
        )

    except requests.RequestException as exc:
        st.error(
            f"ERP integration failed: {exc}"
        )

    return None


def file_key(file):
    data = file.getvalue()

    return hashlib.md5(
        data,
        usedforsecurity=False,
    ).hexdigest()


def add_activity(
    message,
    status="success",
):
    if "activity" not in st.session_state:
        st.session_state["activity"] = []

    st.session_state["activity"].append(
        {
            "message": message,
            "status": status,
        }
    )


def reset_document_state():
    st.session_state["result"] = None
    st.session_state["approved"] = False
    st.session_state["erp_result"] = None
    st.session_state["activity"] = []


def info_card(label, value):
    if value in (None, ""):
        value = "—"

    render_html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #e2e8f0;
            border-radius:13px;
            padding:17px 18px;
            min-height:86px;
            box-sizing:border-box;
        ">
            <div style="
                color:#64748b;
                font-size:12px;
                margin-bottom:7px;
            ">
                {label}
            </div>

            <div style="
                color:#111827;
                font-size:16px;
                font-weight:650;
                overflow-wrap:anywhere;
            ">
                {value}
            </div>
        </div>
        """
    )


def money_card(
    label,
    value,
    currency,
    total=False,
):
    if total:
        background = "#111827"
        border = "#111827"
        label_color = "#9ca3af"
        value_color = "#ffffff"
    else:
        background = "#ffffff"
        border = "#e2e8f0"
        label_color = "#64748b"
        value_color = "#111827"

    render_html(
        f"""
        <div style="
            background:{background};
            border:1px solid {border};
            border-radius:13px;
            padding:19px;
            box-sizing:border-box;
        ">
            <div style="
                color:{label_color};
                font-size:12px;
                margin-bottom:7px;
            ">
                {label}
            </div>

            <div style="
                color:{value_color};
                font-size:23px;
                font-weight:700;
                letter-spacing:-0.4px;
            ">
                {currency} {float(value or 0):,.2f}
            </div>
        </div>
        """
    )


def summary_card(
    label,
    value,
    accent=False,
):
    if accent:
        background = "#111827"
        value_color = "#ffffff"
        label_color = "#9ca3af"
        border = "#111827"
    else:
        background = "#ffffff"
        value_color = "#111827"
        label_color = "#64748b"
        border = "#e2e8f0"

    render_html(
        f"""
        <div style="
            background:{background};
            border:1px solid {border};
            border-radius:12px;
            padding:16px;
            min-height:78px;
            box-sizing:border-box;
        ">
            <div style="
                color:{label_color};
                font-size:11px;
                margin-bottom:7px;
            ">
                {label}
            </div>

            <div style="
                color:{value_color};
                font-size:21px;
                font-weight:700;
            ">
                {value}
            </div>
        </div>
        """
    )


def pipeline_step(
    number,
    title,
    state,
):
    if state == "done":
        icon = "✓"
        bg = "#ecfdf5"
        border = "#a7f3d0"
        icon_color = "#047857"

    elif state == "active":
        icon = "●"
        bg = "#eff6ff"
        border = "#bfdbfe"
        icon_color = "#2563eb"

    else:
        icon = str(number)
        bg = "#f8fafc"
        border = "#e2e8f0"
        icon_color = "#94a3b8"

    return f"""
        <div style="
            display:flex;
            align-items:center;
            gap:9px;
            flex:1;
            min-width:130px;
        ">
            <div style="
                width:28px;
                height:28px;
                border-radius:50%;
                background:{bg};
                border:1px solid {border};
                color:{icon_color};
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:12px;
                font-weight:700;
            ">
                {icon}
            </div>

            <div style="
                color:#334155;
                font-size:12px;
                font-weight:600;
            ">
                {title}
            </div>
        </div>
    """


# -------------------------------------------------------------------
# Global styling
# -------------------------------------------------------------------

st.markdown(
    """
    <style>

        .stApp {
            background: #f6f8fb;
        }

        .block-container {
            max-width: 1200px;
            padding: 2.2rem 2rem 4rem;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        /* ---------------------------------------------------------
           File uploader
        --------------------------------------------------------- */

        [data-testid="stFileUploader"] {
            background: #f8fafc;
            border: 1.5px dashed #cbd5e1;
            border-radius: 12px;
            padding: 8px;
        }


        /* ---------------------------------------------------------
           Buttons
        --------------------------------------------------------- */

        .stButton > button {
            border-radius: 9px;
            border: 1px solid #d1d5db;
            font-weight: 600;
            color: #1f2937;
            background: white;
        }

        .stButton > button[kind="primary"] {
            background: #111827;
            color: white;
            border: none;
        }

        .stButton > button[kind="primary"]:hover {
            background: #1f2937;
        }

        .stDownloadButton > button {
            border-radius: 9px;
            border: 1px solid #d1d5db;
            background: white;
            color: #1f2937;
            font-weight: 600;
        }


        /* ---------------------------------------------------------
           Data editor
        --------------------------------------------------------- */

        [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
        }


        /* ---------------------------------------------------------
           Human review inputs
        --------------------------------------------------------- */

        .stTextInput label,
        .stNumberInput label {
            color: #475569 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            margin-bottom: 6px !important;
        }

        .stTextInput > div > div,
        .stNumberInput > div > div {
            background: #ffffff !important;
            border: 1px solid #d7dee8 !important;
            border-radius: 9px !important;
            box-shadow: none !important;
        }

        .stTextInput input,
        .stNumberInput input {
            background: #ffffff !important;
            color: #111827 !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            border-radius: 9px !important;
            font-size: 13px !important;
        }

        .stTextInput > div > div:focus-within,
        .stNumberInput > div > div:focus-within {
            border: 1px solid #94a3b8 !important;
            box-shadow:
                0 0 0 2px
                rgba(148, 163, 184, 0.12) !important;
        }

        .stNumberInput button {
            background: #f8fafc !important;
            color: #475569 !important;
            border: none !important;
            border-left: 1px solid #e2e8f0 !important;
        }

        .stNumberInput button:hover {
            background: #f1f5f9 !important;
            color: #111827 !important;
        }


        /* ---------------------------------------------------------
           Dividers
        --------------------------------------------------------- */

        hr {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 30px 0;
        }


        /* ---------------------------------------------------------
           Alerts
        --------------------------------------------------------- */

        [data-testid="stAlert"] {
            border-radius: 10px;
        }

    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

render_html(
    """
    <div style="
        display:flex;
        align-items:center;
        justify-content:space-between;
        margin-bottom:5px;
    ">

        <div style="
            display:flex;
            align-items:center;
            gap:12px;
        ">

            <div style="
                width:44px;
                height:44px;
                border-radius:12px;
                background:#111827;
                color:white;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:22px;
            ">
                ▤
            </div>

            <div>

                <div style="
                    font-size:28px;
                    font-weight:750;
                    color:#111827;
                    letter-spacing:-0.8px;
                ">
                    DocuFlow AI
                </div>

                <div style="
                    color:#64748b;
                    font-size:13px;
                    margin-top:1px;
                ">
                    AI-powered document processing and workflow automation
                </div>

            </div>

        </div>

        <div style="
            background:#ffffff;
            border:1px solid #e2e8f0;
            color:#64748b;
            border-radius:999px;
            padding:6px 11px;
            font-size:11px;
            font-weight:600;
        ">
            DEMO ENVIRONMENT
        </div>

    </div>
    """
)


# -------------------------------------------------------------------
# Upload section
# -------------------------------------------------------------------

render_html(
    """
    <div style="
        margin-top:28px;
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:16px;
        padding:24px;
        box-shadow:0 2px 8px rgba(15,23,42,0.04);
    ">

        <div style="
            color:#111827;
            font-size:18px;
            font-weight:700;
            margin-bottom:5px;
        ">
            Process an invoice
        </div>

        <div style="
            color:#64748b;
            font-size:13px;
            margin-bottom:18px;
        ">
            Upload an invoice and DocuFlow will automatically extract,
            validate, review, and prepare it for downstream processing.
        </div>

    </div>
    """
)


uploaded_file = st.file_uploader(
    "Choose an invoice",
    type=[
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "webp",
    ],
    label_visibility="collapsed",
)


# -------------------------------------------------------------------
# Automatic processing
# -------------------------------------------------------------------

if uploaded_file:

    current_file_key = file_key(
        uploaded_file
    )

    previous_file_key = st.session_state.get(
        "file_key"
    )


    if current_file_key != previous_file_key:

        reset_document_state()

        st.session_state["file_key"] = (
            current_file_key
        )

        st.session_state["filename"] = (
            uploaded_file.name
        )


        add_activity(
            "Document uploaded",
            "success",
        )


        with st.spinner(
            "AI is analyzing your document..."
        ):

            result = process_document(
                uploaded_file
            )


        if result:

            st.session_state["result"] = result


            add_activity(
                "AI extraction completed",
                "success",
            )


            validation = result.get(
                "validation",
                {},
            )


            if validation.get(
                "status"
            ) == "PASS":

                add_activity(
                    "Validation completed successfully",
                    "success",
                )

            else:

                add_activity(
                    "Validation requires human review",
                    "warning",
                )


            st.rerun()


result = st.session_state.get(
    "result"
)


# -------------------------------------------------------------------
# Empty state
# -------------------------------------------------------------------

if not result:

    if uploaded_file:

        render_html(
            f"""
            <div style="
                margin-top:12px;
                color:#64748b;
                font-size:12px;
            ">
                Selected:
                <b>{uploaded_file.name}</b>
                · {uploaded_file.size / 1024:.1f} KB
            </div>
            """
        )

    else:

        render_html(
            """
            <div style="
                margin-top:24px;
                background:#ffffff;
                border:1px solid #e2e8f0;
                border-radius:14px;
                padding:28px;
                text-align:center;
                color:#64748b;
            ">

                <div style="
                    font-size:30px;
                    margin-bottom:8px;
                ">
                    📄
                </div>

                <div style="
                    color:#334155;
                    font-size:15px;
                    font-weight:600;
                    margin-bottom:4px;
                ">
                    Upload an invoice to get started
                </div>

                <div style="font-size:12px;">
                    DocuFlow automatically handles the rest.
                </div>

            </div>
            """
        )

    st.stop()


# -------------------------------------------------------------------
# Main data
# -------------------------------------------------------------------

invoice = result["invoice"]

validation = result["validation"]

status = validation["status"]


# -------------------------------------------------------------------
# Workflow pipeline
# -------------------------------------------------------------------

validation_state = (
    "done"
    if status == "PASS"
    else "active"
)


review_state = (
    "done"
    if st.session_state.get(
        "approved",
        False,
    )
    else "active"
)


erp_state = (
    "done"
    if st.session_state.get(
        "erp_result"
    )
    else "pending"
)


render_html(
    f"""
    <div style="
        margin-top:28px;
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:14px;
        padding:17px 20px;
    ">

        <div style="
            color:#64748b;
            font-size:11px;
            font-weight:700;
            letter-spacing:0.6px;
            margin-bottom:13px;
        ">
            DOCUMENT WORKFLOW
        </div>

        <div style="
            display:flex;
            align-items:center;
            gap:18px;
            flex-wrap:wrap;
        ">

            {pipeline_step(
                1,
                "Upload",
                "done",
            )}

            <div style="
                height:1px;
                background:#e2e8f0;
                flex:0.25;
            "></div>

            {pipeline_step(
                2,
                "AI Extraction",
                "done",
            )}

            <div style="
                height:1px;
                background:#e2e8f0;
                flex:0.25;
            "></div>

            {pipeline_step(
                3,
                "Validation",
                validation_state,
            )}

            <div style="
                height:1px;
                background:#e2e8f0;
                flex:0.25;
            "></div>

            {pipeline_step(
                4,
                "Human Review",
                review_state,
            )}

            <div style="
                height:1px;
                background:#e2e8f0;
                flex:0.25;
            "></div>

            {pipeline_step(
                5,
                "ERP Sync",
                erp_state,
            )}

        </div>

    </div>
    """
)


# -------------------------------------------------------------------
# Result header
# -------------------------------------------------------------------

render_html(
    f"""
    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin:28px 0 15px;
    ">

        <div>

            <div style="
                color:#111827;
                font-size:21px;
                font-weight:750;
            ">
                {result["filename"]}
            </div>

            <div style="
                color:#64748b;
                font-size:12px;
                margin-top:3px;
            ">
                Invoice processing result
            </div>

        </div>

        <div style="
            background:#ecfdf5;
            color:#047857;
            border:1px solid #a7f3d0;
            padding:6px 11px;
            border-radius:999px;
            font-size:11px;
            font-weight:700;
        ">
            PROCESSED
        </div>

    </div>
    """
)


# -------------------------------------------------------------------
# Document + extracted information
# -------------------------------------------------------------------

preview_col, data_col = st.columns(
    [0.9, 1.35],
    gap="large",
)


with preview_col:

    render_html(
        """
        <div style="
            color:#111827;
            font-size:17px;
            font-weight:700;
            margin-bottom:9px;
        ">
            Source document
        </div>
        """
    )


    if uploaded_file.type == "application/pdf":

        render_pdf_preview(
            uploaded_file.getvalue()
        )

    else:

        st.image(
            uploaded_file,
            use_container_width=True,
        )


    st.download_button(
        "Open original document",
        data=uploaded_file.getvalue(),
        file_name=uploaded_file.name,
        mime=uploaded_file.type,
        use_container_width=True,
    )


with data_col:

    render_html(
        """
        <div style="
            color:#111827;
            font-size:17px;
            font-weight:700;
            margin-bottom:9px;
        ">
            Extracted information
        </div>
        """
    )


    info_cols = st.columns(2)


    with info_cols[0]:

        info_card(
            "Vendor",
            invoice.get("vendor"),
        )


    with info_cols[1]:

        info_card(
            "Invoice number",
            invoice.get(
                "invoice_number"
            ),
        )


    st.markdown(
        "<div style='height:10px'></div>",
        unsafe_allow_html=True,
    )


    info_cols = st.columns(2)


    with info_cols[0]:

        info_card(
            "Invoice date",
            invoice.get(
                "invoice_date"
            ),
        )


    with info_cols[1]:

        info_card(
            "Due date",
            invoice.get(
                "due_date"
            ),
        )


    st.markdown(
        "<div style='height:18px'></div>",
        unsafe_allow_html=True,
    )


    render_html(
        """
        <div style="
            color:#111827;
            font-size:15px;
            font-weight:700;
            margin-bottom:9px;
        ">
            Financial summary
        </div>
        """
    )


    financial_cols = st.columns(3)

    currency = invoice.get(
        "currency"
    ) or ""


    with financial_cols[0]:

        money_card(
            "Subtotal",
            invoice.get(
                "subtotal"
            ),
            currency,
        )


    with financial_cols[1]:

        money_card(
            "Tax",
            invoice.get(
                "tax"
            ),
            currency,
        )


    with financial_cols[2]:

        money_card(
            "Total",
            invoice.get(
                "total"
            ),
            currency,
            total=True,
        )


# -------------------------------------------------------------------
# Processing summary
# -------------------------------------------------------------------

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


render_html(
    """
    <div style="
        color:#111827;
        font-size:18px;
        font-weight:700;
        margin-bottom:12px;
    ">
        Processing summary
    </div>
    """
)


line_items = invoice.get(
    "line_items"
) or []


passed_checks = validation.get(
    "passed",
    0,
)


total_checks = validation.get(
    "total_checks",
    0,
)


summary_cols = st.columns(5)


with summary_cols[0]:

    summary_card(
        "Fields extracted",
        "10+",
    )


with summary_cols[1]:

    summary_card(
        "Line items",
        str(len(line_items)),
    )


with summary_cols[2]:

    summary_card(
        "Validation checks",
        f"{passed_checks}/{total_checks}",
    )


with summary_cols[3]:

    summary_card(
        "Validation score",
        f'{validation["score"]:.0%}',
        accent=True,
    )


with summary_cols[4]:

    if st.session_state.get(
        "erp_result"
    ):

        summary_card(
            "ERP status",
            "Synced",
        )

    elif status == "PASS":

        summary_card(
            "ERP status",
            "Ready",
        )

    else:

        summary_card(
            "ERP status",
            "Review",
        )


# -------------------------------------------------------------------
# Line items
# -------------------------------------------------------------------

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


render_html(
    """
    <div style="
        color:#111827;
        font-size:18px;
        font-weight:700;
        margin-bottom:4px;
    ">
        Line items
    </div>

    <div style="
        color:#64748b;
        font-size:12px;
        margin-bottom:12px;
    ">
        Review the quantities, prices, and amounts extracted by AI.
    </div>
    """
)


if line_items:

    line_item_rows = []


    for item in line_items:

        line_item_rows.append(
            {
                "Description": item.get(
                    "description",
                    "",
                ),
                "Quantity": item.get(
                    "quantity",
                    0,
                ),
                "Unit Price": item.get(
                    "unit_price",
                    0,
                ),
                "Amount": item.get(
                    "amount",
                    0,
                ),
            }
        )


    edited_items = st.data_editor(
        line_item_rows,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Description": st.column_config.TextColumn(
                "Description",
                width="large",
            ),
            "Quantity": st.column_config.NumberColumn(
                "Quantity",
                min_value=0,
                step=1,
            ),
            "Unit Price": st.column_config.NumberColumn(
                "Unit Price",
                min_value=0,
                step=0.01,
                format="%.2f",
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount",
                min_value=0,
                step=0.01,
                format="%.2f",
            ),
        },
        key="line_item_editor",
    )


else:

    edited_items = []

    st.info(
        "No line items were detected."
    )


if st.button(
    "Save line item changes & re-validate",
):

    updated_line_items = []


    for item in edited_items:

        updated_line_items.append(
            {
                "description": item.get(
                    "Description",
                    "",
                ),
                "quantity": item.get(
                    "Quantity",
                    0,
                ),
                "unit_price": item.get(
                    "Unit Price",
                    0,
                ),
                "amount": item.get(
                    "Amount",
                    0,
                ),
            }
        )


    updated_invoice = {
        **invoice,
        "line_items": updated_line_items,
    }


    with st.spinner(
        "Re-validating line items..."
    ):

        updated_result = revalidate_invoice(
            updated_invoice
        )


    if updated_result:

        result["invoice"] = (
            updated_result["invoice"]
        )

        result["validation"] = (
            updated_result["validation"]
        )

        st.session_state["result"] = result

        st.session_state[
            "approved"
        ] = False

        st.session_state[
            "erp_result"
        ] = None


        add_activity(
            "Line items updated and re-validated",
            "success",
        )


        st.success(
            "Line item changes saved and re-validated."
        )


        st.rerun()


# -------------------------------------------------------------------
# Human review
# -------------------------------------------------------------------

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


render_html(
    """
    <div style="
        color:#111827;
        font-size:18px;
        font-weight:700;
        margin-bottom:4px;
    ">
        Human review
    </div>

    <div style="
        color:#64748b;
        font-size:12px;
        margin-bottom:15px;
    ">
        AI output remains editable before approval.
        Any correction is checked again against the business rules.
    </div>
    """
)


with st.form("review_form"):

    col1, col2 = st.columns(2)


    with col1:

        edited_vendor = st.text_input(
            "Vendor",
            value=invoice.get(
                "vendor"
            ) or "",
        )


        edited_invoice_number = st.text_input(
            "Invoice number",
            value=invoice.get(
                "invoice_number"
            ) or "",
        )


        edited_invoice_date = st.text_input(
            "Invoice date",
            value=invoice.get(
                "invoice_date"
            ) or "",
        )


        edited_due_date = st.text_input(
            "Due date",
            value=invoice.get(
                "due_date"
            ) or "",
        )


    with col2:

        edited_currency = st.text_input(
            "Currency",
            value=invoice.get(
                "currency"
            ) or "",
        )


        edited_subtotal = st.number_input(
            "Subtotal",
            value=float(
                invoice.get(
                    "subtotal"
                ) or 0
            ),
            min_value=0.0,
        )


        edited_tax = st.number_input(
            "Tax",
            value=float(
                invoice.get(
                    "tax"
                ) or 0
            ),
            min_value=0.0,
        )


        edited_total = st.number_input(
            "Total",
            value=float(
                invoice.get(
                    "total"
                ) or 0
            ),
            min_value=0.0,
        )


    review_submitted = st.form_submit_button(
        "Save changes & re-validate",
        type="primary",
    )


if review_submitted:

    updated_invoice = {
        **invoice,
        "vendor": edited_vendor,
        "invoice_number": edited_invoice_number,
        "invoice_date": edited_invoice_date,
        "due_date": edited_due_date,
        "currency": edited_currency,
        "subtotal": edited_subtotal,
        "tax": edited_tax,
        "total": edited_total,
        "line_items": invoice.get(
            "line_items",
            [],
        ),
    }


    with st.spinner(
        "Re-validating changes..."
    ):

        updated_result = revalidate_invoice(
            updated_invoice
        )


    if updated_result:

        result["invoice"] = (
            updated_result["invoice"]
        )

        result["validation"] = (
            updated_result["validation"]
        )

        st.session_state["result"] = result

        st.session_state[
            "approved"
        ] = False

        st.session_state[
            "erp_result"
        ] = None


        add_activity(
            "Document fields updated and re-validated",
            "success",
        )


        st.success(
            "Changes saved and the document was re-validated."
        )


        st.rerun()


# -------------------------------------------------------------------
# Validation + workflow
# -------------------------------------------------------------------

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


left, right = st.columns(
    [1.3, 0.7],
    gap="large",
)


# -------------------------------------------------------------------
# Validation panel
# -------------------------------------------------------------------

with left:

    render_html(
        """
        <div style="
            color:#111827;
            font-size:18px;
            font-weight:700;
            margin-bottom:9px;
        ">
            Validation
        </div>
        """
    )


    checks_html = ""


    for check in validation["checks"]:

        if check["passed"]:

            icon = "✓"
            icon_color = "#047857"

        else:

            icon = "!"
            icon_color = "#c2410c"


        checks_html += f"""
            <div style="
                display:flex;
                gap:10px;
                padding:11px 0;
                border-bottom:1px solid #f1f5f9;
            ">

                <div style="
                    color:{icon_color};
                    font-size:16px;
                    font-weight:700;
                ">
                    {icon}
                </div>

                <div>

                    <div style="
                        color:#1e293b;
                        font-size:13px;
                        font-weight:650;
                    ">
                        {check["name"]}
                    </div>

                    <div style="
                        color:#64748b;
                        font-size:12px;
                        margin-top:3px;
                    ">
                        {check["details"]}
                    </div>

                </div>

            </div>
        """


    if status == "PASS":

        status_box = f"""
            <div style="
                background:#ecfdf5;
                border:1px solid #a7f3d0;
                color:#047857;
                border-radius:9px;
                padding:12px 14px;
                font-size:13px;
                font-weight:650;
                margin-bottom:15px;
            ">
                ✓ All validation checks passed

                <span style="float:right">
                    {validation["score"]:.0%}
                </span>
            </div>
        """

    else:

        failed_checks = sum(
            1
            for check in validation["checks"]
            if not check["passed"]
        )


        status_box = f"""
            <div style="
                background:#fff7ed;
                border:1px solid #fed7aa;
                color:#c2410c;
                border-radius:9px;
                padding:12px 14px;
                font-size:13px;
                font-weight:650;
                margin-bottom:15px;
            ">
                ⚠ Review required

                <span style="float:right">
                    {failed_checks} issue(s)
                </span>
            </div>
        """


    render_html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #e2e8f0;
            border-radius:14px;
            padding:20px;
        ">

            {status_box}

            {checks_html}

        </div>
        """
    )


# -------------------------------------------------------------------
# Workflow panel
# -------------------------------------------------------------------

with right:

    render_html(
        """
        <div style="
            color:#111827;
            font-size:18px;
            font-weight:700;
            margin-bottom:9px;
        ">
            Workflow
        </div>
        """
    )


    erp_result = (
        st.session_state.get(
            "erp_result"
        )
        or {}
    )


    approved = st.session_state.get(
        "approved",
        False,
    )


    if approved:

        workflow_title = "Document approved"

        workflow_description = (
            "The invoice has been approved and "
            "successfully sent to the downstream system."
        )

        workflow_background = "#064e3b"
        workflow_description_color = "#a7f3d0"
        workflow_title_color = "#ecfdf5"


    elif status == "PASS":

        workflow_title = "Human approval"

        workflow_description = (
            "Review the extracted information before "
            "sending it to the downstream system."
        )

        workflow_background = "#111827"
        workflow_description_color = "#94a3b8"
        workflow_title_color = "#ffffff"


    else:

        workflow_title = "Review required"

        workflow_description = (
            "Resolve the validation issues before "
            "the invoice can be approved."
        )

        workflow_background = "#111827"
        workflow_description_color = "#94a3b8"
        workflow_title_color = "#ffffff"


    render_html(
        f"""
        <div style="
            background:{workflow_background};
            color:{workflow_title_color};
            border-radius:14px;
            padding:22px;
            box-sizing:border-box;
        ">

            <div style="
                font-size:16px;
                font-weight:700;
                margin-bottom:7px;
            ">
                {workflow_title}
            </div>

            <div style="
                color:{workflow_description_color};
                font-size:12px;
                line-height:1.6;
            ">
                {workflow_description}
            </div>

        </div>
        """
    )


    if not approved:

        if status == "PASS":

            st.markdown(
                "<div style='height:10px'></div>",
                unsafe_allow_html=True,
            )


            if st.button(
                "Approve & send to ERP",
                type="primary",
                use_container_width=True,
            ):

                with st.spinner(
                    "Sending invoice to ERP..."
                ):

                    erp_response = send_to_erp(
                        invoice
                    )


                if erp_response:

                    st.session_state[
                        "approved"
                    ] = True

                    st.session_state[
                        "erp_result"
                    ] = erp_response


                    add_activity(
                        "Invoice approved and sent to ERP",
                        "success",
                    )


                    st.rerun()


    if erp_result:

        render_html(
            f"""
            <div style="
                margin-top:10px;
                background:#f0fdf4;
                border:1px solid #bbf7d0;
                padding:14px;
                border-radius:10px;
                color:#166534;
            ">

                <div style="
                    font-size:13px;
                    font-weight:700;
                    margin-bottom:5px;
                ">
                    ERP Sync Complete
                </div>

                <div style="
                    font-size:12px;
                    line-height:1.6;
                ">
                    Invoice imported successfully.
                    <br>

                    ERP Record:
                    <b>
                        {erp_result.get(
                            "erp_record_id",
                            "—",
                        )}
                    </b>
                </div>

            </div>
            """
        )


# -------------------------------------------------------------------
# Activity
# -------------------------------------------------------------------

st.markdown(
    "<hr>",
    unsafe_allow_html=True,
)


render_html(
    """
    <div style="
        color:#111827;
        font-size:18px;
        font-weight:700;
        margin-bottom:4px;
    ">
        Activity
    </div>

    <div style="
        color:#64748b;
        font-size:12px;
        margin-bottom:14px;
    ">
        Processing history for this document.
    </div>
    """
)


activity = st.session_state.get(
    "activity",
    [],
)


if activity:

    activity_html = ""


    for event in activity:

        if event["status"] == "warning":

            icon = "!"
            icon_background = "#fff7ed"
            icon_color = "#c2410c"

        else:

            icon = "✓"
            icon_background = "#ecfdf5"
            icon_color = "#047857"


        activity_html += f"""
            <div style="
                display:flex;
                gap:12px;
                padding:10px 0;
                border-bottom:1px solid #f1f5f9;
            ">

                <div style="
                    width:26px;
                    height:26px;
                    min-width:26px;
                    border-radius:50%;
                    background:{icon_background};
                    color:{icon_color};
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-size:12px;
                    font-weight:700;
                ">
                    {icon}
                </div>

                <div style="
                    color:#334155;
                    font-size:13px;
                    padding-top:4px;
                ">
                    {event["message"]}
                </div>

            </div>
        """


    render_html(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #e2e8f0;
            border-radius:14px;
            padding:12px 18px;
        ">
            {activity_html}
        </div>
        """
    )


else:

    st.caption(
        "No activity recorded yet."
    )


# -------------------------------------------------------------------
# Export
# -------------------------------------------------------------------

st.markdown(
    "<div style='height:24px'></div>",
    unsafe_allow_html=True,
)


export_data = {
    "document_id": result["document_id"],
    "filename": result["filename"],
    "invoice": invoice,
    "validation": validation,
    "approved": st.session_state.get(
        "approved",
        False,
    ),
    "erp": st.session_state.get(
        "erp_result",
        None,
    ),
    "activity": activity,
}


st.download_button(
    "Download structured JSON",
    data=json.dumps(
        export_data,
        indent=2,
    ),
    file_name="processed_invoice.json",
    mime="application/json",
    use_container_width=True,
)