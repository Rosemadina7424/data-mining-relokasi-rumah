# app.py
import os
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.tree import DecisionTreeClassifier, export_graphviz
from flask_moment import Moment 
import pandas as pd
import graphviz 
import base64

# --- Konfigurasi Aplikasi ---
class Config:
    # Konfigurasi database untuk PostgreSQL di Railway
    # Railway akan secara otomatis menyediakan variabel lingkungan DATABASE_URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Fallback untuk pengujian lokal dengan SQLite jika DATABASE_URL tidak ditemukan
    if SQLALCHEMY_DATABASE_URI is None:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
        print("Menggunakan SQLite untuk pengembangan lokal. Pastikan DATABASE_URL diatur di Railway.")
    else:
        print(f"Menggunakan PostgreSQL dari DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kunci_rahasia_yang_sangat_kuat_dan_unik') # Ganti dengan kunci rahasia yang kuat
    UPLOAD_FOLDER = 'uploads' # Folder untuk menyimpan file CSV sementara

app = Flask(__name__)
moment = Moment(app) 
app.config.from_object(Config)
db = SQLAlchemy(app)

# Pastikan folder uploads ada
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Model Database ---
class Admin(db.Model):
    __tablename__ = 'tb_admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False) # Password akan di-hash

class Atribut(db.Model):
    __tablename__ = 'tb_atribut'
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False, unique=True)
    nilai_atributs = db.relationship('NilaiAtribut', backref='atribut', lazy=True, cascade="all, delete-orphan")

class NilaiAtribut(db.Model):
    __tablename__ = 'tb_nilai_atribut'
    id = db.Column(db.Integer, primary_key=True)
    id_atribut = db.Column(db.Integer, db.ForeignKey('tb_atribut.id'), nullable=False)
    nilai = db.Column(db.String(100), nullable=False)

class Dataset(db.Model):
    __tablename__ = 'tb_dataset'
    id = db.Column(db.Integer, primary_key=True)
    jenis_bencana = db.Column(db.String(50), nullable=False)
    kecamatan = db.Column(db.String(50), nullable=False)
    desa = db.Column(db.String(50), nullable=False)
    nama_kk = db.Column(db.String(100), nullable=False)
    jumlah_anggota_keluarga = db.Column(db.String(10), nullable=False) # Menggunakan string untuk '5+'
    status_kepemilikan_rumah = db.Column(db.String(50), nullable=False)
    kondisi_atap = db.Column(db.String(50), nullable=False)
    kondisi_kolom_balok = db.Column(db.String(50), nullable=False)
    kondisi_plesteran = db.Column(db.String(50), nullable=False)
    kondisi_lantai = db.Column(db.String(50), nullable=False)
    kondisi_pintu_jendela = db.Column(db.String(50), nullable=False)
    kondisi_instalasi_listrik = db.Column(db.String(50), nullable=False)
    kondisi_struktur_bangunan = db.Column(db.String(50), nullable=False)
    relokasi = db.Column(db.String(10), nullable=False) # Kolom target

# --- Inisialisasi Database dan Data Awal ---
with app.app_context():
    db.create_all()
    # Tambahkan admin default jika belum ada
    if not Admin.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin') # Hash password 'admin'
        admin_user = Admin(username='admin', password=hashed_password)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin default 'admin' dengan password 'admin' telah ditambahkan.")

    # Hapus atribut dan nilai atribut lama untuk menghindari konflik saat inisialisasi baru
    # Ini hanya untuk pengembangan. Di produksi, Anda akan menggunakan migrasi database.
    db.session.query(NilaiAtribut).delete()
    db.session.query(Atribut).delete()
    db.session.commit()

    # Tambahkan atribut dan nilai atribut default baru
    if not Atribut.query.first():
        attrs_data = {
            'JENIS_BENCANA': ['Tanah Gerak', 'Banjir', 'Gempa Bumi'],
            'KECAMATAN': ['Bantarkawung', 'Salem', 'Paguyangan'],
            'DESA': ['Cinanas DN', 'Cinanas KD', 'Cinanas WT', 'Cinanas RD', 'Cinanas AS', 'Cinanas RT', 'Windu Sakti', 'Cipajang'],
            'JUMLAH_ANGGOTA_KELUARGA': ['1', '2', '3', '4', '5+'],
            'STATUS_KEPEMILIKAN_RUMAH': ['Hak Milik', 'Sewa', 'Pinjam Pakai'],
            'KONDISI_ATAP': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_KOLOM_BALOK': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_PLESTERAN': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_LANTAI': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_PINTU_JENDELA': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_INSTALASI_LISTRIK': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan'],
            'KONDISI_STRUKTUR_BANGUNAN': ['Rusak Berat', 'Rusak Sedang', 'Rusak Ringan']
        }
        for attr_name, values in attrs_data.items():
            attr = Atribut(nama=attr_name)
            db.session.add(attr)
            db.session.flush() # Untuk mendapatkan ID atribut sebelum commit
            for val in values:
                db.session.add(NilaiAtribut(id_atribut=attr.id, nilai=val))
        db.session.commit()
        print("Atribut dan nilai atribut default baru telah ditambahkan.")

    # Hapus dataset lama untuk menghindari konflik saat inisialisasi baru
    # Ini hanya untuk pengembangan. Di produksi, Anda akan menggunakan migrasi database.
    db.session.query(Dataset).delete()
    db.session.commit()

    # Tambahkan dataset default baru
    if not Dataset.query.first():
        default_dataset = [
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas DN', 'nama_kk': 'DN', 'jumlah_anggota_keluarga': '4', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Sedang', 'kondisi_kolom_balok': 'Rusak Sedang', 'kondisi_plesteran': 'Rusak Ringan', 'kondisi_lantai': 'Rusak Sedang', 'kondisi_pintu_jendela': 'Rusak Sedang', 'kondisi_instalasi_listrik': 'Rusak Ringan', 'kondisi_struktur_bangunan': 'Rusak Sedang', 'relokasi': 'Tidak'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas KD', 'nama_kk': 'KD', 'jumlah_anggota_keluarga': '4', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Sedang', 'kondisi_kolom_balok': 'Rusak Ringan', 'kondisi_plesteran': 'Rusak Sedang', 'kondisi_lantai': 'Rusak Sedang', 'kondisi_pintu_jendela': 'Rusak Sedang', 'kondisi_instalasi_listrik': 'Rusak Sedang', 'kondisi_struktur_bangunan': 'Rusak Ringan', 'relokasi': 'Tidak'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas WT', 'nama_kk': 'WT', 'jumlah_anggota_keluarga': '2', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Ringan', 'kondisi_kolom_balok': 'Rusak Ringan', 'kondisi_plesteran': 'Rusak Sedang', 'kondisi_lantai': 'Rusak Ringan', 'kondisi_pintu_jendela': 'Rusak Ringan', 'kondisi_instalasi_listrik': 'Rusak Ringan', 'kondisi_struktur_bangunan': 'Rusak Ringan', 'relokasi': 'Tidak'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas RD', 'nama_kk': 'RD', 'jumlah_anggota_keluarga': '1', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Sedang', 'kondisi_kolom_balok': 'Rusak Ringan', 'kondisi_plesteran': 'Rusak Sedang', 'kondisi_lantai': 'Rusak Sedang', 'kondisi_pintu_jendela': 'Rusak Ringan', 'kondisi_instalasi_listrik': 'Rusak Sedang', 'kondisi_struktur_bangunan': 'Rusak Ringan', 'relokasi': 'Tidak'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas AS', 'nama_kk': 'AS', 'jumlah_anggota_keluarga': '4', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Berat', 'kondisi_kolom_balok': 'Rusak Berat', 'kondisi_plesteran': 'Rusak Berat', 'kondisi_lantai': 'Rusak Berat', 'kondisi_pintu_jendela': 'Rusak Berat', 'kondisi_instalasi_listrik': 'Rusak Berat', 'kondisi_struktur_bangunan': 'Rusak Berat', 'relokasi': 'Ya'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas RT', 'nama_kk': 'RT', 'jumlah_anggota_keluarga': '2', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Ringan', 'kondisi_kolom_balok': 'Rusak Ringan', 'kondisi_plesteran': 'Rusak Ringan', 'kondisi_lantai': 'Rusak Ringan', 'kondisi_pintu_jendela': 'Rusak Ringan', 'kondisi_instalasi_listrik': 'Rusak Sedang', 'kondisi_struktur_bangunan': 'Rusak Ringan', 'relokasi': 'Tidak'},
            {'jenis_bencana': 'Tanah Gerak', 'kecamatan': 'Bantarkawung', 'desa': 'Cinanas TR', 'nama_kk': 'TR', 'jumlah_anggota_keluarga': '3', 'status_kepemilikan_rumah': 'Hak Milik', 'kondisi_atap': 'Rusak Ringan', 'kondisi_kolom_balok': 'Rusak Sedang', 'kondisi_plesteran': 'Rusak Ringan', 'kondisi_lantai': 'Rusak Sedang', 'kondisi_pintu_jendela': 'Rusak Ringan', 'kondisi_instalasi_listrik': 'Rusak Ringan', 'kondisi_struktur_bangunan': 'Rusak Sedang', 'relokasi': 'Tidak'},
        ]
        for row in default_dataset:
            db.session.add(Dataset(**row))
        db.session.commit()
        print("Dataset default baru telah ditambahkan.")


# --- Fungsi Pembantu ---
def login_required(f):
    """Decorator untuk memastikan pengguna sudah login."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_c45_model():
    """Mengambil data dari database, melatih model C4.5, dan mengembalikan model serta fitur yang di-encode."""
    data = Dataset.query.all()
    if not data:
        return None, None, "Tidak ada data untuk melatih model. Silakan tambahkan dataset."

    # Konversi data ke Pandas DataFrame
    df = pd.DataFrame([{c.name: getattr(d, c.name) for c in d.__table__.columns} for d in data])
    df = df.drop(columns=['id'], errors='ignore') # Hapus kolom ID

    # Identifikasi fitur (X) dan target (y)
    # Asumsi kolom fitur adalah semua kolom kecuali 'relokasi' dan 'nama_kk' (karena nama_kk unik)
    features = [
        'jenis_bencana', 'kecamatan', 'desa', 'jumlah_anggota_keluarga',
        'status_kepemilikan_rumah', 'kondisi_atap', 'kondisi_kolom_balok',
        'kondisi_plesteran', 'kondisi_lantai', 'kondisi_pintu_jendela',
        'kondisi_instalasi_listrik', 'kondisi_struktur_bangunan'
    ]
    target = 'relokasi'

    if not all(col in df.columns for col in features + [target]):
        return None, None, "Kolom dataset tidak lengkap untuk melatih model C4.5. Pastikan semua atribut yang diperlukan ada."

    # One-Hot Encoding untuk fitur kategorikal
    X = pd.get_dummies(df[features])
    y = df[target]

    if X.empty or y.empty:
        return None, None, "Data tidak cukup untuk pelatihan setelah encoding."

    model = DecisionTreeClassifier(criterion='entropy', random_state=42) # C4.5 menggunakan entropy (Information Gain Ratio)
    model.fit(X, y)
    return model, X.columns.tolist(), None # Mengembalikan model, nama kolom fitur, dan pesan error (None jika sukses)


# --- Rute Aplikasi ---

@app.route('/')
def landing_page(): # Mengganti nama fungsi dari index menjadi landing_page untuk kejelasan
    # Jika sudah login, arahkan ke dashboard
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing_page.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['logged_in'] = True
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'logged_in' in session:
        return redirect(url_for('dashboard')) # Jika sudah login, tidak perlu registrasi lagi

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password or not confirm_password:
            flash('Semua kolom harus diisi.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Konfirmasi password tidak cocok.', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password minimal 6 karakter.', 'danger')
            return render_template('register.html')

        existing_user = Admin.query.filter_by(username=username).first()
        if existing_user:
            flash('Username sudah terdaftar. Silakan pilih username lain.', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        new_admin = Admin(username=username, password=hashed_password)
        db.session.add(new_admin)
        db.session.commit()
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
def logout(): # Tidak perlu login_required karena logout bisa dari mana saja
    session.pop('logged_in', None)
    flash('Anda telah logout.', 'info')
    return redirect(url_for('landing_page')) # Mengarahkan kembali ke landing page

# --- Rute Atribut ---
@app.route('/attributes')
@login_required
def attributes():
    all_attributes = Atribut.query.all()
    return render_template('attributes.html', attributes=all_attributes)

@app.route('/attributes/add', methods=['GET', 'POST'])
@login_required
def add_attribute():
    if request.method == 'POST':
        nama = request.form['nama']
        if Atribut.query.filter_by(nama=nama).first():
            flash('Atribut dengan nama ini sudah ada.', 'danger')
        else:
            new_attr = Atribut(nama=nama)
            db.session.add(new_attr)
            db.session.commit()
            flash('Atribut berhasil ditambahkan!', 'success')
            return redirect(url_for('attributes'))
    return render_template('add_attribute.html')

@app.route('/attributes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_attribute(id):
    attribute = Atribut.query.get_or_404(id)
    if request.method == 'POST':
        nama_baru = request.form['nama']
        if Atribut.query.filter(Atribut.nama == nama_baru, Atribut.id != id).first():
            flash('Atribut dengan nama ini sudah ada.', 'danger')
        else:
            attribute.nama = nama_baru
            db.session.commit()
            flash('Atribut berhasil diperbarui!', 'success')
            return redirect(url_for('attributes'))
    return render_template('edit_attribute.html', attribute=attribute)

@app.route('/attributes/delete/<int:id>', methods=['POST'])
@login_required
def delete_attribute(id):
    attribute = Atribut.query.get_or_404(id)
    db.session.delete(attribute)
    db.session.commit()
    flash('Atribut berhasil dihapus!', 'success')
    return redirect(url_for('attributes'))

# --- Rute Nilai Atribut ---
@app.route('/attribute_values')
@login_required
def attribute_values():
    all_attribute_values = db.session.query(NilaiAtribut, Atribut).join(Atribut).all()
    return render_template('attribute_values.html', attribute_values=all_attribute_values)

@app.route('/attribute_values/add', methods=['GET', 'POST'])
@login_required
def add_attribute_value():
    attributes = Atribut.query.all()
    if request.method == 'POST':
        id_atribut = request.form['id_atribut']
        nilai = request.form['nilai']
        if NilaiAtribut.query.filter_by(id_atribut=id_atribut, nilai=nilai).first():
            flash('Nilai atribut ini sudah ada untuk atribut yang dipilih.', 'danger')
        else:
            new_val = NilaiAtribut(id_atribut=id_atribut, nilai=nilai)
            db.session.add(new_val)
            db.session.commit()
            flash('Nilai atribut berhasil ditambahkan!', 'success')
            return redirect(url_for('attribute_values'))
    return render_template('add_attribute_value.html', attributes=attributes)

@app.route('/attribute_values/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_attribute_value(id):
    value = NilaiAtribut.query.get_or_404(id)
    attributes = Atribut.query.all()
    if request.method == 'POST':
        id_atribut_baru = request.form['id_atribut']
        nilai_baru = request.form['nilai']
        if NilaiAtribut.query.filter(NilaiAtribut.id_atribut == id_atribut_baru, NilaiAtribut.nilai == nilai_baru, NilaiAtribut.id != id).first():
            flash('Nilai atribut ini sudah ada untuk atribut yang dipilih.', 'danger')
        else:
            value.id_atribut = id_atribut_baru
            value.nilai = nilai_baru
            db.session.commit()
            flash('Nilai atribut berhasil diperbarui!', 'success')
            return redirect(url_for('attribute_values'))
    return render_template('edit_attribute_value.html', value=value, attributes=attributes)

@app.route('/attribute_values/delete/<int:id>', methods=['POST'])
@login_required
def delete_attribute_value(id):
    value = NilaiAtribut.query.get_or_404(id)
    db.session.delete(value)
    db.session.commit()
    flash('Nilai atribut berhasil dihapus!', 'success')
    return redirect(url_for('attribute_values'))

# --- Rute Dataset ---
@app.route('/dataset')
@login_required
def dataset():
    all_dataset = Dataset.query.all()
    return render_template('dataset.html', dataset=all_dataset)

@app.route('/dataset/add', methods=['GET', 'POST'])
@login_required
def add_dataset():
    # Ambil semua nilai atribut yang mungkin untuk dropdown
    jenis_bencana_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JENIS_BENCANA').all()]
    kecamatan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KECAMATAN').all()]
    desa_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'DESA').all()]
    jumlah_anggota_keluarga_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JUMLAH_ANGGOTA_KELUARGA').all()]
    status_kepemilikan_rumah_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'STATUS_KEPEMILIKAN_RUMAH').all()]
    kondisi_atap_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_ATAP').all()]
    kondisi_kolom_balok_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_KOLOM_BALOK').all()]
    kondisi_plesteran_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PLESTERAN').all()]
    kondisi_lantai_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_LANTAI').all()]
    kondisi_pintu_jendela_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PINTU_JENDELA').all()]
    kondisi_instalasi_listrik_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_INSTALASI_LISTRIK').all()]
    kondisi_struktur_bangunan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_STRUKTUR_BANGUNAN').all()]
    relokasi_values = ['Ya', 'Tidak'] # Kolom target

    if request.method == 'POST':
        new_entry = Dataset(
            jenis_bencana=request.form['jenis_bencana'],
            kecamatan=request.form['kecamatan'],
            desa=request.form['desa'],
            nama_kk=request.form['nama_kk'],
            jumlah_anggota_keluarga=request.form['jumlah_anggota_keluarga'],
            status_kepemilikan_rumah=request.form['status_kepemilikan_rumah'],
            kondisi_atap=request.form['kondisi_atap'],
            kondisi_kolom_balok=request.form['kondisi_kolom_balok'],
            kondisi_plesteran=request.form['kondisi_plesteran'],
            kondisi_lantai=request.form['kondisi_lantai'],
            kondisi_pintu_jendela=request.form['kondisi_pintu_jendela'],
            kondisi_instalasi_listrik=request.form['kondisi_instalasi_listrik'],
            kondisi_struktur_bangunan=request.form['kondisi_struktur_bangunan'],
            relokasi=request.form['relokasi']
        )
        db.session.add(new_entry)
        db.session.commit()
        flash('Data dataset berhasil ditambahkan!', 'success')
        return redirect(url_for('dataset'))
    return render_template('add_dataset.html',
                           jenis_bencana_values=jenis_bencana_values,
                           kecamatan_values=kecamatan_values,
                           desa_values=desa_values,
                           jumlah_anggota_keluarga_values=jumlah_anggota_keluarga_values,
                           status_kepemilikan_rumah_values=status_kepemilikan_rumah_values,
                           kondisi_atap_values=kondisi_atap_values,
                           kondisi_kolom_balok_values=kondisi_kolom_balok_values,
                           kondisi_plesteran_values=kondisi_plesteran_values,
                           kondisi_lantai_values=kondisi_lantai_values,
                           kondisi_pintu_jendela_values=kondisi_pintu_jendela_values,
                           kondisi_instalasi_listrik_values=kondisi_instalasi_listrik_values,
                           kondisi_struktur_bangunan_values=kondisi_struktur_bangunan_values,
                           relokasi_values=relokasi_values)

@app.route('/dataset/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_dataset(id):
    data_entry = Dataset.query.get_or_404(id)
    jenis_bencana_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JENIS_BENCANA').all()]
    kecamatan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KECAMATAN').all()]
    desa_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'DESA').all()]
    jumlah_anggota_keluarga_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JUMLAH_ANGGOTA_KELUARGA').all()]
    status_kepemilikan_rumah_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'STATUS_KEPEMILIKAN_RUMAH').all()]
    kondisi_atap_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_ATAP').all()]
    kondisi_kolom_balok_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_KOLOM_BALOK').all()]
    kondisi_plesteran_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PLESTERAN').all()]
    kondisi_lantai_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_LANTAI').all()]
    kondisi_pintu_jendela_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PINTU_JENDELA').all()]
    kondisi_instalasi_listrik_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_INSTALASI_LISTRIK').all()]
    kondisi_struktur_bangunan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_STRUKTUR_BANGUNAN').all()]
    relokasi_values = ['Ya', 'Tidak']

    if request.method == 'POST':
        data_entry.jenis_bencana = request.form['jenis_bencana']
        data_entry.kecamatan = request.form['kecamatan']
        data_entry.desa = request.form['desa']
        data_entry.nama_kk = request.form['nama_kk']
        data_entry.jumlah_anggota_keluarga = request.form['jumlah_anggota_keluarga']
        data_entry.status_kepemilikan_rumah = request.form['status_kepemilikan_rumah']
        data_entry.kondisi_atap = request.form['kondisi_atap']
        data_entry.kondisi_kolom_balok = request.form['kondisi_kolom_balok']
        data_entry.kondisi_plesteran = request.form['kondisi_plesteran']
        data_entry.kondisi_lantai = request.form['kondisi_lantai']
        data_entry.kondisi_pintu_jendela = request.form['kondisi_pintu_jendela']
        data_entry.kondisi_instalasi_listrik = request.form['kondisi_instalasi_listrik']
        data_entry.kondisi_struktur_bangunan = request.form['kondisi_struktur_bangunan']
        data_entry.relokasi = request.form['relokasi']
        db.session.commit()
        flash('Data dataset berhasil diperbarui!', 'success')
        return redirect(url_for('dataset'))
    return render_template('edit_dataset.html',
                           data=data_entry,
                           jenis_bencana_values=jenis_bencana_values,
                           kecamatan_values=kecamatan_values,
                           desa_values=desa_values,
                           jumlah_anggota_keluarga_values=jumlah_anggota_keluarga_values,
                           status_kepemilikan_rumah_values=status_kepemilikan_rumah_values,
                           kondisi_atap_values=kondisi_atap_values,
                           kondisi_kolom_balok_values=kondisi_kolom_balok_values,
                           kondisi_plesteran_values=kondisi_plesteran_values,
                           kondisi_lantai_values=kondisi_lantai_values,
                           kondisi_pintu_jendela_values=kondisi_pintu_jendela_values,
                           kondisi_instalasi_listrik_values=kondisi_instalasi_listrik_values,
                           kondisi_struktur_bangunan_values=kondisi_struktur_bangunan_values,
                           relokasi_values=relokasi_values)

@app.route('/dataset/delete/<int:id>', methods=['POST'])
@login_required
def delete_dataset(id):
    data_entry = Dataset.query.get_or_404(id)
    db.session.delete(data_entry)
    db.session.commit()
    flash('Data dataset berhasil dihapus!', 'success')
    return redirect(url_for('dataset'))

@app.route('/dataset/import_csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Tidak ada bagian file.', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Tidak ada file yang dipilih.', 'danger')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            header = [h.strip().lower() for h in next(csv_input)] # Baca header dan ubah ke lowercase
            
            # Pastikan header sesuai dengan kolom Dataset baru
            expected_headers = [
                'jenis bencana', 'kecamatan', 'desa', 'nama kk',
                'jumlah anggota keluarga', 'status kepemilikan rumah',
                'kondisi atap', 'kondisi kolom/balok', 'kondisi plesteran',
                'kondisi lantai', 'kondisi pintu/jendela',
                'kondisi instalasi listrik', 'kondisi struktur bangunan',
                'relokasi'
            ]
            
            # Konversi header CSV ke nama kolom model
            header_mapping = {
                'jenis bencana': 'jenis_bencana',
                'kecamatan': 'kecamatan',
                'desa': 'desa',
                'nama kk': 'nama_kk',
                'jumlah anggota keluarga': 'jumlah_anggota_keluarga',
                'status kepemilikan rumah': 'status_kepemilikan_rumah',
                'kondisi atap': 'kondisi_atap',
                'kondisi kolom/balok': 'kondisi_kolom_balok',
                'kondisi plesteran': 'kondisi_plesteran',
                'kondisi lantai': 'kondisi_lantai',
                'kondisi pintu/jendela': 'kondisi_pintu_jendela',
                'kondisi instalasi listrik': 'kondisi_instalasi_listrik',
                'kondisi struktur bangunan': 'kondisi_struktur_bangunan',
                'relokasi': 'relokasi'
            }
            
            # Periksa apakah semua header yang diharapkan ada
            if not all(h in header for h in expected_headers):
                flash(f"Header CSV tidak sesuai. Harap gunakan: {', '.join(expected_headers)}", 'danger')
                return redirect(request.url)

            imported_count = 0
            for row in csv_input:
                if len(row) == len(header):
                    row_data = dict(zip(header, row))
                    # Map CSV headers to model attributes
                    mapped_data = {header_mapping[k]: v for k, v in row_data.items() if k in header_mapping}
                    try:
                        new_entry = Dataset(**mapped_data)
                        db.session.add(new_entry)
                        imported_count += 1
                    except Exception as e:
                        flash(f"Gagal mengimpor baris: {row}. Error: {e}", 'warning')
                        db.session.rollback() # Rollback jika ada error pada baris tertentu
                        continue
            db.session.commit()
            flash(f'{imported_count} data berhasil diimpor dari CSV!', 'success')
            return redirect(url_for('dataset'))
        else:
            flash('Format file tidak didukung. Harap unggah file CSV.', 'danger')
    return render_template('import_csv.html')


# --- Rute C4.5 Tree & Calculation ---
@app.route('/tree')
@login_required
def tree():
    model, feature_names, error_msg = get_c45_model()
    tree_image_base64 = None
    if error_msg:
        flash(error_msg, 'danger')
    elif model:
        try:
            dot_data = export_graphviz(model, out_file=None,
                                       feature_names=feature_names,
                                       class_names=model.classes_,
                                       filled=True, rounded=True,
                                       special_characters=True)
            graph = graphviz.Source(dot_data, format="png")
            # Render graph to bytes and encode to base64
            png_bytes = graph.pipe()
            tree_image_base64 = base64.b64encode(png_bytes).decode('utf-8')
        except Exception as e:
            flash(f"Gagal menghasilkan visualisasi pohon. Pastikan Graphviz terinstal. Error: {e}", 'danger')
            tree_image_base64 = None

    return render_template('tree.html', tree_image_base64=tree_image_base64)

@app.route('/calculation')
@login_required
def calculation():
    # Untuk bagian perhitungan, kita akan menampilkan informasi dasar tentang model
    # dan mungkin beberapa statistik dataset. Perhitungan gain/gain ratio detail
    # akan membutuhkan implementasi C4.5 manual atau ekstraksi dari scikit-learn
    # yang lebih dalam. Untuk kesederhanaan, kita akan fokus pada ringkasan.
    model, feature_names, error_msg = get_c45_model()
    
    if error_msg:
        flash(error_msg, 'danger')
        return render_template('calculation.html', model_info="Tidak dapat melatih model.", feature_importances=None)

    model_info = "Model C4.5 berhasil dilatih."
    feature_importances = None
    if model and feature_names:
        # Menampilkan pentingnya fitur sebagai indikasi perhitungan
        importances = model.feature_importances_
        feature_importances = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        
    return render_template('calculation.html', model_info=model_info, feature_importances=feature_importances)


# --- Rute Prediksi ---
@app.route('/predict', methods=['GET', 'POST'])
def predict(): # TIDAK ADA login_required di sini, karena ini untuk masyarakat
    model, feature_names, error_msg = get_c45_model()
    prediction_result = None
    
    # Ambil semua nilai atribut yang mungkin untuk dropdown
    jenis_bencana_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JENIS_BENCANA').all()]
    kecamatan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KECAMATAN').all()]
    desa_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'DESA').all()]
    jumlah_anggota_keluarga_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'JUMLAH_ANGGOTA_KELUARGA').all()]
    status_kepemilikan_rumah_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'STATUS_KEPEMILIKAN_RUMAH').all()]
    kondisi_atap_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_ATAP').all()]
    kondisi_kolom_balok_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_KOLOM_BALOK').all()]
    kondisi_plesteran_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PLESTERAN').all()]
    kondisi_lantai_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_LANTAI').all()]
    kondisi_pintu_jendela_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_PINTU_JENDELA').all()]
    kondisi_instalasi_listrik_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_INSTALASI_LISTRIK').all()]
    kondisi_struktur_bangunan_values = [na.nilai for na in NilaiAtribut.query.join(Atribut).filter(Atribut.nama == 'KONDISI_STRUKTUR_BANGUNAN').all()]

    if error_msg:
        flash(error_msg, 'danger')
    elif model:
        if request.method == 'POST':
            input_data = {
                'jenis_bencana': request.form['jenis_bencana'],
                'kecamatan': request.form['kecamatan'],
                'desa': request.form['desa'],
                'jumlah_anggota_keluarga': request.form['jumlah_anggota_keluarga'],
                'status_kepemilikan_rumah': request.form['status_kepemilikan_rumah'],
                'kondisi_atap': request.form['kondisi_atap'],
                'kondisi_kolom_balok': request.form['kondisi_kolom_balok'],
                'kondisi_plesteran': request.form['kondisi_plesteran'],
                'kondisi_lantai': request.form['kondisi_lantai'],
                'kondisi_pintu_jendela': request.form['kondisi_pintu_jendela'],
                'kondisi_instalasi_listrik': request.form['kondisi_instalasi_listrik'],
                'kondisi_struktur_bangunan': request.form['kondisi_struktur_bangunan']
            }

            # Buat DataFrame dari input pengguna
            input_df = pd.DataFrame([input_data])

            # One-Hot Encode input data, pastikan kolomnya sesuai dengan saat training
            # Gunakan reindex untuk memastikan semua kolom fitur ada, isi dengan 0 jika tidak ada
            input_encoded = pd.get_dummies(input_df).reindex(columns=feature_names, fill_value=0)

            if not input_encoded.empty:
                try:
                    prediction = model.predict(input_encoded)
                    prediction_result = prediction[0]
                    flash(f'Prediksi Relokasi: {prediction_result}', 'info')
                except Exception as e:
                    flash(f"Gagal melakukan prediksi. Error: {e}", 'danger')
            else:
                flash('Gagal mengolah input prediksi.', 'danger')
    else:
        flash("Model belum siap untuk prediksi. Silakan periksa dataset.", 'warning')

    return render_template('predict.html',
                           prediction_result=prediction_result,
                           jenis_bencana_values=jenis_bencana_values,
                           kecamatan_values=kecamatan_values,
                           desa_values=desa_values,
                           jumlah_anggota_keluarga_values=jumlah_anggota_keluarga_values,
                           status_kepemilikan_rumah_values=status_kepemilikan_rumah_values,
                           kondisi_atap_values=kondisi_atap_values,
                           kondisi_kolom_balok_values=kondisi_kolom_balok_values,
                           kondisi_plesteran_values=kondisi_plesteran_values,
                           kondisi_lantai_values=kondisi_lantai_values,
                           kondisi_pintu_jendela_values=kondisi_pintu_jendela_values,
                           kondisi_instalasi_listrik_values=kondisi_instalasi_listrik_values,
                           kondisi_struktur_bangunan_values=kondisi_struktur_bangunan_values)

# --- Jalankan Aplikasi ---
if __name__ == '__main__':
    app.run(debug=True)
