# WPOS PRO 2 — Windows Suite

Windows desktop POS offline berbasis SQLite dengan **Password Reset Center**.

## Struktur
- `app/wpos_app.py` — login, kasir, produk, checkout tunai, stok, dan reset password.
- `app/reset_tool.py` — launcher reset password khusus.
- `build_windows.bat` — build dua EXE dengan PyInstaller.
- `.github/workflows/windows-build.yml` — build otomatis dan artifact ZIP.

## Database
Database produksi **tidak disimpan di Git**. Letakkan `wpos.db` di samping EXE saat runtime.

Password menggunakan format WPOS:
`pbkdf2_sha256$210000$salt$hash`

Password reset membuat backup timestamped sebelum UPDATE.

## Build lokal
Jalankan `build_windows.bat` pada Windows dengan Python 3.11+.

## Status
Fondasi Windows sudah disiapkan. Modul lanjutan seperti Printer Center, laporan A4/thermal, pembelian, supplier, pelanggan, dan settings akan diintegrasikan bertahap dengan schema WPOS yang ada.
