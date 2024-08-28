# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV DATABASE_URL=postgresql://postgres:110303@localhost/qhse_app GROQ_API_KEY='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' HUGGINGFACEHUB_API_TOKEN=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 GOOGLE_API_KEY=AIzaSyCYJFCq7gIcueWwlZsmxu3pmFFkoyMHiBc

# Run app.py when the container launches
CMD ["flask", "run"]