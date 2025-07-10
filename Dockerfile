# Gunakan image Python resmi sebagai base image.
# python:3.11-slim-buster adalah pilihan yang baik karena ringan dan berbasis Debian.
FROM python:3.11-slim-buster

# Set working directory di dalam container
WORKDIR /app

# Instal dependensi sistem yang diperlukan:
# - build-essential: Untuk kompilasi paket Python tertentu (misalnya psycopg2-binary)
# - libpq-dev: Header dan library untuk PostgreSQL (diperlukan oleh psycopg2-binary)
# - graphviz: Untuk program 'dot' yang digunakan oleh pustaka graphviz Python
# - libgraphviz-dev: Library pengembangan untuk Graphviz
# - pkg-config: Tool untuk membantu kompilasi
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Salin file requirements.txt ke working directory
COPY requirements.txt .

# --- LANGKAH DIAGNOSTIK DAN INSTALASI YANG DIPERBARUI ---
# Cetak isi requirements.txt untuk verifikasi di log build Railway
RUN echo "--- Contents of requirements.txt ---" && cat requirements.txt && echo "------------------------------------"

# Instal dependensi Python dengan mode verbose untuk detail lebih lanjut
# Gunakan python3 -m pip untuk memastikan pip yang benar digunakan
RUN python3 -m pip install --no-cache-dir --verbose -r requirements.txt

# Verifikasi instalasi Flask-Moment
RUN echo "--- Verifying Flask-Moment installation ---" && python3 -m pip show Flask-Moment || echo "Flask-Moment not found or error occurred." && echo "-----------------------------------------"

# Salin semua file aplikasi lainnya ke working directory
COPY . .

# Expose port yang akan digunakan Gunicorn
EXPOSE 8080

# Command untuk menjalankan aplikasi menggunakan Gunicorn
# Pastikan 'app:app' sesuai dengan nama file dan instance Flask Anda
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
