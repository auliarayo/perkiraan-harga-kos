from pathlib import Path
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

MIN_JARAK = 0.50
MAX_JARAK = 5.00
MIN_BUDGET = 500_000
MAX_BUDGET = 1_500_000


def format_rp(nilai: float) -> str:
    return f"Rp {int(round(nilai)):,}".replace(",", ".")


def format_jt(nilai_rp: float) -> str:
    if nilai_rp >= 1_000_000:
        return f"{nilai_rp / 1_000_000:.2f}jt".replace(".", ",")
    return f"{int(round(nilai_rp / 1_000))}rb"


def muat_dataset() -> pd.DataFrame:
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "kos_madiun.csv"
    df = pd.read_csv(csv_path)
    df["ac_bersih"] = df["ac"].astype(str).str.strip().str.lower()
    df["ac_bin"] = (df["ac_bersih"] == "ya").astype(int)
    df["harga_rp"] = df["harga"].astype(float).apply(lambda x: x * 1000 if x < 10_000 else x)
    return df


def latih_model_rf(df: pd.DataFrame):
    X = df[["jarak_km", "ac_bin", "rating"]]
    y = df["harga_rp"]
    X_latih, X_uji, y_latih, y_uji = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_latih, y_latih)
    mae = float(mean_absolute_error(y_uji, model.predict(X_uji)))
    return model, mae


def proses_prediksi_dan_rekomendasi(
    df: pd.DataFrame,
    model: RandomForestRegressor,
    jarak_in: float,
    budget_in: int,
    rating_in: float,
    ac_in: str,
):
    ac_pilihan = ac_in if ac_in in {"semua", "ya", "tidak"} else "semua"

    if ac_pilihan == "semua":
        df_pred = pd.DataFrame([
            {"jarak_km": jarak_in, "ac_bin": 1, "rating": rating_in},
            {"jarak_km": jarak_in, "ac_bin": 0, "rating": rating_in},
        ])
        pred_rp = float(model.predict(df_pred).mean())
        beda_ac = pd.Series(0.0, index=df.index)
    else:
        ac_bin_in = 1 if ac_pilihan == "ya" else 0
        df_pred = pd.DataFrame([{"jarak_km": jarak_in, "ac_bin": ac_bin_in, "rating": rating_in}])
        pred_rp = float(model.predict(df_pred)[0])
        beda_ac = (df["ac_bin"] != ac_bin_in).astype(float) * 0.4

    min_rating = float(df["rating"].min())
    max_rating = float(df["rating"].max())
    rentang_j = MAX_JARAK - MIN_JARAK
    rentang_b = MAX_BUDGET - MIN_BUDGET
    rentang_r = max(max_rating - min_rating, 0.1)

    skor_df = df.copy()
    skor_df["skor"] = (
        ((skor_df["jarak_km"] - jarak_in).abs() / rentang_j)
        + ((skor_df["harga_rp"] - budget_in).abs() / rentang_b)
        + ((skor_df["rating"] - rating_in).abs() / rentang_r)
        + beda_ac
    )

    top4_df = skor_df.sort_values("skor").head(4)
    empat_kos = []
    for _, row in top4_df.iterrows():
        harga_val = float(row["harga_rp"])
        status_budget = (
            "Sesuai" if harga_val <= budget_in else f"+{format_rp(harga_val - budget_in)}"
        )
        empat_kos.append({
            "nama": row["nama"],
            "jarak_fmt": f"{float(row['jarak_km']):.2f} km",
            "ac": row["ac_bersih"],
            "rating": f"{float(row['rating']):.1f}",
            "harga_fmt": format_rp(harga_val),
            "budget_status": status_budget,
        })

    semua_kos = []
    for _, row in df.iterrows():
        semua_kos.append({
            "nama": row["nama"],
            "jarak_fmt": f"{float(row['jarak_km']):.2f} km",
            "ac": row["ac_bersih"],
            "rating": f"{float(row['rating']):.1f}",
            "harga_fmt": format_rp(float(row["harga_rp"])),
        })

    counts, edges = pd.cut(df["harga_rp"], bins=8, retbins=True)
    hist_labels = [
        f"{format_jt(edges[i])}-{format_jt(edges[i + 1])}"
        for i in range(len(edges) - 1)
    ]
    hist_counts = counts.value_counts().sort_index().tolist()

    ya_df = df[df["ac_bin"] == 1]
    tdk_df = df[df["ac_bin"] == 0]
    scatter_ya = [
        {"x": float(r["jarak_km"]), "y": float(r["harga_rp"]), "nama": r["nama"]}
        for _, r in ya_df.iterrows()
    ]
    scatter_tdk = [
        {"x": float(r["jarak_km"]), "y": float(r["harga_rp"]), "nama": r["nama"]}
        for _, r in tdk_df.iterrows()
    ]

    grup_rating = pd.cut(
        df["rating"],
        bins=[0, 3.5, 4.2, 5.0],
        labels=["<= 3.5", "3.6 - 4.2", "> 4.2"],
    )
    rata_rating = df.groupby(grup_rating, observed=False)["harga_rp"].mean()
    rating_labels = [str(idx) for idx in rata_rating.index]
    rating_values = [0.0 if pd.isna(v) else float(v) for v in rata_rating.values]
    rating_texts = [format_jt(v) if v > 0 else "0" for v in rating_values]

    masuk_budget = pred_rp <= budget_in
    ket_budget = (
        f"Masih sesuai dengan budget kamu ({format_rp(budget_in)} / bulan)"
        if masuk_budget
        else f"Sedikit di atas budget kamu ({format_rp(budget_in)} / bulan)"
    )

    return {
        "pred_rp": pred_rp,
        "pred_rp_fmt": format_rp(pred_rp),
        "ket_budget": ket_budget,
        "masuk_budget": masuk_budget,
        "empat_kos": empat_kos,
        "semua_kos": semua_kos,
        "chart_data": {
            "budget_in": float(budget_in),
            "budget_fmt": format_rp(budget_in),
            "hist_labels": hist_labels,
            "hist_counts": hist_counts,
            "scatter_ya": scatter_ya,
            "scatter_tdk": scatter_tdk,
            "pred_point": {"x": float(jarak_in), "y": float(pred_rp)},
            "rating_labels": rating_labels,
            "rating_values": rating_values,
            "rating_texts": rating_texts,
        },
    }