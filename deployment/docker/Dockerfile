FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user:user dashboard/ dashboard/
COPY --chown=user:user assistant/ assistant/
COPY --chown=user:user deployment/ deployment/
USER user
ENV HOME=/home/user PYTHONUNBUFFERED=1 ENABLE_LIVE_ASSISTANT=false
EXPOSE 7860
CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=7860", "--browser.gatherUsageStats=false"]
