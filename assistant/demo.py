"""Public demo: verified static aggregate results; no network or LLM calls."""
import json
from pathlib import Path
import streamlit as st

def render():
    results=json.loads((Path(__file__).resolve().parents[1]/'deployment/demo_results.json').read_text())
    st.title('Assistant demo')
    st.warning('Verified static examples — not live AI. Buttons display saved SQL results from a separate 1,000-member Sample 1 fixture. Dashboard pages cover full Samples 1 and 2.')
    for item in results['examples']:
        if st.button(item['question'],key=item['id']):
            st.session_state['demo_result']=item
    if 'demo_result' in st.session_state:
        item=st.session_state['demo_result']
        st.subheader(item['question'])
        st.caption(results['scope']+' · Verified '+results['verified_at'])
        st.dataframe(item['rows'])
        st.code(item['sql'],language='sql')
    st.text_input('Ask your own question',disabled=True,placeholder='Live AI is unavailable in this public demo')
    st.info('Live AI is not available in this public demo. These examples use saved verified results; no API calls are made. Readmission rates are observed, not risk-adjusted; medical payments exclude Rx gross cost.')
