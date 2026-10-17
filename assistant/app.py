"""Run: .venv/bin/streamlit run assistant/app.py"""
import sys
import os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
from assistant.sql_agent import Agent, AssistantError
from assistant.budget import BudgetError

st.set_page_config(page_title='Medicare claims assistant',layout='wide')
if os.getenv('ENABLE_LIVE_ASSISTANT', 'false').lower() != 'true':
    from assistant.demo import render
    render()
    st.stop()
st.title('Medicare claims assistant')
st.caption('Historical synthetic data · 2009–2010 · Medical payments exclude Rx gross cost')
sample=st.selectbox('Sample',[1,2])
year=st.selectbox('Performance year',[2009,2010])
method=st.selectbox('Default attribution method',['A_visits','B_allowed'])
st.session_state.setdefault('questions',0)
st.caption(f"{st.session_state.questions}/10 questions used in this session. Explicit question scope overrides defaults.")
with st.form('question'):
    question=st.text_area('Question',placeholder='Which 5 providers had the highest readmission rate?',max_chars=1500)
    submitted=st.form_submit_button('Ask',disabled=st.session_state.questions>=10)
if submitted and question.strip():
    st.session_state.questions+=1
    try:
        with st.spinner('Checking definitions, querying and explaining…'):
            st.session_state.result=Agent().ask(question,sample,year,method)
    except (AssistantError,BudgetError) as error:
        st.session_state.pop('result',None)
        st.error(str(error))
    except Exception:
        st.session_state.pop('result',None)
        st.error('Assistant unavailable. Check local configuration and logs; no answer was generated.')
if 'result' in st.session_state:
    result=st.session_state.result
    st.write(result['answer'])
    st.write('Assumptions',result['assumptions'])
    if result['sql']:
        st.code(result['sql'],language='sql')
        st.dataframe(result['rows'])
    with st.expander('Request usage'):
        st.json(result['usage'])
