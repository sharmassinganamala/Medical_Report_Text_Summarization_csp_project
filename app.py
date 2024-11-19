from flask import Flask, request, render_template, send_file
import re
import PyPDF2
import io
from transformers import pipeline

app = Flask(__name__)

# Initialize the summarization pipeline
summarizer = pipeline("summarization")

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(reader.pages)):
        text += reader.pages[page_num].extract_text()
    return text

# Function to check if the uploaded file is a medical report
def is_medical_report(text):
    medical_keywords = ["Patient Name", "Physician", "Diagnosis", "Prescription", "Report", "Findings", "Recommendations"]
    return any(keyword in text for keyword in medical_keywords)

# Function to summarize text
def summarize_text(text, max_length=150, min_length=40):
    if len(text.split()) < min_length:
        return "Text too short for summarization."
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text']

# Function to extract patient and physician information
def extract_patient_physician_info(text):
    patient_name = None
    physician_name = None
    patient_match = re.search(r'Patient Name:\s*(.*)', text)
    physician_match = re.search(r'Physician:\s*(.*)', text)
    if patient_match:
        patient_name = patient_match.group(1).strip()
    if physician_match:
        physician_name = physician_match.group(1).strip()
    return patient_name, physician_name

# Function to extract report sections
def extract_report_sections(text):
    sections = re.findall(r'\b(?:Diagnosis|Prescription|Lab Results|Imaging|Recommendations)\b', text)
    return sections if sections else ["No specific report sections identified."]

# Function to get precautions based on the report
def get_precautions(text):
    precautions = []
    if re.search(r'\bhigh blood pressure\b', text, re.IGNORECASE):
        precautions.append("Maintain a low-sodium diet and monitor blood pressure regularly.")
    if re.search(r'\bdiabetes\b', text, re.IGNORECASE):
        precautions.append("Monitor blood sugar levels, exercise regularly, and follow a balanced diet.")
    if re.search(r'\bfracture\b|\bbroken bone\b', text, re.IGNORECASE):
        precautions.append("Rest, avoid weight-bearing activities, and follow up with a specialist.")
    if re.search(r'\bheart\b|\bcardiovascular\b', text, re.IGNORECASE):
        precautions.append("Limit physical exertion, avoid stress, and follow a heart-healthy diet.")
    if re.search(r'\ballergy\b', text, re.IGNORECASE):
        precautions.append("Avoid allergens and keep medications accessible.")
    if not precautions:
        precautions.append("General advice: Follow your physician's recommendations carefully.")
    return precautions

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    if file and file.filename.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file)

        if not is_medical_report(extracted_text):
            return "Uploaded file does not appear to be a medical report."

        patient_name, physician_name = extract_patient_physician_info(extracted_text)
        summary = summarize_text(extracted_text)
        sections = extract_report_sections(extracted_text)
        precautions = get_precautions(extracted_text)

        return render_template(
            'summary.html',
            patient_name=patient_name,
            physician_name=physician_name,
            summary=summary,
            sections=sections,
            precautions=precautions
        )

    return "Invalid file type. Please upload a PDF."

# Route to download the summary
@app.route('/download', methods=['GET'])
def download_summary():
    summary_content = request.args.get('summary')
    patient_info = request.args.get('patient_info', "No Patient Info Provided")
    precautions = request.args.get('precautions', "No Precautions Provided")
    
    file_content = f"Patient Info:\n{patient_info}\n\nSummary:\n{summary_content}\n\nPrecautions:\n{precautions}"
    return send_file(
        io.BytesIO(file_content.encode('utf-8')),
        as_attachment=True,
        download_name='summary.txt',
        mimetype='text/plain'
    )

if __name__ == '__main__':
    app.run(debug=True)
