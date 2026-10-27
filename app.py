
import streamlit as st
import pandas as pd
from google.cloud import bigquery
from sheets_helper import get_sheet
from datetime import datetime
PROJECT_ID = "ai-prediksi-bbm-kapal"
MODEL_ID = f"{PROJECT_ID}.vessel_ai.model_bbm_v2"

st.set_page_config(
    page_title="Vessel Fuel AI",
    page_icon="🚢",
    layout="wide",
)

@st.cache_resource
def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)

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
        sql = f"""
        SELECT *
        FROM ML.PREDICT(
          MODEL `{MODEL_ID}`,
          (
            SELECT
              @jenis_kapal AS jenis_kapal,
              CAST(@jarak_tempuh_nm AS INT64) AS jarak_tempuh_nm,
              CAST(@durasi_jam AS INT64) AS durasi_jam,
              CAST(@muatan_ton AS INT64) AS muatan_ton
          )
        )
        """

        parameters = [
            bigquery.ScalarQueryParameter(
                "jenis_kapal", "STRING", jenis_kapal
            ),
            bigquery.ScalarQueryParameter(
                "jarak_tempuh_nm", "FLOAT64", jarak_tempuh_nm
            ),
            bigquery.ScalarQueryParameter(
                "durasi_jam", "FLOAT64", durasi_jam
            ),
            bigquery.ScalarQueryParameter(
                "muatan_ton", "FLOAT64", muatan_ton
            ),
        ]

        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=parameters
            )

            with st.spinner("Model AI sedang menghitung..."):
                client = get_bigquery_client()
                rows = list(
                    client.query(
                        sql, job_config=job_config
                    ).result()
                )

            if not rows:
                st.warning("Model tidak menghasilkan prediksi.")
            else:
                result = dict(rows[0])
                prediction = result.get(
                    "predicted_konsumsi_bbm_liter"
                )

                if prediction is None:
                    st.error("Kolom prediksi tidak ditemukan.")
                    st.write("Kolom yang diterima:", list(result.keys()))
                else:
                    
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
                          st.success("Prediksi berhasil dan tersimpan ke Google Sheets!")
                    except Exception as save_error:
                          st.warning("Prediksi berhasil, tetapi gagal menyimpan riwayat.")
                          st.code(str(save_error))



                    # Kartu metrik
                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Estimasi konsumsi BBM",
                        f"{prediction:,.2f} liter",
                    )
                    col2.metric("Jarak tempuh", f"{jarak_tempuh_nm:g} NM")
                    col3.metric("Durasi perjalanan", f"{durasi_jam:g} jam")

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

st.divider()
st.subheader("🕘 Riwayat Prediksi")

try:
    history_sql = f"""
    SELECT
        prediction_time,
        jenis_kapal,
        jarak_tempuh_nm,
        durasi_jam,
        muatan_ton,
        predicted_konsumsi_bbm_liter
    FROM `{PROJECT_ID}.vessel_ai.prediction_history`
    ORDER BY prediction_time DESC
    LIMIT 20
    """

    history_df = get_bigquery_client().query(history_sql).to_dataframe()

    if history_df.empty:
        st.info("Belum ada riwayat prediksi.")
    else:
        history_df["prediction_time"] = (
            history_df["prediction_time"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )
        st.dataframe(
            history_df,
            hide_index=True,
            use_container_width=True
        )

except Exception as e:
    st.error("Riwayat prediksi gagal dimuat.")
    st.code(str(e))


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
