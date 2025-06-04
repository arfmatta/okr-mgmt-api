# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (everything in the ./app directory)
# into the container at /app/app
# So, if you have app/main.py locally, it becomes /app/app/main.py in container
COPY ./app ./app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable to tell uvicorn where to find the app
# (Not strictly necessary if CMD specifies app.main:app, but can be good practice)
# ENV MODULE_NAME="app.main"
# ENV VARIABLE_NAME="app"

# Run app.main:app when the container launches
# Use 0.0.0.0 to make it accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
