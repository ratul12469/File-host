# Use a lightweight Python base image
FROM python:3.11-slim

# Install system dependencies (FFmpeg is critical for your bot)
# We also clean up the apt cache to keep the image size small
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (this helps Docker cache the installation)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot's files into the container
COPY . .

# Expose the port your aiohttp server uses (for Render/Koyeb health checks)
EXPOSE 10000

# Command to start the bot
CMD ["python", "bot.py"]
