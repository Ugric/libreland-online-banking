FROM python:3.12-alpine

# Set the working directory

WORKDIR /app

# Copy the current directory contents into the container at /app

COPY . /app

RUN chmod 777 /app

# Install any needed packages specified in requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container

EXPOSE 5000

# run
CMD ["python", "app.py"]

