import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_CACHE_INSIGHT = {}


def _fallback_insight(ringkasan: dict) -> dict:
    budget_fmt = ringkasan.get("budget_fmt", "Rp 1.000.000")
    pred_fmt = ringkasan.get("pred_rp_fmt", "Rp 1.000.000")
    jarak = ringkasan.get("jarak_in", "1.50")
    ac = ringkasan.get("ac_in", "semua")

    return {
        "chart_1": (
            f"Sebagian besar kos berada di rentang harga menengah, sementara batas budget kamu di {budget_fmt} "
            f"membantu menyaring pilihan yang paling pas."
        ),
        "chart_2": (
            f"Dengan jarak sekitar {jarak} km dan pilihan AC '{ac}', titik perkiraan berada di kisaran {pred_fmt} "
            f"dibandingkan sebaran kos lain di Madiun."
        ),
        "chart_3": (
            "Kelompok rating yang lebih tinggi cenderung memiliki rata-rata sewa bulanan yang lebih tinggi pula, "
            "jadi kamu bisa menimbang antara rating dan budget."
        ),
    }


def buat_keterangan_grafik(ringkasan: dict) -> dict:
    cache_key = json.dumps(ringkasan, sort_keys=True)
    if cache_key in _CACHE_INSIGHT:
        return _CACHE_INSIGHT[cache_key]

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        hasil = _fallback_insight(ringkasan)
        _CACHE_INSIGHT[cache_key] = hasil
        return hasil

    prompt = (
        "Kamu adalah asisten penjelas grafik kos mahasiswa di Madiun dengan gaya bahasa yang hangat, "
        "ramah, sopan, dan jelas seperti GoPay (pakai 'kamu', tidak kaku, tidak terlalu gaul, tanpa emoji).\n"
        "Berdasarkan ringkasan data berikut, buatkan 1-2 kalimat keterangan singkat dan bermanfaat "
        "untuk masing-masing dari 3 diagram.\n"
        "Jawab HANYA dalam format JSON valid dengan kunci tepat: "
        '{"chart_1": "...", "chart_2": "...", "chart_3": "..."}\n\n'
        f"Data: {json.dumps(ringkasan, ensure_ascii=False)}"
    )

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        konten = resp.choices[0].message.content or "{}"
        parsed = json.loads(konten)
        fallback = _fallback_insight(ringkasan)
        hasil = {
            "chart_1": str(parsed.get("chart_1") or fallback["chart_1"]),
            "chart_2": str(parsed.get("chart_2") or fallback["chart_2"]),
            "chart_3": str(parsed.get("chart_3") or fallback["chart_3"]),
        }
    except Exception:
        hasil = _fallback_insight(ringkasan)

    _CACHE_INSIGHT[cache_key] = hasil
    return hasil