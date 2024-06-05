FROM python:3.9

# Install Supervisor and other dependencies
RUN apt-get update && \
    apt-get install -y screen && \
    # apt-get install -y supervisor && \
    rm -rf /var/lib/apt/lists/*
    
WORKDIR /app/backend

# Copy application and configuration files
COPY . /app/backend

# COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the necessary ports
EXPOSE 8000

# Run migrations, start Django, and Supervisor
CMD ["sh", "-c", "python3 manage.py makemigrations && python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8000"]
