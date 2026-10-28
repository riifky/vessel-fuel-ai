
import streamlit as st
import pandas as pd
from datetime import datetime


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Vessel Fuel AI",
    page_icon="🚢",
    layout="wide",
)


# =========================================================
# MODEL: LINEAR REGRESSION
# Bobot diambil dari BigQuery ML model_bbm_v2.
# Prediksi dihitung lokal agar aplikasi publik tidak
# memerlukan kredensial BigQuery.
# =========================================================

CATEGORY_WEIGHTS = {
    "Tugboat": 284.97867970439506,
    "SPOB": 414.30282565425694,
    "Crew Boat": 251.21849993806902,
}

INTERCEPT = -316.99367910222594
WEIGHT_DISTANCE = 3.3033492123938575
WEIGHT_DURATION = 28.226681305909175
WEIGHT_CARGO = 0.40528329218125553


def predict_fuel(
    jenis_kapal,
    jarak_tempuh_nm,
    durasi_jam,
    muatan_ton,
):
    """Menghitung estimasi konsumsi BBM dengan bobot model."""

    if jenis_kapal not in CATEGORY_WEIGHTS:
        raise ValueError("Jenis kapal tidak dikenali.")

    # Menyamakan tipe input dengan query BigQuery sebelumnya.
    jarak = int(jarak_tempuh_nm)
    durasi = int(durasi_jam)
    muatan = int(muatan_ton)

    prediction = (
        INTERCEPT
        + CATEGORY_WEIGHTS[jenis_kapal]
        + WEIGHT_DISTANCE * jarak
        + WEIGHT_DURATION * durasi
        + WEIGHT_CARGO * muatan
    )

    return max(0.0, float(prediction))


# =========================================================
# SESSION HISTORY
# Riwayat terpisah untuk setiap sesi pengunjung.
# =========================================================

if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []


# =========================================================
# HEADER
# =========================================================

st.title("🚢 Vessel Fuel AI")
st.caption(
    "Smart Maritime Fuel Prediction | "
    "Prototype berbasis model Linear Regression"
)

st.divider()


# =========================================================
# SIDEBAR INPUT
# =========================================================

with st.sidebar:
    st.header("⚙️ Parameter Kapal")
    st.write(
        "Masukkan data perjalanan untuk membuat prediksi."
    )

    jenis_kapal = st.selectbox(
        "Jenis kapal",
        ["Tugboat", "SPOB", "Crew Boat"],
    )

    jarak_tempuh_nm = st.number_input(
        "Jarak tempuh (NM)",
        min_value=0.0,
        value=40.0,
        step=5.0,
    )

    durasi_jam = st.number_input(
        "Durasi perjalanan (jam)",
        min_value=0.0,
        value=6.0,
        step=1.0,
    )

    muatan_ton = st.number_input(
        "Muatan (ton)",
        min_value=0.0,
        value=0.0,
        step=100.0,
    )

    predict_button = st.button(
        "🔍 Prediksi Konsumsi BBM",
        use_container_width=True,
        type="primary",
    )


# =========================================================
# PREDICTION
# =========================================================

st.subheader("Ringkasan Prediksi")
st.write(
    "Masukkan parameter di panel kiri, lalu jalankan prediksi."
)

if predict_button:

    if jarak_tempuh_nm <= 0 or durasi_jam <= 0:
        st.error(
            "Jarak dan durasi perjalanan harus lebih dari nol."
        )

    else:
        try:
            with st.spinner("Model AI sedang menghitung..."):
                prediction = predict_fuel(
                    jenis_kapal,
                    jarak_tempuh_nm,
                    durasi_jam,
                    muatan_ton,
                )

            # Simpan riwayat ke sesi pengguna.
            history_record = {
                "Waktu Prediksi": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Jenis Kapal": jenis_kapal,
                "Jarak (NM)": int(jarak_tempuh_nm),
                "Durasi (Jam)": int(durasi_jam),
                "Muatan (Ton)": int(muatan_ton),
                "Prediksi BBM (Liter)": round(
                    prediction, 2
                ),
            }

            st.session_state.prediction_history.append(
                history_record
            )

            # Kartu metrik.
            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Estimasi konsumsi BBM",
                f"{prediction:,.2f} liter",
            )

            col2.metric(
                "Jarak tempuh",
                f"{jarak_tempuh_nm:g} NM",
            )

            col3.metric(
                "Durasi perjalanan",
                f"{durasi_jam:g} jam",
            )

            st.success("Prediksi berhasil dihitung!")

            st.divider()
            st.subheader("Detail Perjalanan")

            details = pd.DataFrame({
                "Parameter": [
                    "Jenis kapal",
                    "Jarak tempuh",
                    "Durasi perjalanan",
                    "Muatan",
                ],
                "Nilai": [
                    jenis_kapal,
                    f"{jarak_tempuh_nm:g} NM",
                    f"{durasi_jam:g} jam",
                    f"{muatan_ton:g} ton",
                ],
            })

            st.dataframe(
                details,
                hide_index=True,
                use_container_width=True,
            )

            st.subheader("Profil Input Perjalanan")

            chart_data = pd.DataFrame({
                "Parameter": [
                    "Jarak (NM)",
                    "Durasi (jam)",
                    "Muatan (ton)",
                ],
                "Nilai": [
                    jarak_tempuh_nm,
                    durasi_jam,
                    muatan_ton,
                ],
            }).set_index("Parameter")

            st.bar_chart(chart_data)

            st.info(
                "Prototipe ini menggunakan bobot model hasil "
                "pelatihan sebelumnya. Hasil prediksi belum "
                "divalidasi untuk operasi kapal nyata."
            )

        except Exception as e:
            st.error("Prediksi gagal dijalankan.")
            st.code(str(e))

else:
    st.info(
        "👈 Atur parameter kapal di panel kiri, "
        "kemudian klik Prediksi Konsumsi BBM."
    )


# =========================================================
# PREDICTION HISTORY
# =========================================================

st.divider()
st.subheader("🕘 Riwayat Prediksi")

history = st.session_state.prediction_history

if history:
    history_df = pd.DataFrame(history)

    st.dataframe(
        history_df.iloc[::-1].head(20),
        hide_index=True,
        use_container_width=True,
    )

    if st.button("🗑️ Hapus Riwayat Sesi"):
        st.session_state.prediction_history = []
        st.rerun()

else:
    st.info(
        "Belum ada riwayat prediksi pada sesi ini."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()
st.caption(
    "Vessel Fuel AI • Portfolio Machine Learning"
)
