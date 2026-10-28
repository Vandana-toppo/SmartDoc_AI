import os
import json
import re

import streamlit as st
import pymupdf
from dotenv import load_dotenv
from google import genai


# -------------------- CONFIGURATION --------------------

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.5-flash-lite"

st.set_page_config(
    page_title="SmartDocs AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------- CUSTOM CSS --------------------

def load_css():
    try:
        with open("style.css", "r", encoding="utf-8") as file:
            css = file.read()
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        pass


load_css()


# -------------------- SESSION STATE --------------------

defaults = {
    "document_text": "",
    "document_name": "",
    "summary": "",
    "practice_questions": [],
    "practice_topic": "",
    "practice_answers": {},
    "practice_submitted": False,
    "weak_topics": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------- AI HELPER --------------------

def ask_ai(prompt):
    """Send a prompt to Gemini and return its response."""
    if not api_key:
        raise ValueError(
            "API key missing. Check GEMINI_API_KEY in your .env file."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    if not response.text:
        raise ValueError("AI returned an empty response.")

    return response.text


def extract_json(text):
    """Extract JSON even if the AI wraps it in a code block."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def show_ai_error(error):
    st.error("AI could not complete the request.")
    st.caption(str(error))


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.title("📚 SmartDocs AI")
    st.caption("Your personal document learning assistant.")
    st.divider()

    st.markdown("### Your Workspace")
    st.write("📄 Upload and understand PDFs")
    st.write("💬 Ask questions")
    st.write("🧠 Practise what you learn")
    st.write("🎯 Revise weak topics")

    if st.session_state.document_name:
        st.divider()
        st.caption("Current document")
        st.write(st.session_state.document_name)


# -------------------- HEADER --------------------

st.title("📚 SmartDocs AI")
st.markdown(
    "### Your Documents. Your AI. Your Smart Assistant."
)
st.write(
    "Upload a document, understand difficult topics, "
    "test your knowledge, and revise what you find difficult."
)

st.divider()


# -------------------- PDF UPLOAD --------------------

uploaded_file = st.file_uploader(
    "📄 Upload your PDF document",
    type=["pdf"],
    help="Choose a text-based PDF to get started.",
)

if uploaded_file is not None:
    if (
        st.session_state.document_name != uploaded_file.name
        or not st.session_state.document_text
    ):
        try:
            pdf = pymupdf.open(
                stream=uploaded_file.getvalue(),
                filetype="pdf",
            )

            extracted_text = ""

            for page in pdf:
                extracted_text += page.get_text() + "\n"

            pdf.close()

            if not extracted_text.strip():
                st.warning(
                    "No readable text found. "
                    "This PDF may contain scanned images."
                )
            else:
                st.session_state.document_text = extracted_text
                st.session_state.document_name = uploaded_file.name

                # Clear results belonging to the previous document.
                st.session_state.summary = ""
                st.session_state.practice_questions = []
                st.session_state.practice_answers = {}
                st.session_state.practice_submitted = False
                st.session_state.weak_topics = []

                st.success("PDF text extracted successfully!")

        except Exception as error:
            st.error("Could not read this PDF.")
            st.caption(str(error))


document_text = st.session_state.document_text

if document_text:
    st.caption(
        f"Loaded: {st.session_state.document_name} "
        f"• {len(document_text):,} characters"
    )

    with st.expander("👀 Preview extracted text"):
        st.text(document_text[:8000])

    tabs = st.tabs([
        "📝 AI Summary",
        "💬 Ask Document",
        "📖 Explain Topic",
        "🎯 Practice Test",
        "🔁 Weak Topic Revision",
    ])

    # -------------------- TAB 1: SUMMARY --------------------

    with tabs[0]:
        st.subheader("📝 Understand the document")

        st.write(
            "Get a simple summary with important points "
            "from your uploaded PDF."
        )

        if st.button(
            "✨ Generate AI Summary",
            key="generate_summary",
        ):
            prompt = (
                "Summarize the following document in very simple English. "
                "Use a clear title, short paragraphs, bullet points, "
                "important definitions, and key takeaways. "
                "Do not invent information not supported by the document.\n\n"
                + document_text[:25000]
            )

            try:
                with st.spinner("Preparing your summary..."):
                    st.session_state.summary = ask_ai(prompt)
            except Exception as error:
                show_ai_error(error)

        if st.session_state.summary:
            st.markdown("### Your Summary")
            st.markdown(st.session_state.summary)

    # -------------------- TAB 2: ASK DOCUMENT --------------------

    with tabs[1]:
        st.subheader("💬 Ask Your Document")

        st.write(
            "Ask a question about the uploaded PDF. "
            "The answer should be based on the document."
        )

        question = st.text_input(
            "What would you like to know?",
            key="document_question",
            placeholder="Example: Explain the main objectives.",
        )

        if st.button(
            "🔍 Get Answer",
            key="ask_document",
        ):
            if not question.strip():
                st.warning("Please enter a question first.")
            else:
                prompt = (
                    "Answer the user's question using the document "
                    "provided below. Explain in simple English. "
                    "If the answer is not present in the document, "
                    "say so clearly instead of guessing.\n\n"
                    "DOCUMENT:\n"
                    + document_text[:25000]
                    + "\n\nQUESTION:\n"
                    + question
                )

                try:
                    with st.spinner("Finding the answer..."):
                        answer = ask_ai(prompt)

                    st.markdown("### Answer")
                    st.markdown(answer)

                except Exception as error:
                    show_ai_error(error)

    # -------------------- TAB 3: EXPLAIN TOPIC --------------------

    with tabs[2]:
        st.subheader("📖 Explain a difficult topic")

        topic = st.text_input(
            "Enter the topic",
            key="explain_topic",
            placeholder="Example: Neural Networks",
        )

        explanation_style = st.selectbox(
            "Choose explanation style",
            [
                "Very Simple English",
                "Detailed Explanation",
                "Exam-Ready Answer",
                "Example-Based Explanation",
            ],
            key="explanation_style",
        )

        if st.button(
            "📘 Explain Topic",
            key="explain_topic_button",
        ):
            if not topic.strip():
                st.warning("Please enter a topic.")
            else:
                prompt = (
                    "Explain the topic: "
                    + topic
                    + "\nExplanation style: "
                    + explanation_style
                    + "\nUse the following document as the main reference. "
                    "If the topic is not covered, clearly distinguish "
                    "general knowledge from information in the document. "
                    "Use headings and examples where useful.\n\n"
                    "DOCUMENT:\n"
                    + document_text[:20000]
                )

                try:
                    with st.spinner("Preparing your explanation..."):
                        explanation = ask_ai(prompt)

                    st.markdown("### Topic Explanation")
                    st.markdown(explanation)

                except Exception as error:
                    show_ai_error(error)

    # -------------------- TAB 4: PRACTICE TEST --------------------

    with tabs[3]:
        st.subheader("🎯 Test your understanding")

        st.write(
            "Generate multiple-choice questions, use hints, "
            "and check your answers."
        )

        practice_topic = st.text_input(
            "Topic to practise",
            key="practice_topic_input",
            placeholder="Example: Artificial Neural Networks",
        )

        col1, col2 = st.columns(2)

        with col1:
            question_count = st.selectbox(
                "Number of questions",
                [3, 5, 10],
                index=1,
                key="question_count",
            )

        with col2:
            difficulty = st.selectbox(
                "Difficulty",
                ["Easy", "Medium", "Hard"],
                key="practice_difficulty",
            )

        if st.button(
            "🎯 Generate Practice Questions",
            key="generate_practice",
        ):
            selected_topic = (
                practice_topic.strip()
                or "Important topics from the document"
            )

            prompt = f"""
Create exactly {question_count} multiple-choice questions
about: {selected_topic}

Difficulty: {difficulty}

Use this document as the main source:
{document_text[:20000]}

Return ONLY a valid JSON array. Do not use Markdown fences.

Every array item must follow this format:
{{
  "question": "Question text",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "answer": 0,
  "explanation": "Why the correct answer is correct",
  "topic": "Short topic name"
}}

Rules:
- answer must be an integer from 0 to 3.
- There must be exactly four options per question.
- Questions must test understanding, not only memorisation.
- All questions and answers must be factually consistent.
- Do not include the correct answer in the question text.
"""

            try:
                with st.spinner("Creating your practice test..."):
                    result = ask_ai(prompt)
                    questions = extract_json(result)

                if not isinstance(questions, list) or not questions:
                    raise ValueError("The AI did not return a valid question list.")

                valid_questions = []

                for q in questions:
                    if not isinstance(q, dict):
                        continue

                    options = q.get("options", [])
                    answer = q.get("answer")

                    if (
                        isinstance(q.get("question"), str)
                        and isinstance(options, list)
                        and len(options) == 4
                        and isinstance(answer, int)
                        and not isinstance(answer, bool)
                        and 0 <= answer < 4
                    ):
                        q.setdefault("explanation", "Review the topic again.")
                        q.setdefault("topic", selected_topic)
                        valid_questions.append(q)

                if not valid_questions:
                    raise ValueError("No valid questions were returned.")

                st.session_state.practice_questions = valid_questions
                st.session_state.practice_topic = selected_topic
                st.session_state.practice_answers = {}
                st.session_state.practice_submitted = False

                st.success(
                    f"{len(valid_questions)} questions are ready!"
                )

            except Exception as error:
                show_ai_error(error)

        questions = st.session_state.practice_questions

        if questions:
            st.divider()
            st.markdown(
                f"### Practice Test: {st.session_state.practice_topic}"
            )

            # Questions are outside a form so hint buttons work independently.
            for i, q in enumerate(questions):
                st.markdown(f"**Question {i + 1}:** {q['question']}")

                with st.expander("💡 Show Hint"):
                    if st.button(
                        "Get Hint",
                        key=f"hint_{i}",
                    ):
                        hint_prompt = (
                            "Give one short, helpful hint for this "
                            "multiple-choice question. Do not reveal "
                            "the answer or identify the correct option.\n\n"
                            "Question: "
                            + q["question"]
                            + "\nOptions: "
                            + ", ".join(q["options"])
                        )

                        try:
                            with st.spinner("Preparing hint..."):
                                hint = ask_ai(hint_prompt)
                            st.info(hint)
                        except Exception as error:
                            show_ai_error(error)

                selected = st.radio(
                    "Choose your answer:",
                    options=range(4),
                    format_func=lambda x, opts=q["options"]: opts[x],
                    key=f"practice_answer_{i}",
                    index=None,
                )

                st.session_state.practice_answers[i] = selected
                st.divider()

            if st.button(
                "✅ Submit Test",
                key="submit_practice_test",
            ):
                unanswered = [
                    i
                    for i in range(len(questions))
                    if st.session_state.practice_answers.get(i) is None
                ]

                if unanswered:
                    st.warning(
                        f"Please answer all questions. "
                        f"{len(unanswered)} question(s) remain unanswered."
                    )
                else:
                    st.session_state.practice_submitted = True

            if st.session_state.practice_submitted:
                answers = st.session_state.practice_answers

                score = sum(
                    answers.get(i) == q["answer"]
                    for i, q in enumerate(questions)
                )

                total = len(questions)

                st.markdown("### 📊 Your Test Result")
                st.subheader(f"Your Score: {score}/{total}")
                st.progress(score / total)

                st.write(
                    f"Accuracy: {round((score / total) * 100)}%"
                )

                weak_topics = []

                for i, q in enumerate(questions):
                    chosen = answers.get(i)
                    correct = q["answer"]
                    is_correct = chosen == correct

                    with st.expander(
                        f"Question {i + 1} — "
                        f"{'✅ Correct' if is_correct else '❌ Review'}"
                    ):
                        st.write(
                            "Your answer: "
                            + (
                                q["options"][chosen]
                                if chosen is not None
                                else "Not answered"
                            )
                        )

                        st.write(
                            "Correct answer: "
                            + q["options"][correct]
                        )

                        st.write("Explanation: " + q["explanation"])

                    if not is_correct:
                        weak_topics.append(
                            q.get("topic", st.session_state.practice_topic)
                        )

                st.session_state.weak_topics = list(dict.fromkeys(weak_topics))

                if score == total:
                    st.success("Excellent! You answered every question correctly.")
                elif score / total < 0.6:
                    st.info(
                        "Revise the topics you found difficult, "
                        "then try another practice test."
                    )
                else:
                    st.info(
                        "Good effort! Review the incorrect answers "
                        "to strengthen your understanding."
                    )

    # -------------------- TAB 5: WEAK TOPIC REVISION --------------------

    with tabs[4]:
        st.subheader("🔁 Revise your weak topics")

        st.write(
            "After submitting a practice test, topics with incorrect "
            "answers will appear here for revision."
        )

        weak_topics = st.session_state.weak_topics

        if not weak_topics:
            st.info(
                "Complete and submit a practice test first. "
                "Any topics you find difficult will appear here."
            )
        else:
            st.markdown("### Topics to review")

            for weak_topic in weak_topics:
                st.write(f"📌 {weak_topic}")

            revision_topic = st.selectbox(
                "Choose a topic to revise",
                weak_topics,
                key="revision_topic",
            )

            if st.button(
                "🔁 Generate Revision Notes",
                key="generate_revision",
            ):
                prompt = (
                    "Create revision notes for this weak topic: "
                    + revision_topic
                    + ". Use very simple English. Include the core idea, "
                    "important definitions, a simple example, common "
                    "mistakes, and three quick revision points. "
                    "Use the uploaded document as the main reference. "
                    "Do not invent document-specific facts.\n\n"
                    "DOCUMENT:\n"
                    + document_text[:20000]
                )

                try:
                    with st.spinner("Preparing revision notes..."):
                        revision = ask_ai(prompt)

                    st.markdown("### Your Revision Notes")
                    st.markdown(revision)

                except Exception as error:
                    show_ai_error(error)

else:
    st.info(
        "👆 Upload a PDF above to start using SmartDocs AI."
    )


# -------------------- FOOTER --------------------

st.divider()
st.caption("SmartDocs AI | Learn smarter, not harder.")