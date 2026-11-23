"""
analisis_skenario.py — Label semua run + ringkasan per kondisi + uji regresi REG vs baseline #21–#22.

    python analisis_skenario.py                      # semua run di log_skenario (folder berawalan _ dilewati)
    python analisis_skenario.py --ulang              # hitung ulang label walau label_*.npz sudah ada
    python analisis_skenario.py --pola "*REG_t*"     # hanya run tertentu

Keluaran: hasil_analisis/ringkasan_kondisi.csv, ringkasan_kondisi.json, laporan.md
           + di tiap folder run: label_ep*.npz, lintasan_ep*.csv (label_kegagalan.py)

Metrik per kondisi (rata-rata episode + CI 95% bootstrap, 5000 ulangan):
  roda_tak_tercapai_gagal  metrik UTAMA (HASIL_BASELINE.md): % lubang yang dilewati tanpa kontak roda / semua lubang
  roda_hanya_dilewati      % tanpa kontak di antara lubang yang dilewati
  dika                     % 'avoids' penghitung Dika (dicatat env) / semua lubang
  episode_gagal            % episode berakhir tabrakan atau keluar jalan
  gagal_persepsi_lintasan  % lintasan lubang (yang tampak) dengan kotak teratas YOLO cocok < 50% frame jendela 3–15 m
  terlambat_lintasan       % lintasan lubang yang tidak pernah cocok pada jarak >= 8 m
  gagal_persepsi_frame     % frame bertarget dengan kotak teratas tidak cocok
  palsu_top_frame          % frame tanpa target dengan kotak teratas tidak mengenai lubang mana pun
  langkah_kontak_H         % langkah berlabel kontak dalam 2 s (prevalensi label monitor keputusan)

Uji regresi REG (runner baru) vs baseline (cleanTest, #21–#22) dengan metrik yang sama dihitung ulang dari
posisi_ep*.csv baseline. "Setara" = CI 95% bootstrap selisih rata-rata mencakup 0 untuk roda_tak_tercapai_gagal,
dika, dan episode_gagal. Ini kriteria praktis, bukan uji ekuivalensi formal (TOST).
"""
import argparse
import csv
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from label_kegagalan import VERSI, label_episode, label_lintasan, ringkas_episode, simpan  # noqa: E402
from kontak_roda import MICROLINO  # noqa: E402

METRIK = ["roda_tak_tercapai_gagal", "roda_hanya_dilewati", "dika", "episode_gagal", "gagal_persepsi_lintasan",
          "terlambat_lintasan", "gagal_persepsi_frame", "palsu_top_frame", "langkah_kontak_H"]
METRIK_REGRESI = ["roda_tak_tercapai_gagal", "dika", "episode_gagal"]
BASELINE_DIR = os.path.normpath(os.path.join(DIR, "..", "10_runner", "DQN_Akselerasi vertikal", "log_runner"))
BASELINE_GT = os.path.normpath(os.path.join(DIR, "..", "alat_carla", "pothole_gt_v2_segmen_dika.json"))
REG_KE_BASELINE = {1: "ClearNoon", 2: "HardRainNoon", 3: "ClearNight"}
RNG = np.random.default_rng(0)


def ci(v):
    v = np.asarray([x for x in v if x == x], float)
    if len(v) == 0:
        return [np.nan, np.nan]
    if len(v) < 2:
        return [float(v[0])] * 2
    b = RNG.choice(v, (5000, len(v))).mean(1)
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def ci_selisih(a, b):
    a = np.asarray([x for x in a if x == x], float)
    b = np.asarray([x for x in b if x == x], float)
    if len(a) < 2 or len(b) < 2:
        return [np.nan, np.nan]
    d = RNG.choice(a, (5000, len(a))).mean(1) - RNG.choice(b, (5000, len(b))).mean(1)
    return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def urai_nama(run):
    b = os.path.basename(run.rstrip("\\/"))
    p = b.split("_")
    # <tanggal>_<jam>_<kode>_t<tingkat>_<mode>_<backend>_<label>
    return dict(kode=p[2], tingkat=int(p[3][1:]), mode=p[4], backend=p[5], label="_".join(p[6:]))


def proses_run(run, ulang=False):
    out = []
    f = os.path.join(run, "ringkasan_episode.csv")
    if not os.path.exists(f):
        return out
    with open(f) as fh:
        ring = list(csv.DictReader(fh))
    for r in ring:
        nama = "ep%03d_seed%s" % (int(r["episode"]), r["seed"])
        h = None if ulang else muat_label(run, nama)
        if h is None:
            h = label_episode(run, nama)
            simpan(run, nama, h)
        e = ringkas_episode(h, r)
        e.update(seed=int(r["seed"]), run=os.path.basename(run), verif=r.get("verif_percobaan", ""),
                 hook=int(r.get("hook_tidak_cocok", 0) or 0))
        out.append(e)
    return out


def muat_label(run, nama):
    """Pakai label tersimpan (label_*.npz + lintasan_*.csv) bila versinya sama dan lebih baru dari log."""
    pn = os.path.join(run, "label_%s.npz" % nama)
    pc = os.path.join(run, "lintasan_%s.csv" % nama)
    pl = os.path.join(run, "langkah_%s.csv" % nama)
    if not (os.path.exists(pn) and os.path.exists(pc)) or os.path.getmtime(pn) < os.path.getmtime(pl):
        return None
    z = np.load(pn)
    if str(z["versi"]) != VERSI:
        return None
    langkah = {k: z[k] for k in z.files if k != "versi"}
    lintasan = []
    with open(pc) as f:
        for b in csv.DictReader(f):
            for k in ("gagal_persepsi", "terlambat"):
                if b.get(k, "") != "":
                    b[k] = int(b[k])
            lintasan.append(b)
    return dict(langkah=langkah, lintasan=lintasan)


def baseline_episode(kondisi):
    """Metrik yang sama untuk run baseline cleanTest (#21–#22), dari posisi_ep*.csv."""
    runs = sorted(glob.glob(os.path.join(BASELINE_DIR, "*_%s_Epic" % kondisi)))
    if not runs:
        return []
    with open(BASELINE_GT, encoding="utf-8") as f:
        gt = json.load(f)
    out = []
    for run in runs:
        with open(os.path.join(run, "ringkasan_episode.csv")) as fh:
            ring = {r["seed"]: r for r in csv.DictReader(fh)}
        for p in sorted(glob.glob(os.path.join(run, "posisi_ep*.csv"))):
            seed = p.rsplit("seed", 1)[1].split(".")[0]
            if seed not in ring:
                continue
            with open(p) as fh:
                rows = list(csv.DictReader(fh))
            x, y, yaw = (np.array([float(q[c]) for q in rows]) for c in ("x", "y", "yaw"))
            langkah, lintasan = label_lintasan(x, y, yaw, gt, MICROLINO)
            r = dict(ring[seed])
            xe = float(r["x_akhir"])
            r["akhir"] = "finis" if xe >= -28 else ("tabrakan" if r.get("tabrakan") else "keluar_jalan")
            e = ringkas_episode(dict(langkah=langkah, lintasan=lintasan), r)
            e.update(seed=int(seed), run=os.path.basename(run))
            out.append(e)
    return out


def fmt(m, c):
    return "%.1f [%.1f–%.1f]" % (m, c[0], c[1]) if m == m else "–"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pola", default="2026*")
    ap.add_argument("--ulang", action="store_true")
    ap.add_argument("--out", default=os.path.join(DIR, "hasil_analisis"))
    ap.add_argument("--tanpa_baseline", action="store_true")
    ap.add_argument("--hanya_baseline", default="", help="isi cache satu kondisi baseline lalu keluar (mis. ClearNoon)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.hanya_baseline:
        bl = baseline_episode(a.hanya_baseline)
        json.dump(bl, open(os.path.join(a.out, "cache_baseline_%s.json" % a.hanya_baseline), "w"),
                  default=lambda o: None if o != o else float(o))
        print("cache baseline %s: %d episode" % (a.hanya_baseline, len(bl)))
        return
    runs = sorted(r for r in glob.glob(os.path.join(DIR, "log_skenario", a.pola)) if os.path.isdir(r))
    grup = defaultdict(list)
    for run in runs:
        k = urai_nama(run)
        kunci = (k["kode"], k["tingkat"], k["mode"], k["backend"], k["label"])
        eps = proses_run(run, a.ulang)
        grup[kunci] += eps
        print("%-50s %d episode" % (os.path.basename(run), len(eps)))

    baris = []
    for kunci in sorted(grup):
        eps = grup[kunci]
        seeds = [e["seed"] for e in eps]
        b = dict(kode=kunci[0], tingkat=kunci[1], mode=kunci[2], backend=kunci[3], label=kunci[4], episode=len(eps),
                 seed_ganda=len(seeds) - len(set(seeds)),
                 tanpa_verifikasi=sum(1 for e in eps if e["verif"] == ""),
                 hook_gagal=sum(e["hook"] for e in eps),
                 akhir={x: sum(e["akhir"] == x for e in eps) for x in sorted({e["akhir"] for e in eps})})
        for m in METRIK:
            v = [e[m] for e in eps]
            b[m] = float(np.nanmean(v)) if any(x == x for x in v) else np.nan
            b[m + "_ci95"] = ci(v)
        baris.append(b)

    # --- regresi REG ---
    regresi = []
    if not a.tanpa_baseline:
        for kunci, eps in sorted(grup.items()):
            if kunci[0] != "REG":
                continue
            kond = REG_KE_BASELINE[kunci[1]]
            cache = os.path.join(a.out, "cache_baseline_%s.json" % kond)
            if os.path.exists(cache) and not a.ulang:
                bl = json.load(open(cache))
            else:
                bl = baseline_episode(kond)
                json.dump(bl, open(cache, "w"), default=lambda o: None if o != o else float(o))
            if not bl:
                continue
            r = dict(kondisi="REG t%d (%s)" % (kunci[1], kond), n_reg=len(eps), n_baseline=len(bl), setara=True)
            for m in METRIK_REGRESI:
                vr, vb = [e[m] for e in eps], [e[m] for e in bl]
                cs = ci_selisih(vr, vb)
                r[m] = dict(reg=float(np.nanmean(vr)), reg_ci=ci(vr), baseline=float(np.nanmean(vb)), baseline_ci=ci(vb),
                            selisih_ci=cs, mencakup_0=bool(cs[0] <= 0 <= cs[1]))
                r["setara"] &= r[m]["mencakup_0"]
            regresi.append(r)

    # --- tulis ---
    kol = ["kode", "tingkat", "mode", "backend", "label", "episode", "seed_ganda", "tanpa_verifikasi", "hook_gagal"]
    with open(os.path.join(a.out, "ringkasan_kondisi.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(kol + sum([[m, m + "_ci_bawah", m + "_ci_atas"] for m in METRIK], []) + ["akhir"])
        for b in baris:
            w.writerow([b[k] for k in kol] + sum([[round(b[m], 2), round(b[m + "_ci95"][0], 2), round(b[m + "_ci95"][1], 2)]
                                                  for m in METRIK], []) + [json.dumps(b["akhir"])])
    with open(os.path.join(a.out, "ringkasan_kondisi.json"), "w", encoding="utf-8") as f:
        json.dump(dict(versi_label=VERSI, kondisi=baris, regresi=regresi), f, indent=1, ensure_ascii=False,
                  default=lambda o: None if o != o else str(o))

    L = ["# Ringkasan analisis skenario", "", "Dibuat oleh `analisis_skenario.py` (%s). Rata-rata per episode, [CI 95%% bootstrap]." % VERSI, ""]
    if regresi:
        L += ["## Uji regresi REG (runner baru) vs baseline #21–#22", "",
              "| Kondisi | n | Metrik | REG | Baseline | CI selisih | Mencakup 0 |", "|---|---|---|---|---|---|---|"]
        for r in regresi:
            for m in METRIK_REGRESI:
                q = r[m]
                L.append("| %s | %d / %d | %s | %s | %s | [%.1f, %.1f] | %s |" % (
                    r["kondisi"], r["n_reg"], r["n_baseline"], m, fmt(q["reg"], q["reg_ci"]),
                    fmt(q["baseline"], q["baseline_ci"]), q["selisih_ci"][0], q["selisih_ci"][1], "ya" if q["mencakup_0"] else "**tidak**"))
        L += ["", "Kesimpulan: " + "; ".join("%s %s" % (r["kondisi"], "SETARA" if r["setara"] else "**TIDAK SETARA**") for r in regresi), ""]
    L += ["## Per kondisi", "",
          "| Kode | t | Mode | Backend | n | Roda (utama) | Logika Dika | Episode gagal | Persepsi gagal / lintasan | Terlambat / lintasan | Palsu / frame | Akhir |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for b in baris:
        L.append("| %s | %d | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
            b["kode"], b["tingkat"], b["mode"], b["backend"], b["episode"],
            fmt(b["roda_tak_tercapai_gagal"], b["roda_tak_tercapai_gagal_ci95"]), fmt(b["dika"], b["dika_ci95"]),
            fmt(b["episode_gagal"], b["episode_gagal_ci95"]),
            fmt(b["gagal_persepsi_lintasan"], b["gagal_persepsi_lintasan_ci95"]),
            fmt(b["terlambat_lintasan"], b["terlambat_lintasan_ci95"]),
            fmt(b["palsu_top_frame"], b["palsu_top_frame_ci95"]), b["akhir"]))
    peringatan = [b for b in baris if b["seed_ganda"] or b["tanpa_verifikasi"] or b["hook_gagal"]]
    if peringatan:
        L += ["", "## Peringatan", ""] + ["- %s t%d %s: seed ganda %d, tanpa verifikasi %d, hook gagal %d" % (
            b["kode"], b["tingkat"], b["mode"], b["seed_ganda"], b["tanpa_verifikasi"], b["hook_gagal"]) for b in peringatan]
    L += ["", "Catatan: n = 1 episode hanya uji alur; jangan ditafsirkan sebagai hasil."]
    with open(os.path.join(a.out, "laporan.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))
    print("\nDitulis ke", a.out)


if __name__ == "__main__":
    main()
