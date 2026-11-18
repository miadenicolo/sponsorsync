import os, csv
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
APP_DIR = Path(__file__).parent
BRANDS_FILE = APP_DIR / "sample_brands.csv"

st.set_page_config(page_title="SponsorSync", page_icon="🤝", layout="wide")
st.markdown("""
<style>
.main-title {color:#173E35;font-size:2.5rem;font-weight:750}
.subtitle {color:#62736c;margin-top:-12px}
div[data-testid="stMetric"] {background:#eef4f1;padding:12px;border-radius:12px}
</style>
""", unsafe_allow_html=True)

def api_key():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        try: key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
        except Exception: key = ""
    return key

def ai_call(prompt):
    if not api_key():
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file or Streamlit secrets.")
    client = OpenAI(api_key=api_key())
    result = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
        instructions=(
            "You are SponsorSync, helping student organizations, nonprofits, and small event planners "
            "identify potential sponsorship partners. Use only supplied brand information. Never claim "
            "a brand is accepting sponsorships or has expressed interest unless explicitly verified. "
            "Do not invent facts, contacts, campaigns, budgets, or availability. Clearly label inferences."
        ),
        input=prompt,
    )
    return result.output_text.strip()

def brand_records():
    with BRANDS_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

st.markdown('<div class="main-title">🤝 SponsorSync</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered brand partnership matching</div>', unsafe_allow_html=True)
st.caption("Prototype by Mia Denicolo and Grace Warner")
with st.sidebar:
    st.header("AI connection")
    if api_key(): st.success("API key detected")
    else:
        st.warning("API key not configured")
        st.markdown("[Create an API key](https://platform.openai.com/api-keys)")
        st.caption("Add it to your local .env file. Never paste it into source code.")
    st.caption(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-5.5')}")

match_tab, email_tab, info_tab = st.tabs(["🔎 Find sponsors", "✉️ Create outreach", "ℹ️ How it works"])

with match_tab:
    st.subheader("Tell us about your event")
    with st.form("event_form"):
        c1, c2 = st.columns(2)
        with c1:
            event_name = st.text_input("Organization / event name", "University Wellness Festival")
            event_type = st.selectbox("Event category", ["Health & Wellness","Sports & Fitness","Business & Networking","Arts & Entertainment","Education","Community & Charity","Other"])
            location = st.text_input("Location", "Miami, Florida")
            attendance = st.number_input("Expected attendance", min_value=1, value=300, step=25)
        with c2:
            audience = st.text_input("Target audience", "College students ages 18–24")
            budget = st.text_input("Sponsorship budget / request", "$2,000 plus product samples")
            needs = st.text_area("What support are you seeking?", "Financial sponsorship, product samples, and event activations")
        description = st.text_area("Describe your event", "A campus wellness festival promoting fitness, healthy lifestyles, and self-care through interactive activities.")
        submitted = st.form_submit_button("✨ Generate AI sponsor matches", type="primary", use_container_width=True)

    if submitted:
        try:
            brands = brand_records()
            brand_text = "\n".join(
                f"- {b['brand_name']}: category={b['category']}; description={b['description']}; "
                f"documented_interests={b['documented_interests']}; verification={b['verification_status']}"
                for b in brands
            )
            prompt = f"""
Rank up to five potential sponsors for this event.

EVENT
Name: {event_name}
Category: {event_type}
Location: {location}
Attendance: {attendance}
Audience: {audience}
Sponsorship request: {budget}
Needs: {needs}
Description: {description}

BRAND DATABASE
{brand_text}

For each match provide: rank and exact database brand name; qualitative fit (High/Medium/Low, no invented percentages);
two reasons tied to supplied facts; one possible activation; and information to verify before outreach.
Only recommend brands in the database. Do not imply current sponsorship availability. If no strong match exists, say so.
End by noting that recommendations are preliminary and require human review.
"""
            with st.spinner("SponsorSync is analyzing your event and brand database..."):
                st.session_state["matches"] = ai_call(prompt)
                st.session_state["event_context"] = {
                    "event_name": event_name, "event_type": event_type, "location": location,
                    "attendance": attendance, "audience": audience, "budget": budget,
                    "needs": needs, "description": description,
                }
            st.success("Live AI sponsor matching completed.")
        except Exception as e:
            st.error(f"Could not generate matches: {e}")

    if st.session_state.get("matches"):
        st.divider()
        st.subheader("AI-generated sponsor recommendations")
        st.markdown(st.session_state["matches"])
        st.info("These are preliminary AI suggestions based on the included database, not confirmed sponsorship opportunities. Verify details and availability.")

with email_tab:
    st.subheader("Personalized sponsorship outreach")
    if not st.session_state.get("matches"):
        st.info("Generate sponsor matches first in the Find sponsors tab.")
    else:
        ctx = st.session_state["event_context"]
        with st.form("email_form"):
            brand = st.text_input("Brand to contact")
            recipient = st.text_input("Recipient / team", "Brand Partnerships Team")
            tone = st.selectbox("Email tone", ["Professional and friendly","Concise and direct","Enthusiastic"])
            extra = st.text_area("Additional details to include", "We can provide event promotion and social media visibility.")
            send = st.form_submit_button("✉️ Generate outreach email", type="primary", use_container_width=True)
        if send:
            if not brand.strip():
                st.warning("Enter a brand name from your recommendations.")
            else:
                prompt = f"""
Write a personalized sponsorship inquiry email. Do not invent facts or claim the brand expressed interest.
Use placeholders for unknown contact details.

EVENT DETAILS: {ctx}
AI MATCH RESULTS: {st.session_state['matches']}
BRAND: {brand}
RECIPIENT: {recipient}
TONE: {tone}
ADDITIONAL DETAILS: {extra}

Include a subject line, concise introduction, evidence-based reason the event may fit the brand,
sponsorship request, potential value offered, and a low-pressure call to action. Mark details to verify.
"""
                try:
                    with st.spinner("Generating your email with AI..."):
                        st.session_state["email"] = ai_call(prompt)
                    st.success("AI email draft generated.")
                except Exception as e:
                    st.error(f"Could not generate email: {e}")
        if st.session_state.get("email"):
            edited = st.text_area("Review and edit before sending", st.session_state["email"], height=350)
            st.download_button("Download email draft", edited, "sponsorsync_outreach.txt", "text/plain", use_container_width=True)

with info_tab:
    st.subheader("System architecture")
    st.markdown("""
    1. **User interface:** Streamlit collects event details.
    2. **Application logic:** Python validates inputs and prepares the AI request.
    3. **Data:** A CSV file stores sample brand descriptions and documented interests.
    4. **AI model:** OpenAI Responses API compares the event with supplied brand records.
    5. **Output:** Ranked recommendations, fit explanations, and editable outreach drafts.
    """)
    st.warning("The included sample brand records are fictional placeholders for testing. Replace them with researched, documented brand information before evaluating real-world fit.")
    st.markdown("**Safeguards:** The AI is instructed not to invent sponsorship availability or brand interest. A person must review recommendations. Keep the API key private and avoid entering confidential information.")

st.divider()
st.caption("SponsorSync | AI Innovation Group Project | Mia Denicolo and Grace Warner")
