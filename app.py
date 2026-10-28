
import streamlit as st
import pandas as pd
import requests

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Vessel Fuel AI",
    page_icon="🚢",
    layout="wide",
)

HISTORY_COLUMNS = [
    "Waktu Prediksi",
    "Jenis Kapal",
    "Jarak (NM)",
    "Durasi (Jam)",
    "Muatan (Ton)",
    "Prediksi BBM (Liter)",
]

# =========================================================
# MODEL: LINEAR REGRESSION
# Bobot tetap menggunakan hasil BigQuery ML model_bbm_v2.
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


def predict_fuel(jenis_kapal, jarak_tempuh_nm, durasi_jam, muatan_ton):
    if jenis_kapal not in CATEGORY_WEIGHTS:
        raise ValueError("Jenis kapal tidak dikenali.")

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
# GOOGLE SHEETS API
# =========================================================

def get_sheets_config():
    try:
        url = st.secrets["SHEETS_WEB_APP_URL"]
        token = st.secrets["SHEETS_API_TOKEN"]
    except Exception:
        raise RuntimeError(
            "Konfigurasi Google Sheets belum tersedia. "
            "Periksa Settings > Secrets di Streamlit Cloud."
        )

    if not url or not token:
        raise RuntimeError("URL atau token Google Sheets kosong.")

    return url, token


def get_prediction_history():
    url, token = get_sheets_config()

    response = requests.get(
        url,
        params={
            "action": "history",
            "token": token,
        },
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(
            result.get("message", "Gagal membaca riwayat spreadsheet.")
        )

    return result.get("history", [])


def save_prediction_history(record):
    url, token = get_sheets_config()

    payload = {
        "action": "append",
        "token": token,
        "row": [
            record["Waktu Prediksi"],
            record["Jenis Kapal"],
            record["Jarak (NM)"],
            record["Durasi (Jam)"],
            record["Muatan (Ton)"],
            record["Prediksi BBM (Liter)"],
        ],
    }

    response = requests.post(
        url,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(
            result.get("message", "Gagal menyimpan riwayat.")
        )

    return True


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
    st.write("Masukkan data perjalanan untuk membuat prediksi.")

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

if predict_button:
    if jarak_tempuh_nm <= 0 or durasi_jam <= 0:
        st.error("Jarak dan durasi perjalanan harus lebih dari nol.")
    else:
        try:
            with st.spinner("Model AI sedang menghitung..."):
                prediction = predict_fuel(
                    jenis_kapal,
                    jarak_tempuh_nm,
                    durasi_jam,
                    muatan_ton,
                )

            from datetime import datetime

            record = {
                "Waktu Prediksi": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Jenis Kapal": jenis_kapal,
                "Jarak (NM)": int(jarak_tempuh_nm),
                "Durasi (Jam)": int(durasi_jam),
                "Muatan (Ton)": int(muatan_ton),
                "Prediksi BBM (Liter)": round(prediction, 2),
            }

            # Penyimpanan tidak menghalangi hasil prediksi.
            saved = False
            save_error = None

            try:
                save_prediction_history(record)
                saved = True
            except Exception as e:
                save_error = str(e)

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

            if saved:
                st.success(
                    "Prediksi berhasil! Riwayat tersimpan di "
                    "Google Spreadsheet."
                )
            else:
                st.warning(
                    "Prediksi berhasil dihitung, tetapi riwayat "
                    "belum tersimpan ke spreadsheet."
                )
                with st.expander("Detail kesalahan penyimpanan"):
                    st.code(save_error)

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
# PREDICTION HISTORY FROM GOOGLE SPREADSHEET
# =========================================================

st.divider()
st.subheader("🕘 Riwayat Prediksi")

try:
    with st.spinner("Memuat riwayat dari Google Spreadsheet..."):
        history = get_prediction_history()

    if history:
        history_df = pd.DataFrame(
            history,
            columns=HISTORY_COLUMNS,
        )

        st.dataframe(
            history_df.head(20),
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "Riwayat ditampilkan dari Google Spreadsheet, "
            "terbaru terlebih dahulu."
        )
    else:
        st.info("Belum ada riwayat prediksi di spreadsheet.")

except Exception as e:
    st.error("Riwayat spreadsheet gagal dimuat.")
    st.caption(
        "Periksa URL deployment, token, izin Web app, "
        "dan nama tab spreadsheet."
    )
    with st.expander("Detail kesalahan"):
        st.code(str(e))

# =========================================================
# FOOTER
# =========================================================

st.divider()
st.caption("Vessel Fuel AI • Portfolio Machine Learning")
