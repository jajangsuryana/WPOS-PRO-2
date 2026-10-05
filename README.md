# WPOS PRO 2

WPOS PRO 2 adalah aplikasi POS offline berbasis Python + Tkinter + SQLite.

## Modul terpadu
- Login Admin/Kasir
- Dashboard
- Kasir, keranjang, pembayaran, kembalian
- Produk dan stok
- Pembelian / stok masuk
- Pelanggan dan supplier
- Laporan dan export CSV
- Pengguna dan reset password
- Pengaturan toko
- Backup database
- Cetak struk melalui printer Windows

## Menjalankan lokal di Windows

1. Install Python 3.11+.
2. Buka Command Prompt pada folder repository.
3. Jalankan:

```bat
python app\wpos_app.py
```

Database `wpos.db` akan dibuat/digunakan otomatis di folder aplikasi.

## Login awal

Username: `admin`
Password: `admin112233`

Segera ubah password setelah login melalui menu Pengguna.

## Catatan keamanan

Jangan commit database produksi, file backup, atau password nyata ke repository publik. Gunakan database lokal untuk pengujian.
