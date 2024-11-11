# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY pyproject.toml .
COPY main.py .
COPY components/ components/
COPY utils/ utils/
COPY .streamlit/ .streamlit/

# Install dependencies
RUN pip install --no-cache-dir streamlit pandas numpy plotly

# Expose port 5000
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run streamlit
CMD ["streamlit", "run", "main.py", "--server.port", "5000"]
