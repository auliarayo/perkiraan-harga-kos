import json
from django.shortcuts import render
from groq_insight import buat_keterangan_grafik
from ml import (
    MAX_BUDGET,
    MAX_JARAK,
    MIN_BUDGET,
    MIN_JARAK,
    latih_model_rf,
    muat_dataset,
    proses_prediksi_dan_rekomendasi,
)

DF_KOS = muat_dataset()
MODEL_RF, MAE_UJI = latih_model_rf(DF_KOS)
MIN_RATING = float(DF_KOS["rating"].min())
MAX_RATING = float(DF_KOS["rating"].max())


def _clamp_float(val, low, high, default):
    try:
        num = float(val)
        return max(low, min(high, num))
    except (TypeError, ValueError):
        return default


def _clamp_int(val, low, high, default):
    try:
        num = int(float(val))
        return max(low, min(high, num))
    except (TypeError, ValueError):
        return default


def index(request):
    params = request.GET
    jarak_in = _clamp_float(params.get("jarak"), MIN_JARAK, MAX_JARAK, 1.50)
    budget_in = _clamp_int(params.get("budget"), MIN_BUDGET, MAX_BUDGET, 1_000_000)
    rating_in = _clamp_float(params.get("rating"), MIN_RATING, MAX_RATING, 4.0)
    ac_in = params.get("ac", "semua")
    if ac_in not in {"semua", "ya", "tidak"}:
        ac_in = "semua"

    hasil = proses_prediksi_dan_rekomendasi(
        df=DF_KOS,
        model=MODEL_RF,
        jarak_in=jarak_in,
        budget_in=budget_in,
        rating_in=rating_in,
        ac_in=ac_in,
    )

    ringkasan_grafik = {
        "jarak_in": f"{jarak_in:.2f}",
        "budget_fmt": f"Rp {budget_in:,}".replace(",", "."),
        "rating_in": f"{rating_in:.1f}",
        "ac_in": ac_in,
        "pred_rp_fmt": hasil["pred_rp_fmt"],
        "hist_labels": hasil["chart_data"]["hist_labels"],
        "hist_counts": hasil["chart_data"]["hist_counts"],
        "rating_labels": hasil["chart_data"]["rating_labels"],
        "rating_texts": hasil["chart_data"]["rating_texts"],
    }
    ai_insight = buat_keterangan_grafik(ringkasan_grafik)

    context = {
        "jarak_in": f"{jarak_in:.2f}",
        "budget_in": budget_in,
        "budget_fmt": f"Rp {budget_in:,}".replace(",", "."),
        "rating_in": f"{rating_in:.1f}",
        "ac_in": ac_in,
        "min_jarak": f"{MIN_JARAK:.2f}",
        "max_jarak": f"{MAX_JARAK:.2f}",
        "min_budget": MIN_BUDGET,
        "max_budget": MAX_BUDGET,
        "min_rating": f"{MIN_RATING:.1f}",
        "max_rating": f"{MAX_RATING:.1f}",
        "pred_rp_fmt": hasil["pred_rp_fmt"],
        "ket_budget": hasil["ket_budget"],
        "masuk_budget": hasil["masuk_budget"],
        "empat_kos": hasil["empat_kos"],
        "semua_kos": hasil["semua_kos"],
        "chart_data_json": json.dumps(hasil["chart_data"]),
        "ai_insight": ai_insight,
    }
    return render(request, "prediksi/index.html", context)