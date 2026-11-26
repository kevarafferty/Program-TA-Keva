# Ringkasan analisis skenario

Dibuat oleh `analisis_skenario.py` (label_kegagalan v2 (22 Nov 2026, FRAKSI_MIN 0,5 / D_TERLAMBAT 8 m)). Rata-rata per episode, [CI 95% bootstrap].

## Per kondisi

| Kode | t | Mode | Backend | n | Roda (utama) | Logika Dika | Episode gagal | Persepsi gagal / lintasan | Terlambat / lintasan | Palsu / frame | Akhir |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ID0 | 1 | konstan | grid | 30 | 57.6 [52.0–62.9] | 74.6 [70.1–78.9] | 20.0 [6.7–36.7] | 3.0 [1.2–5.0] | 0.0 [0.0–0.0] | 9.1 [8.1–10.2] | {'finis': 24, 'tabrakan': 6} |
| ID0 | 1 | konstan | grid | 30 | 29.9 [24.7–35.0] | 34.2 [29.4–39.2] | 63.3 [46.7–80.0] | 2.1 [0.0–4.7] | 0.0 [0.0–0.0] | 15.1 [12.3–18.2] | {'finis': 11, 'keluar_jalan': 1, 'tabrakan': 18} |
| ID0 | 1 | konstan | grid | 30 | 47.5 [43.4–51.7] | 56.3 [51.7–60.9] | 30.0 [13.3–46.7] | 9.6 [5.1–14.4] | 0.0 [0.0–0.0] | 8.3 [7.3–9.4] | {'finis': 21, 'tabrakan': 9} |
| ID0 | 1 | konstan | grid | 30 | 36.2 [27.7–44.4] | 36.9 [28.2–45.6] | 50.0 [33.3–70.0] | 11.5 [6.3–16.9] | 0.0 [0.0–0.0] | 5.6 [4.8–6.3] | {'finis': 15, 'keluar_jalan': 15} |

Catatan: n = 1 episode hanya uji alur; jangan ditafsirkan sebagai hasil.
