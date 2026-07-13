# Implementation Plan — Index & Urutan Kerja

> Voice of Customer System × OneBox · dibuat 2026-07-13 · semua plan grounded ke codebase (penanda [verified]/[assumption]/[blocked] di tiap dokumen)
> **Cara pakai:** kerjakan berurutan sesuai fase. Tiap selesai task: isi §7 (Temuan & Deviasi) dokumen itu — jadi bahan RI-17.

## Keputusan Arsitektur
Semua keputusan (D1–D8) tercatat di [RI-02](RI-02_keputusan-arsitektur.md) — sudah dipilihkan default terbaik, tinggal ratifikasi Pak Agung. Kalau ada override, propagasi ke plan yang menyebut nomor D-nya.

## Urutan Eksekusi

### Fase A — Fondasi (jalan duluan, ±10 MD)
| # | Task | MD | Dependensi |
|---|------|----|------------|
| [RI-01](RI-01_field-mapping.md) | Field mapping (draft ±80% sudah terverifikasi) | 3 | — |
| [RI-02](RI-02_keputusan-arsitektur.md) | Ratifikasi keputusan D1–D8 | 2 | RI-01 |
| [RI-03](RI-03_kesiapan-api-voc.md) | VoC run lokal + uji dari WSL + fixture | 2 | — (paralel RI-01) |
| — | Buat feature branch `feature/DNGO19-XXXX_VoC-Integration` dari `develop` | — | tiket Jira |

### Fase B — Ingestion (inti backend, ±15 MD)
| # | Task | MD | Dependensi |
|---|------|----|------------|
| [RI-04](RI-04_client.md) | `VoiceOfCustomerSystemClient` (pola CiptalifeApi) | 4 | RI-03 |
| [RI-05](RI-05_ingest-task.md) | `VoiceOfCustomerSystemTask` (pola SonarTask) | 5 | RI-01, 04 |
| [RI-06](RI-06_tenant-mapping.md) | Mapping site↔lokasi (config MVP) | 3 | RI-05 |
| [RI-07](RI-07_analysis-fields.md) | issue_category → CategoryId + Meta | 3 | RI-05, D7 |

### Fase C — Otomasi (±7 MD)
| # | Task | MD | Dependensi |
|---|------|----|------------|
| [RI-09](RI-09_error-observability.md) | Error handling & ringkasan run | 3 | RI-05 |
| [RI-08](RI-08_scheduler-delta.md) | Scheduler + delta sync (`updated_since`) | 4 | RI-05, 09, gap Codex |

*(RI-09 sengaja sebelum RI-08 — jangan menjadwalkan job yang belum tahan banting.)*

### Fase D — UI/VOC (±16 MD)
| # | Task | MD | Dependensi |
|---|------|----|------------|
| [RI-10](RI-10_ui-list.md) | List review di Mediamonitoring | 4 | RI-05 |
| [RI-11](RI-11_ui-detail.md) | Detail review | 4 | RI-10 |
| [RI-12](RI-12_dashboard-voc.md) | Dashboard VOC | 5 | RI-07, 10 |
| [RI-15](RI-15_menu-role.md) | Menu + role | 2 | RI-10 |

### 🏁 Garis MVP = selesai Fase A–D (± 48 MD) → demo ke lead/CEO

### Fase E — Pasca-MVP (±12 MD)
| # | Task | MD | Dependensi |
|---|------|----|------------|
| [RI-14](RI-14_manajemen-review.md) | Aksi kelola: assign/resolve/note | 4 | RI-11 |
| [RI-13](RI-13_ui-polish.md) | Poles visual vs benchmark Next.js | 3 | RI-12 |
| [RI-16](RI-16_integration-test.md) | E2E test + staging | 3 | semua |
| [RI-17](RI-17_dokumentasi-runbook.md) | Dokumentasi + runbook | 2 | semua |

## Guardrail Lintas-Task (berlaku selalu)
1. Semua query/insert scoped `SiteId` — tanpa kecuali.
2. Jangan commit `.env*`, `app/config/development.php`, `app/config/local.php`, atau credential apa pun.
3. Jangan refactor MediamonitoringController — hanya TAMBAH action.
4. Jangan bikin migration sebelum D4/D7 diratifikasi.
5. Teks review = konten publik tak terpercaya — selalu escape di Volt.
6. API gap → handoff ke Codex, jangan ditambal di OneBox.
