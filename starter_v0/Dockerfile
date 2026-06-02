FROM python:3.10-slim

# Ngăn Python tạo file pyc và đảm bảo logs được in ngay lập tức
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501

WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (git cần cho Streamlit/GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt python dependencies trước để tận dụng Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Expose port mặc định (Render sẽ tự động ghi đè qua biến PORT)
EXPOSE 8501

# Khởi chạy ứng dụng Streamlit
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0"]
