import streamlit as st
import requests
import os
import tempfile
import PyPDF2
import speech_recognition as sr
from fpdf import FPDF
from PIL import Image

# ---- Page Setup ----
st.set_page_config(page_title="Harsha's-grama", layout="wide")

# ---- Theme Toggle ----
theme = st.sidebar.radio("🌓 Theme", ["Light", "Dark"])
custom_css = """
<style>
body {
    background-color: %s;
    color: %s;
}
</style>
""" % ("#FFFFFF" if theme == "Light" else "#0E1117",
       "#000000" if theme == "Light" else "#FAFAFA")
st.markdown(custom_css, unsafe_allow_html=True)

# ---- Load Gemini API ----
genai_api_key = st.secrets["GEMINI_API_KEY"]
model = "gemini-1.5-flash"
genai_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={genai_api_key}"

# ---- Session State ----
if "history" not in st.session_state:
    st.session_state.history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "trigger_voice" not in st.session_state:
    st.session_state.trigger_voice = False
if "pdf_context" not in st.session_state:
    st.session_state.pdf_context = ""

# ---- Sidebar: Filters ----
st.sidebar.title("🔧 Options")
user_name = st.sidebar.text_input("👤 Your Name", "Harsha")
language = st.sidebar.radio("🌐 Choose Language:", ["English", "Telugu"])
domain = st.sidebar.selectbox("📚 Select Domain:", ["General", "Agriculture", "Health", "Schemes"])
country = st.sidebar.selectbox("🌍 Select Country", ["Select...", "India", "Nepal", "Bangladesh"])
state = st.sidebar.selectbox("🏙 Select State", ["Select...", "Telangana", "Andhra Pradesh", "Karnataka", "Tamil Nadu"])
city = st.sidebar.text_input("🏘 Enter City Name", placeholder="e.g., Medak")
village = st.sidebar.text_input("🏡 Enter Village Name", placeholder="e.g., Narsapur")

# ---- Title Block ----
st.markdown("<h1 style='text-align: center;'>🌾 PalleVignana(grama) – Village Development AI Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Ask me anything about government schemes, agriculture, health, or your local village concerns.</p>", unsafe_allow_html=True)

# ---- Upload PDF ----
st.markdown("### 📄 Upload a document (PDF)")
uploaded_pdf = st.file_uploader("Upload a PDF", type="pdf")
if uploaded_pdf:
    def extract_text_from_pdf(uploaded_file):
        text = ''
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text

    st.session_state.pdf_context = extract_text_from_pdf(uploaded_pdf)
    st.success("✅ PDF uploaded!")

# ---- Camera Input ----
st.markdown("### 📸 Camera Capture (Optional)")
use_camera = st.checkbox("Enable Camera Capture")
camera_image = None
image_path = ""
if use_camera:
    camera_image = st.camera_input("Take a picture")
    if camera_image:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(camera_image.getbuffer())
            image_path = temp_file.name
        st.image(Image.open(camera_image), caption="Captured Image", use_column_width=True)
        st.success("✅ Image captured!")

# ---- Input Box ----
with st.form(key="chat_form"):
    col1, col2, col3 = st.columns([5, 1, 1])
    with col1:
        user_input = st.text_input("Ask your question here:", key="user_input_input", value=st.session_state.user_input)
    with col2:
        submit_clicked = st.form_submit_button("Submit")
    with col3:
        voice_clicked = st.form_submit_button("🎤", help="Use Voice Input")

# ---- Voice Input Logic ----
def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙 Listening...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "❌ Could not understand audio."
    except sr.RequestError:
        return "❌ Voice recognition error."

if st.session_state.trigger_voice:
    st.session_state.user_input = recognize_speech()
    st.session_state.trigger_voice = False
    st.rerun()

if voice_clicked:
    st.session_state.trigger_voice = True
    st.rerun()

# ---- Gemini API ----
def query_gemini_api(prompt):
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    try:
        response = requests.post(genai_api_url, json=payload)
        response.raise_for_status()
        res = response.json()
        candidates = res.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        else:
            return "❌ No response from Gemini API."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ---- Handle Submit ----
if submit_clicked:
    if not user_input and not st.session_state.pdf_context and not image_path:
        st.warning("⚠️ Please enter a question, upload a PDF, or take a photo.")
    else:
        lang_instruction = f"Please respond in {language}.\n"
        location_context = (
            f"This query is related to:\n"
            f"- Country: {country}\n"
            f"- State: {state}\n"
            f"- City: {city}\n"
            f"- Village: {village}\n\n"
        )

        pdf_context = f"📄 A document was uploaded. Content:\n{st.session_state.pdf_context}\n\n" if st.session_state.pdf_context else ""
        image_context = "📸 A photo was captured. Consider it as reference.\n\n" if image_path else ""
        user_question = f"{user_name}: {user_input}\n\n" if user_input else ""

        full_prompt = f"{lang_instruction}{location_context}{pdf_context}{image_context}{user_question}AI:"

        response_text = query_gemini_api(full_prompt)

        if user_input:
            st.session_state.history.append((user_name, user_input))
        if st.session_state.pdf_context:
            st.session_state.history.append(("📄 PDF", "PDF uploaded."))
        if image_path:
            st.session_state.history.append(("📸 Photo", "Photo captured."))
        st.session_state.history.append(("PalleVignana", response_text))
        st.session_state.user_input = ""

# ---- Chat Display ----
for sender, msg in st.session_state.history:
    if sender in [user_name, "📄 PDF", "📸 Photo"]:
        st.chat_message("user").markdown(f"**{sender}**: {msg}")
    else:
        st.chat_message("assistant").markdown(msg)

# ---- Export Chat ----
if st.session_state.history:
    if st.button("📥 Export Chat as PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for sender, msg in st.session_state.history:
            pdf.multi_cell(0, 10, f"{sender}: {msg}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            pdf.output(f.name)
            st.download_button("Download Chat", data=open(f.name, "rb").read(), file_name="PalleVignana_Chat.pdf")
