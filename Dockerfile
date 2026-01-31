FROM python:3.11-slim

# Install Rust
RUN apt-get update && \
    apt-get install -y curl build-essential && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . $HOME/.cargo/env && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir maturin

# Copy Rust code and build
COPY rust/ ./rust/
RUN cd rust && maturin build --release && \
    pip install target/wheels/*.whl && \
    cd .. && rm -rf rust/target

# Copy application code
COPY bot/ ./bot/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create directories for logs and data
RUN mkdir -p logs data

# Environment variables (override these at runtime)
ENV TELEGRAM_BOT_TOKEN=""
ENV TELEGRAM_CHAT_ID=""

# Run the bot
CMD ["python", "-m", "bot.main", "config/config.yaml"]
