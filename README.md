# data-mining-relokasi-rumah
Fitur
Klasifikasi C4.5: Menerapkan algoritma pohon keputusan C4.5 untuk klasifikasi data.

Manajemen Dataset: CRUD (Create, Read, Update, Delete) data dataset bencana.

Impor CSV: Kemampuan untuk mengimpor data dataset dari file CSV.

Manajemen Atribut: CRUD atribut dan nilai-nilai atribut yang digunakan dalam model.

Visualisasi Pohon Keputusan: Menampilkan pohon keputusan yang dihasilkan oleh model C4.5.

Halaman Perhitungan: Ringkasan informasi model dan pentingnya fitur.

Form Klasifikasi/Prediksi Publik: Antarmuka sederhana untuk masyarakat umum melakukan klasifikasi/prediksi tanpa login.

Sistem Autentikasi: Login admin untuk akses ke fitur manajemen data.

Database Fleksibel: Mendukung SQLite untuk pengembangan lokal dan PostgreSQL untuk deployment.

Teknologi yang Digunakan
Backend: Python 3.11+

Framework Web: Flask

Database ORM: Flask-SQLAlchemy

Database: SQLite (lokal), PostgreSQL (produksi)

Machine Learning: scikit-learn

Data Manipulation: pandas

Visualisasi Pohon: graphviz

Manajemen Waktu: Flask-Moment

Server WSGI: Gunicorn (untuk deployment)

Containerization: Docker

Instalasi Lokal
Ikuti langkah-langkah ini untuk menjalankan aplikasi di lingkungan pengembangan lokal Anda.

Prasyarat
Python 3.11 atau lebih tinggi terinstal.

pip (manajer paket Python) terinstal.

(Opsional, jika ingin menggunakan PostgreSQL lokal) PostgreSQL server terinstal dan berjalan.

Langkah-langkah Instalasi
Clone Repositori:

git clone https://github.com/Rosemadina7424/data-mining-relokasi-rumah.git
cd data-mining-relokasi-rumah



Buat dan Aktifkan Virtual Environment:
Sangat disarankan untuk menggunakan virtual environment untuk mengelola dependensi proyek.

python -m venv venv
# Di Windows:
.\venv\Scripts\activate
# Di macOS/Linux:
source venv/bin/activate



Instal Dependensi Python:

pip install -r requirements.txt



Konfigurasi Database (Lokal):
Secara default, aplikasi akan menggunakan SQLite (site.db) di folder proyek. Anda tidak perlu konfigurasi tambahan untuk ini.
Jika Anda ingin menggunakan PostgreSQL secara lokal, atur variabel lingkungan DATABASE_URL sebelum menjalankan aplikasi (lihat detail di app.py atau dokumentasi Flask-SQLAlchemy).

Jalankan Aplikasi:

python app.py



Aplikasi akan berjalan di http://127.0.0.1:5000/.

Deployment di Railway
Aplikasi ini dikonfigurasi untuk deployment menggunakan Docker di Railway.

Prasyarat
Akun Railway.

Proyek Railway yang terhubung ke repositori GitHub Anda.

Layanan PostgreSQL ditambahkan ke proyek Railway Anda.

Langkah-langkah Deployment
Pastikan File Proyek Terbaru:
Pastikan file app.py, requirements.txt, dan Dockerfile di repositori GitHub Anda adalah versi terbaru dan sesuai dengan yang disediakan dalam proyek ini.

requirements.txt:

setuptools==65.5.0
wheel==0.41.2
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Werkzeug==2.3.7
numpy==1.26.4
scipy==1.12.0
scikit-learn==1.4.2
pandas==2.2.2
graphviz==0.20.1
Jinja2==3.1.2
Flask-Moment==1.0.0
psycopg2-binary==2.9.9
gunicorn==21.2.0



Dockerfile:

FROM python:3.11-slim-buster
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir --verbose -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]



Procfile (di root proyek):

web: gunicorn app:app



Konfigurasi Variabel Lingkungan di Railway:
Di dashboard Railway Anda, navigasikan ke proyek Anda, lalu ke tab Variables. Tambahkan variabel berikut:

DATABASE_URL: Ini akan diisi secara otomatis oleh Railway jika Anda menambahkan layanan PostgreSQL. Jika tidak, masukkan URL koneksi PostgreSQL Anda.

SECRET_KEY: Masukkan string acak yang panjang dan unik untuk keamanan sesi Flask Anda.

Memicu Deployment:

Setelah semua file di-push ke GitHub dan variabel lingkungan diatur, Railway akan secara otomatis memicu build dan deployment.

Jika deployment tidak otomatis, Anda bisa memicunya secara manual di tab Deployments di Railway.

Penting: Saat memicu redeploy, cari dan aktifkan opsi "Clear build cache" atau "Rebuild without cache" untuk memastikan build yang bersih.

Pantau Log:
Pantau Build Logs di Railway untuk memastikan tidak ada error selama proses instalasi dependensi.

Akses Aplikasi:
Setelah deployment berhasil, Anda akan mendapatkan URL publik untuk aplikasi Anda di dashboard Railway.

Penggunaan Aplikasi
Login Admin
Akses halaman login di /login.

Kredensial Admin Default:

Username: admin

Password: admin

Sangat disarankan untuk mengubah password ini setelah login pertama kali di lingkungan produksi.

Manajemen Data
Setelah login sebagai admin, Anda dapat mengakses fitur manajemen data melalui dashboard:

Dataset: Kelola data mentah yang digunakan untuk melatih model. Anda bisa menambah, mengedit, menghapus, atau mengimpor dari CSV.

Atribut: Kelola daftar atribut (misalnya, JENIS_BENCANA, KECAMATAN).

Nilai Atribut: Kelola nilai-nilai yang mungkin untuk setiap atribut (misalnya, untuk JENIS_BENCANA: 'Tanah Gerak', 'Banjir').

Perhitungan & Pohon Keputusan
Akses halaman /calculation dan /tree (membutuhkan login admin) untuk melihat detail model C4.5 yang dilatih dan visualisasi pohon keputusan.

Prediksi Publik
Masyarakat umum dapat mengakses halaman /predict untuk melakukan prediksi kebutuhan relokasi dengan memasukkan data kondisi rumah dan keluarga. Halaman ini tidak memerlukan login.

Kredensial Admin Default
Username: admin

Password: admin

Peringatan: Untuk keamanan, segera ubah password ini setelah deployment pertama di lingkungan produksi.
