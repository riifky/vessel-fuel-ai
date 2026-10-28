
import streamlit as st
import pandas as pd
from sheets_helper import get_sheet
from datetime import datetime


def predict_fuel(
    jenis_kapal,
    jarak_tempuh_nm,
    durasi_jam,
    muatan_ton,
):
    category_weights = {
        "Tugboat": 284.97867970439506,
        "SPOB": 414.30282565425694,
        "Crew Boat": 251.21849993806902,
    }

    if jenis_kapal not in category_weights:
        raise ValueError("Jenis kapal tidak dikenali.")

    # Menyamakan input dengan SQL sebelumnya,
    # yang mengubah ketiga fitur numerik menjadi INT64.
    jarak = int(jarak_tempuh_nm)
    durasi = int(durasi_jam)
    muatan = int(muatan_ton)

    return (
        -316.99367910222594
        + category_weights[jenis_kapal]
        + 3.3033492123938575 * jarak
        + 28.226681305909175 * durasi
        + 0.40528329218125553 * muatan
    )


st.set_page_config(
    page_title="Vessel Fuel AI",
    page_icon="🚢",
    layout="wide",
)

# Header
st.title("🚢 Vessel Fuel AI")
st.caption(
    "Smart Maritime Fuel Prediction | "
    "Prototype berbasis Google Cloud BigQuery ML"
)

st.divider()

# Sidebar input
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

# Area utama
st.subheader("Ringkasan Prediksi")
st.write(
    "Masukkan parameter di panel kiri, lalu jalankan prediksi."
)

if predict_button:
    if jarak_tempuh_nm <= 0 or durasi_jam <= 0:
        st.error("Jarak dan durasi harus lebih dari nol.")
    else:
        try:
            with st.spinner("Model AI sedang menghitung..."):
                prediction = predict_fuel(
                    jenis_kapal,
                    jarak_tempuh_nm,
                    durasi_jam,
                    muatan_ton,
                )

            # Kartu metrik
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

            st.success("Prediksi berhasil dihitung.")

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

            # Simpan riwayat ke Google Sheets
            try:
                sheet = get_sheet()
                sheet.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    jenis_kapal,
                    int(jarak_tempuh_nm),
                    int(durasi_jam),
                    int(muatan_ton),
                    float(prediction),
                ])
                st.success(
                    "Riwayat prediksi berhasil disimpan ke Google Sheets."
                )
            except Exception as save_error:
                st.warning(
                    "Prediksi berhasil, tetapi riwayat belum tersimpan."
                )
                st.caption(str(save_error))

            st.info(
                "Ini adalah prototipe dengan data simulasi. "
                "Hasilnya belum tervalidasi untuk operasi kapal nyata."
            )

        except Exception as e:
            st.error("Prediksi gagal dijalankan.")
            st.code(str(e))

else:
    st.info(
        "👈 Atur parameter kapal di panel kiri, "
        "kemudian klik Prediksi Konsumsi BBM."
    )

# Riwayat prediksi dari Google Sheets
st.divider()
st.subheader("🕘 Riwayat Prediksi")

try:
    sheet = get_sheet()
    records = sheet.get_all_records()
    history_df = pd.DataFrame(records)

    if history_df.empty:
        st.info("Belum ada riwayat prediksi.")
    else:
        st.dataframe(
            history_df.tail(20).iloc[::-1],
            hide_index=True,
            use_container_width=True,
        )

except Exception as e:
    st.warning("Riwayat prediksi belum dapat dimuat.")
    st.caption(str(e))

st.divider()
st.caption(
    "Vessel Fuel AI • Prototype pembelajaran Machine Learning di GCP"
)
