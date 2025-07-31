# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY pyproject.toml .

# Install any needed packages specified in pyproject.toml
RUN pip install --no-cache-dir .

# Copy the rest of the application's code into the container
COPY src/ /app/src

# Make port 8002 available to the world outside this container
EXPOSE 8002

# Run main.py when the container launches
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"] 