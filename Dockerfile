# Start with a lightweight Linux + Python system
FROM python:3.9-slim

# Prevent Python from buffering outputs (so we see logs instantly)
ENV PYTHONUNBUFFERED=1

# Install the exact libraries your Agent needs
# We add seaborn/scikit-learn just in case you want advanced analytics later
RUN pip install pandas matplotlib seaborn scikit-learn

# Set the working directory inside the container
WORKDIR /workspace

# Keep the container running so the Agent can connect to it
CMD ["tail", "-f", "/dev/null"]