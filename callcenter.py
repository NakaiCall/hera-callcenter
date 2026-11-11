from datetime import datetime
import io
import json
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import streamlit as st

st.set_page_config(
    page_title="NakaiCall - Multi-Agenzia & Presenze",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS Personalizzato
st.markdown(
    """
<style>
    .main-title { font-size: 26px; font-weight: 800; color: #003366; margin-bottom: 2px; }
    .sub-title { font-size: 14px; color: #555555; margin-bottom: 15px; }
    .card-box { background-color: #f8f9fa; border-radius: 12px; padding: 22px; border-left: 8px solid #0056b3; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); }
    .setup-box { background-color: #e0f2fe; border-radius: 12px; padding: 25px; border-left: 8px solid #0284c7; margin-bottom: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.08); }
    .warning-box { background-color: #f8d7da; border-radius: 10px; padding: 15px; border-left: 8px solid #dc3545; color: #721c24; margin-bottom: 15px; font-weight: bold; }
    
    .privacy-alert-popup { background-color: #fff3cd; border: 2px solid #ffecb5; border-radius: 10px; padding: 15px; color: #664d03; margin-bottom: 15px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); text-align: center; }
    
    .phone-highlight { font-size: 34px !important; font-weight: 900 !important; color: #d9534f !important; letter-spacing: 1.5px; margin: 10px 0; }
    .name-highlight { font-size: 28px !important; font-weight: 800 !important; color: #1b1e21 !important; }
    .status-badge-ok { background-color: #d4edda; color: #155724; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .status-badge-warn { background-color: #fff3cd; color: #856404; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    
    .privacy-yes { background-color: #d4edda; color: #155724; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 18px; display: inline-block; }
    .privacy-no { background-color: #f8d7da; color: #721c24; padding: 6px 12px; border-radius: 6px; font-weight: 900; font-size: 18px; display: inline-block; }

    .stButton>button { width: 100%; height: 45px; font-size: 15px; font-weight: bold; border-radius: 8px; }
    
    .energy-container { background: white; border-radius: 10px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    .energy-title { font-size: 14px; font-weight: bold; color: #334155; margin-bottom: 6px; display: flex; justify-content: space-between; }
    .progress-bar-bg { background-color: #e2e8f0; border-radius: 20px; height: 18px; width: 100%; overflow: hidden; }
    .progress-bar-fill-calls { background: linear-gradient(90deg, #3b82f6, #0056b3); height: 100%; border-radius: 20px; }
    .progress-bar-fill-apps { background: linear-gradient(90deg, #f59e0b, #10b981); height: 100%; border-radius: 20px; }
</style>
""",
    unsafe_allow_html=True,
)

DB_NAME = "hera_shared_calls.db"
DESTINATARI_EMAIL = [
    "giulianalavoro1@gmail.com",
    "fabio.asilo.office@consulenti.gruppohera.it",
    "nakaisrls@gmail.com",
]


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            foglio TEXT,
            telefono TEXT,
            nome TEXT,
            codice_fiscale TEXT,
            dati_json TEXT,
            esito TEXT DEFAULT '',
            data_ora_esito TEXT DEFAULT '',
            postazione TEXT DEFAULT '',
            operatore TEXT DEFAULT '',
            sede_appuntamento TEXT DEFAULT '',
            note TEXT DEFAULT ''
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            ruolo TEXT,
            postazione TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS presenze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            postazione TEXT,
            tipo TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS impostazioni_email (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            smtp_server TEXT,
            smtp_port INTEGER,
            sender_email TEXT,
            sender_pass TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def invia_email_notifica(oggetto, messaggio, attachment_bytes=None, attachment_name=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT smtp_server, smtp_port, sender_email, sender_pass FROM impostazioni_email ORDER BY id DESC LIMIT 1")
    cfg = cursor.fetchone()
    conn.close()

    if not cfg:
        return False, "Configurazione SMTP non trovata. Inseriscila nella sezione Master."

    smtp_server, smtp_port, sender_email, sender_pass = cfg
    if not sender_email or not sender_pass:
        return False, "Credenziali email mittente non configurate."

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = ", ".join(DESTINATARI_EMAIL)
        msg["Subject"] = oggetto

        msg.attach(MIMEText(messaggio, "plain"))

        if attachment_bytes and attachment_name:
            part = MIMEApplication(attachment_bytes, Name=attachment_name)
            part["Content-Disposition"] = f'attachment; filename="{attachment_name}"'
            msg.attach(part)

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, DESTINATARI_EMAIL, msg.as_string())
        server.quit()
        return True, "Email inviata con successo!"
    except Exception as e:
        return False, f"Errore invio email: {e}"


def get_all_shared_dataframe():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM clienti", conn)
    conn.close()
    return df


def get_today_stats(operatore):
    conn = sqlite3.connect(DB_NAME)
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE ? AND esito != 'Scartato / Fuori Provincia'",
        (operatore, f"{today_str}%"),
    )
    chiamate_oggi = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE ? AND esito = 'Appuntamento Confermato'",
        (operatore, f"{today_str}%"),
    )
    appuntamenti_oggi = cursor.fetchone()[0] or 0
    conn.close()
    return chiamate_oggi, appuntamenti_oggi


def calcola_ore_lavorate(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tipo, timestamp FROM presenze WHERE username = ? ORDER BY timestamp ASC",
        (username,),
    )
    timbrature = cursor.fetchall()
    conn.close()

    ore_oggi = 0.0
    ore_mese = 0.0
    today_str = datetime.now().strftime("%Y-%m-%d")
    month_str = datetime.now().strftime("%Y-%m")
    ultimo_ingresso = None

    for tipo, t_str in timbrature:
        try:
            dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
        except:
            continue

        if tipo == "ENTRATA":
            ultimo_ingresso = dt
        elif tipo == "USCITA" and ultimo_ingresso is not None:
            delta = (dt - ultimo_ingresso).total_seconds() / 3600.0
            if delta > 0:
                if dt.strftime("%Y-%m-%d") == today_str:
                    ore_oggi += delta
                if dt.strftime("%Y-%m") == month_str:
                    ore_mese += delta
            ultimo_ingresso = None

    if ultimo_ingresso is not None:
        dt_now = datetime.now()
        if ultimo_ingresso.strftime("%Y-%m-%d") == today_str:
            delta = (dt_now - ultimo_ingresso).total_seconds() / 3600.0
            if delta > 0:
                ore_oggi += delta
                ore_mese += delta

    return round(ore_oggi, 2), round(ore_mese, 2)


def get_timbrature_dataframe(username=None):
    conn = sqlite3.connect(DB_NAME)
    if username:
        df = pd.read_sql_query("SELECT username as Operatore, postazione as Postazione, tipo as Tipo, timestamp as DataOra FROM presenze WHERE username = ? ORDER BY timestamp DESC", conn, params=(username,))
    else:
        df = pd.read_sql_query("SELECT username as Operatore, postazione as Postazione, tipo as Tipo, timestamp as DataOra FROM presenze ORDER BY timestamp DESC", conn)
    conn.close()
    return df


def update_call_in_db(record_id, esito, postazione, operatore, sede_appuntamento, note):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE clienti 
        SET esito = ?, data_ora_esito = ?, postazione = ?, operatore = ?, sede_appuntamento = ?, note = ?
        WHERE id = ?
    """,
        (esito, timestamp, postazione, operatore, sede_appuntamento, note, int(record_id)),
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM clienti WHERE esito = '' OR esito IS NULL")
    rimanenti = cursor.fetchone()[0] or 0
    conn.close()

    if rimanenti < 120:
        today_marker = datetime.now().strftime("%Y-%m-%d")
        alert_key = f"alert_120_inviato_{today_marker}"
        if alert_key not in st.session_state:
            st.session_state[alert_key] = True
            msg_alert = f"ATTENZIONE: La lista chiamate di NakaiCall è quasi esaurita!\nRimangono solamente {rimanenti} clienti da chiamare.\nSi prega di caricare una nuova lista al più presto."
            invia_email_notifica("🚨 ALERT: Scorta Nomi NakaiCall Sotto i 120!", msg_alert)


def pulisci_telefono(tel):
    if pd.isna(tel) or not tel:
        return "N/D"
    t_str = str(tel).strip()
    if t_str.endswith(".0"):
        t_str = t_str[:-2]
    return t_str


def format_dataframe_for_export(df_db):
    export_list = []
    for _, r in df_db.iterrows():
        try:
            d = json.loads(r["dati_json"])
        except:
            d = {}

        d.pop("foglio", None)
        d.pop("Foglio", None)

        nome = r["nome"]
        cf = r["codice_fiscale"]
        tel = r["telefono"]

        new_d = {}
        new_d["NOME"] = nome
        new_d["CODICE FISCALE"] = cf
        new_d["TELEFONO"] = tel

        for k, v in d.items():
            k_upper = str(k).strip().upper()
            if k_upper not in ["NOME", "CLIENTE", "CODICE FISCALE", "TELEFONO", "TEL"]:
                new_d[k] = v

        new_d["Esito Chiamata"] = r["esito"] if r["esito"] else "Non Chiamato"
        new_d["Data Ora Chiamata"] = r["data_ora_esito"]
        new_d["Operatore"] = r["operatore"]
        new_d["Postazione Sede"] = r["postazione"]
        new_d["Sede Appuntamento"] = r["sede_appuntamento"]
        new_d["Note Operatore"] = r["note"]

        export_list.append(new_d)

    return pd.DataFrame(export_list)


def estrai_dati_excel_puliti(uploaded_file):
    excel_file = pd.ExcelFile(uploaded_file)
    tutti_i_record = []

    for sheet in excel_file.sheet_names:
        df_temp = pd.read_excel(uploaded_file, header=None, sheet_name=sheet)
        header_row = 0
        for idx, row in df_temp.iterrows():
            row_str = " ".join([str(v).lower() for v in row.values if pd.notna(v)])
            matches = sum(1 for k in ["telefono", "tel", "cliente", "nominativo", "codice fiscale", "residenza", "esito"] if k in row_str)
            if matches >= 2:
                header_row = idx
                break

        df_sheet = pd.read_excel(uploaded_file, header=header_row, sheet_name=sheet)
        df_sheet.columns = [str(c).strip() for c in df_sheet.columns]

        for _, row in df_sheet.iterrows():
            row_dict = row.to_dict()

            def cerca_val(keys):
                d_norm = {str(k).strip().upper(): v for k, v in row_dict.items() if k is not None}
                for k in keys:
                    if k.upper() in d_norm:
                        val = d_norm[k.upper()]
                        if not pd.isna(val) and str(val).strip().lower() not in ["nan", "n/d", ""]:
                            return str(val).strip()
                for k, v in d_norm.items():
                    for key in keys:
                        if key.upper() in k:
                            if not pd.isna(v) and str(v).strip().lower() not in ["nan", "n/d", ""]:
                                return str(v).strip()
                return "N/D"

            tel_raw = cerca_val(["TELEFONO", "TEL", "CELLULARE", "CELL", "RECAPITO"])
            tel = pulisci_telefono(tel_raw)
            nome = cerca_val(["CLIENTE", "NOMINATIVO", "REFERENTE TITOLARE", "RAGIONE SOCIALE", "NOME", "COGNOME E NOME"])
            if not nome or nome.lower() in ["nan", "n/d", ""]:
                nome = "Cliente Sconosciuto"

            cf = cerca_val(["CODICE FISCALE", "CF", "PARTITA IVA", "P.IVA", "CODICE_FISCALE"])
            indirizzo = cerca_val(["RESIDENZA", "INDIRIZZO RESIDENZA", "INDIRIZZO", "VIA", "SEDE"])
            luce = cerca_val(["LUCE", "STATO LUCE", "STATO_LUCE"])
            gas = crestato = cerca_val(["GAS", "STATO GAS", "STATO_GAS"])
            data_verifica = cerca_val(["DATA VERIFICA", "DATA", "DATA_VERIFICA"])
            note_det = cerca_val(["NOTE DETTAGLIATE", "NOTE", "DETTAGLI", "NOTE_DETTAGLIATE"])
            esito_file = cerca_val(["ESITO", "STATO FORNITURA", "ESITO_FORNITURA"])
            privacy = cerca_val(["PRIVACY MARKETING", "PRIVACY", "CONSENSO", "PRIVACY PROFILAZIONE", "TRATTAMENTO DATI"])

            record_pulito = {
                "foglio": sheet,
                "telefono": tel,
                "nome": nome,
                "codice_fiscale": cf,
                "indirizzo": indirizzo,
                "luce": luce,
                "gas": crestato,
                "data_verifica": data_verifica,
                "note_dettagliate": note_det,
                "esito_file": esito_file,
                "privacy": privacy,
            }
            tutti_i_record.append(record_pulito)

    return tutti_i_record


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "postazione" not in st.session_state:
    st.session_state.postazione = ""
if "force_setup" not in st.session_state:
    st.session_state.force_setup = False

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("SELECT username FROM utenti")
utenti_esistenti = [row[0] for row in cursor.fetchall()]
conn.close()

if len(utenti_esistenti) == 0 or st.session_state.force_setup:
    st.markdown("<h1 style='text-align: center; color: #0284c7;'>⚙️ Inizializzazione Nuova Agenzia</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="setup-box">', unsafe_allow_html=True)
        setup_user = st.text_input("Username Amministratore / Titolare", value="")
        setup_pass = st.text_input("Password Master Segreta", type="password", placeholder="Scegli password")
        setup_postazione = st.text_input("Nome Sede Principale", value="Sede Principale")

        if st.button("🚀 Attiva Agenzia e Crea Master"):
            if setup_user.strip() and setup_pass.strip():
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO utenti (username, password, ruolo, postazione)
                        VALUES (?, ?, ?, ?)
                    """,
                        (setup_user.strip(), setup_pass.strip(), "ADMIN", setup_postazione.strip()),
                    )
                    conn.commit()
                    conn.close()
                    st.session_state.force_setup = False
                    st.success("✅ Account Master creato con successo!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Username già esistente.")
            else:
                st.warning("⚠️ Compila tutti i campi.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center; color: #003366;'>📞 Accesso NakaiCall</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        selected_user = st.selectbox("👤 Seleziona Utente", utenti_esistenti)
        login_pass = st.text_input("🔑 Inserisci Password", type="password")

        if st.button("🚀 Accedi"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT ruolo, postazione FROM utenti WHERE username = ? AND password = ?", (selected_user, login_pass))
            res = cursor.fetchone()
            conn.close()
            if res:
                st.session_state.logged_in = True
                st.session_state.username = selected_user
                st.session_state.role = res[0]
                st.session_state.postazione = res[1]
                st.rerun()
            else:
                st.error("❌ Password non corretta.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- BARRA LATERALE ---
st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.markdown(f"**Ruolo:** {st.session_state.role}")
st.sidebar.markdown(f"**Postazione:** {st.session_state.postazione}")

if st.session_state.role == "OPERATORE":
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⏱️ Il tuo Cartellino Presenze")
    ore_oggi_sidebar, ore_mese_sidebar = calcola_ore_lavorate(st.session_state.username)
    st.sidebar.info(f"⏳ **Ore Oggi:** {ore_oggi_sidebar}h\n\n📅 **Ore Mese:** {ore_mese_sidebar}h")

    col_s1, col_s2 = st.sidebar.columns(2)
    with col_s1:
        if st.button("🟢 Entrata"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO presenze (username, postazione, tipo, timestamp) VALUES (?, ?, ?, ?)",
                (st.session_state.username, st.session_state.postazione, "ENTRATA", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
            st.sidebar.success("Entrata timbrata!")
            st.rerun()
    with col_s2:
        if st.button("🔴 Uscita"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO presenze (username, postazione, tipo, timestamp) VALUES (?, ?, ?, ?)",
                (st.session_state.username, st.session_state.postazione, "USCITA", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
            conn.close()
            st.sidebar.success("Uscita timbrata!")
            st.rerun()

    df_miei_orari = get_timbrature_dataframe(st.session_state.username)
    if not df_miei_orari.empty:
        out_ore_op = io.BytesIO()
        with pd.ExcelWriter(out_ore_op, engine="openpyxl") as writer:
            df_sum_ore = pd.DataFrame([{"Operatore": st.session_state.username, "Ore Oggi (h)": ore_oggi_sidebar, "Ore Mese (h)": ore_mese_sidebar}])
            df_sum_ore.to_excel(writer, index=False, sheet_name="RIEPILOGO_ORE")
            df_miei_orari.to_excel(writer, index=False, sheet_name="TIMBRATURE")
        excel_ore_op = out_ore_op.getvalue()

        st.sidebar.download_button(
            label="⏱️ Scarica Excel Ore Lavorate",
            data=excel_ore_op,
            file_name=f"ore_lavorate_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Scarica i tuoi Risultati Chiamate")
    df_all_op = get_all_shared_dataframe()
    df_miei_lavorati = df_all_op[df_all_op["operatore"] == st.session_state.username]

    if not df_miei_lavorati.empty:
        df_miei_final = format_dataframe_for_export(df_miei_lavorati)
        output_op = io.BytesIO()
        with pd.ExcelWriter(output_op, engine="openpyxl") as writer:
            df_miei_final.to_excel(writer, index=False, sheet_name="MIEI_RISULTATI_CHIAMATE")
        excel_data_op = output_op.getvalue()

        st.sidebar.download_button(
            label=f"📥 Scarica Esiti Personali ({len(df_miei_final)} chiamate)",
            data=excel_data_op,
            file_name=f"esiti_personali_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.sidebar.info("Nessuna chiamata effettuata finora.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Da Chiamare per Comune")
df_full_check = get_all_shared_dataframe()
if not df_full_check.empty:
    comuni_list = []
    for _, r in df_full_check.iterrows():
        try:
            d = json.loads(r["dati_json"])
        except:
            d = {}
        ind = d.get("indirizzo", "")
        comune_trovato = "ALTRO"
        for c_key in ["SPILIMBERGO", "SAN MARTINO", "CODROIPO", "PORDENONE", "ZOPPOLA", "CASARSA", "SAN VITO", "MANIAGO", "BRUGNERA", "UDINE", "FANNA"]:
            if c_key in str(ind).upper():
                comune_trovato = c_key
                break
        comuni_list.append({"comune": comune_trovato, "esito": r["esito"]})

    df_c_stat = pd.DataFrame(comuni_list)
    df_da_chiamare = df_c_stat[(df_c_stat["esito"] == "") | (df_c_stat["esito"].isna())]
    if not df_da_chiamare.empty:
        for com, num in df_da_chiamare["comune"].value_counts().items():
            st.sidebar.markdown(f"📍 **{com}**: <span style='color: #d9534f; font-weight: bold;'>{num} da chiamare</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Esci / Logout"):
    st.session_state.logged_in = False
    st.rerun()

# 2. MASTER ACCOUNT
if st.session_state.role == "ADMIN":
    st.markdown('<div class="main-title">🛠️ Master Account - Amministrazione & Statistiche</div>', unsafe_allow_html=True)

    with st.expander("👥 Gestione Collaboratori & Password", expanded=False):
        col_u1, col_u2, col_u3, col_u4 = st.columns(4)
        with col_u1:
            new_username = st.text_input("Nome Operatore / Username")
        with col_u2:
            new_password = st.text_input("Password Operatore", type="password")
        with col_u3:
            new_ruolo = st.selectbox("Ruolo Account", ["OPERATORE", "ADMIN"])
        with col_u4:
            new_postazione = st.text_input("Sede / Postazione", value="Sede 1")

        if st.button("💾 Registra Operatore"):
            if new_username and new_password:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO utenti (username, password, ruolo, postazione)
                        VALUES (?, ?, ?, ?)
                    """,
                        (new_username.strip(), new_password.strip(), new_ruolo, new_postazione.strip()),
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Operatore {new_username} registrato!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Username già esistente.")
            else:
                st.warning("⚠️ Compila tutti i campi.")

        st.markdown("---")
        st.subheader("🔑 Modifica Password Master")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            nuova_pass_master = st.text_input("Nuova Password", type="password", key="new_master_pass")
        with col_p2:
            conferma_pass_master = st.text_input("Conferma Password", type="password", key="conf_master_pass")
        if st.button("🔒 Aggiorna Password Master"):
            if nuova_pass_master and nuova_pass_master == conferma_pass_master:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("UPDATE utenti SET password = ? WHERE username = ?", (nuova_pass_master.strip(), st.session_state.username))
                conn.commit()
                conn.close()
                st.success("✅ Password aggiornata con successo!")
            else:
                st.warning("⚠️ Le password non coincidono.")

    with st.expander("📧 Configurazione e Invio Email Automatiche", expanded=False):
        st.subheader("⚙️ Configurazione Account SMTP Mittente (es. Gmail)")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT smtp_server, smtp_port, sender_email, sender_pass FROM impostazioni_email ORDER BY id DESC LIMIT 1")
        saved_cfg = cursor.fetchone()
        conn.close()

        s_srv = saved_cfg[0] if saved_cfg else "smtp.gmail.com"
        s_prt = saved_cfg[1] if saved_cfg else 587
        s_eml = saved_cfg[2] if saved_cfg else ""
        s_pss = saved_cfg[3] if saved_cfg else ""

        c_e1, c_e2 = st.columns(2)
        with c_e1:
            smtp_server_in = st.text_input("Server SMTP", value=s_srv)
            smtp_port_in = st.number_input("Porta SMTP", value=int(s_prt))
        with c_e2:
            sender_email_in = st.text_input("Email Mittente (es. tuamail@gmail.com)", value=s_eml)
            sender_pass_in = st.text_input("Password per le App Google", type="password", value=s_pss)

        if st.button("💾 Salva Configurazione Email"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO impostazioni_email (smtp_server, smtp_port, sender_email, sender_pass) VALUES (?, ?, ?, ?)",
                (smtp_server_in, int(smtp_port_in), sender_email_in.strip(), sender_pass_in.strip()),
            )
            conn.commit()
            conn.close()
            st.success("✅ Configurazione email salvata!")

        st.markdown("---")
        st.subheader("📤 Invio Manuale Report Globale via Email")
        st.markdown("Invio immediato dell'Excel completo a: " + ", ".join(DESTINATARI_EMAIL))
        if st.button("📧 Invia Excel Completo via Email a Tutti"):
            df_glob_mail = get_all_shared_dataframe()
            if not df_glob_mail.empty:
                df_glob_mail_fin = format_dataframe_for_export(df_glob_mail)
                out_mail = io.BytesIO()
                with pd.ExcelWriter(out_mail, engine="openpyxl") as writer:
                    df_glob_mail_fin.to_excel(writer, index=False, sheet_name="RISULTATI_GLOBALI")
                excel_bytes = out_mail.getvalue()
                file_n = f"risultati_globali_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

                successo, msg_esito = invia_email_notifica(
                    "📊 Report Globale Clienti - NakaiCall",
                    "In allegato il report excel globale aggiornato di tutti i clienti gestiti in NakaiCall.",
                    attachment_bytes=excel_bytes,
                    attachment_name=file_n,
                )
                if successo:
                    st.success("✅ " + msg_esito)
                else:
                    st.error("❌ " + msg_esito)
            else:
                st.warning("⚠️ Nessun dato presente nel database.")

    with st.expander("📊 Statistiche Dettagliate e Ore Lavorate per Utente", expanded=True):
        st.subheader("📋 Tabella Riepilogativa Attività e Ore per Dipendente")
        conn = sqlite3.connect(DB_NAME)
        df_clienti_all = pd.read_sql_query("SELECT * FROM clienti", conn)
        df_presenze_all = pd.read_sql_query("SELECT * FROM presenze", conn)
        conn.close()

        df_rimanenti_master = df_clienti_all[(df_clienti_all["esito"] == "") | (df_clienti_all["esito"].isna())]
        tot_rimanenti = len(df_rimanenti_master)

        st.markdown(
            f"""
        <div style="background-color: #e0f2fe; padding: 15px; border-radius: 10px; border-left: 6px solid #0284c7; margin-bottom: 20px;">
            <span style="font-size: 18px; font-weight: bold; color: #0369a1;">📍 Clienti totali rimasti da chiamare: {tot_rimanenti}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        comuni_rimanenti_list = []
        for _, r in df_rimanenti_master.iterrows():
            try:
                d = json.loads(r["dati_json"])
            except:
                d = {}
            ind = d.get("indirizzo", "")
            comune_trovato = "ALTRO"
            for c_key in ["SPILIMBERGO", "SAN MARTINO", "CODROIPO", "PORDENONE", "ZOPPOLA", "CASARSA", "SAN VITO", "MANIAGO", "BRUGNERA", "UDINE", "FANNA"]:
                if c_key in str(ind).upper():
                    comune_trovato = c_key
                    break
            comuni_rimanenti_list.append(comune_trovato)

        if comuni_rimanenti_list:
            s_comuni = pd.Series(comuni_rimanenti_list).value_counts()
            cols_comuni = st.columns(min(len(s_comuni), 4))
            idx_c = 0
            for com, count in s_comuni.items():
                with cols_comuni[idx_c % len(cols_comuni)]:
                    st.metric(label=f"Comune: {com}", value=f"{count} rimasti")
                idx_c += 1

        st.markdown("---")

        cursor = sqlite3.connect(DB_NAME).cursor()
        cursor.execute("SELECT username FROM utenti WHERE ruolo = 'OPERATORE'")
        lista_ops = [r[0] for r in cursor.fetchall()]

        if lista_ops:
            report_data = []
            tot_chiamate_generale = 0
            tot_ore_generale = 0.0

            for op in lista_ops:
                df_op_calls = df_clienti_all[df_clienti_all["operatore"] == op]
                num_chiamate = len(df_op_calls[df_op_calls["esito"] != "Scartato / Fuori Provincia"])
                num_appuntamenti = len(df_op_calls[df_op_calls["esito"] == "Appuntamento Confermato"])
                num_non_risp = len(df_op_calls[df_op_calls["esito"] == "Non Risponde / Occupato"])
                num_scartati = len(df_op_calls[df_op_calls["esito"] == "Scartato / Fuori Provincia"])

                o_oggi, o_mese = calcola_ore_lavorate(op)
                tot_chiamate_generale += num_chiamate
                tot_ore_generale += o_mese

                report_data.append({
                    "Operatore": op,
                    "Chiamate Fatte": num_chiamate,
                    "Appuntamenti Presi": num_appuntamenti,
                    "Non Risposto": num_non_risp,
                    "Scartati / Fuori Provincia": num_scartati,
                    "Ore Oggi (h)": o_oggi,
                    "Ore Mese (h)": o_mese,
                })

            df_report_stat = pd.DataFrame(report_data)
            st.dataframe(df_report_stat, use_container_width=True)

            st.markdown("---")
            col_tot1, col_tot2 = st.columns(2)
            with col_tot1:
                st.markdown(f"📞 **Totale Generale Chiamate Fatte:** <b>{tot_chiamate_generale}</b>", unsafe_allow_html=True)
            with col_tot2:
                st.markdown(f"⏱️ **Totale Generale Ore Lavorate (Mese):** <b>{round(tot_ore_generale, 2)} h</b>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_dwn1, col_dwn2 = st.columns(2)

            # Bottone 1: Report Timbrature e Statistiche ore
            output_p = io.BytesIO()
            with pd.ExcelWriter(output_p, engine="openpyxl") as writer:
                df_report_stat.to_excel(writer, index=False, sheet_name="STATISTICHE_UTENTI")
                df_presenze_all.to_excel(writer, index=False, sheet_name="TIMBRATURE_GREZZE")
            excel_p_data = output_p.getvalue()

            with col_dwn1:
                st.download_button(
                    label="📥 Scarica Report Timbrature e Ore in Excel",
                    data=excel_p_data,
                    file_name=f"report_statistiche_ore_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # Bottone 2: Report Globale di TUTTI i risultati chiamate (di tutti gli user)
            if not df_clienti_all.empty:
                df_export_final = format_dataframe_for_export(df_clienti_all)
                output_glob = io.BytesIO()
                with pd.ExcelWriter(output_glob, engine="openpyxl") as writer:
                    df_export_final.to_excel(writer, index=False, sheet_name="TUTTI_I_RISULTATI")
                    df_scartati = df_export_final[df_export_final["Esito Chiamata"] == "Scartato / Fuori Provincia"]
                    df_scartati.to_excel(writer, index=False, sheet_name="SOLO_SCARTATI")
                    df_confermati = df_export_final[df_export_final["Esito Chiamata"] == "Appuntamento Confermato"]
                    df_confermati.to_excel(writer, index=False, sheet_name="APPUNTAMENTI_CONFERMATI")
                excel_glob_data = output_glob.getvalue()

                with col_dwn2:
                    st.download_button(
                        label="📥 Scarica Excel Globale Tutti Risultati Chiamate",
                        data=excel_glob_data,
                        file_name=f"report_completo_risultati_chiamate_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
        else:
            st.info("Nessun operatore registrato.")

    with st.expander("📥 Caricamento e Gestione Clienti Excel", expanded=False):
        uploaded_file = st.file_uploader("Carica file Excel (.xlsx) per verifica", type=["xlsx"])
        if uploaded_file is not None:
            try:
                preview_records = estrai_dati_excel_puliti(uploaded_file)
                df_preview = pd.DataFrame(preview_records)
                st.info(f"🔍 **Controllo Riuscito!** Trovati **{len(preview_records)}** record.")
                if st.button("🚀 Conferma e Importa nel Database Centrale"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM clienti")
                    for rec in preview_records:
                        cursor.execute(
                            """
                            INSERT INTO clienti (foglio, telefono, nome, codice_fiscale, dati_json, esito)
                            VALUES (?, ?, ?, ?, ?, '')
                        """,
                            (rec["foglio"], rec["telefono"], rec["nome"], rec["codice_fiscale"], json.dumps(rec, ensure_ascii=False)),
                        )
                    conn.commit()
                    conn.close()
                    st.success("✅ Importazione completata!")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Errore: {e}")

        st.markdown("---")
        st.subheader("📊 Esporta Tutti i Risultati Chiamate e Clienti in Excel (Tutti gli Esiti)")
        df_export_db = get_all_shared_dataframe()
        if not df_export_db.empty:
            df_export_final = format_dataframe_for_export(df_export_db)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_export_final.to_excel(writer, index=False, sheet_name="TUTTI_I_RISULTATI")
                df_scartati = df_export_final[df_export_final["Esito Chiamata"] == "Scartato / Fuori Provincia"]
                df_scartati.to_excel(writer, index=False, sheet_name="SOLO_SCARTATI")
                df_confermati = df_export_final[df_export_final["Esito Chiamata"] == "Appuntamento Confermato"]
                df_confermati.to_excel(writer, index=False, sheet_name="APPUNTAMENTI_CONFERMATI")
                
            excel_data = output.getvalue()
            st.download_button(
                label="📥 Scarica Excel Globale Risultati (Tutti gli Esiti e Scartati inclusi)",
                data=excel_data,
                file_name=f"report_completo_risultati_chiamate_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# 3. INTERFACCIA OPERATORE
else:
    st.markdown(
        f'<div class="main-title">📞 Operatore: <span style="color:#0056b3;">{st.session_state.username}</span> (Sede: {st.session_state.postazione})</div>',
        unsafe_allow_html=True,
    )

    n_calls_today, n_apps_today = get_today_stats(st.session_state.username)
    target_calls = 100
    target_apps = 4

    pct_calls = min(int((n_calls_today / target_calls) * 100), 100)
    pct_apps = min(int((n_apps_today / target_apps) * 100), 100)

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown(
            f"""
            <div class="energy-container">
                <div class="energy-title">
                    <span>⚡ Chiamate Oggi: <b>{n_calls_today} / {target_calls}</b></span>
                    <span>{pct_calls}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill-calls" style="width: {pct_calls}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_b2:
        st.markdown(
            f"""
            <div class="energy-container">
                <div class="energy-title">
                    <span>🎯 Appuntamenti Oggi: <b>{n_apps_today} / {target_apps}</b></span>
                    <span>{pct_apps}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill-apps" style="width: {pct_apps}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    df_db = get_all_shared_dataframe()

    if df_db.empty:
        st.warning("⚠️ Nessun dato nel database. Contatta il Master.")
    else:
        records_list = []
        for _, db_row in df_db.iterrows():
            try:
                dati = json.loads(db_row["dati_json"])
            except:
                dati = {}
            dati["_id_db"] = db_row["id"]
            dati["Esito Chiamata"] = db_row["esito"]
            dati["Data Ora Esito"] = db_row["data_ora_esito"]
            dati["Postazione Chiamata"] = db_row["postazione"]
            dati["Operatore Chiamata"] = db_row["operatore"]
            dati["Sede Appuntamento"] = db_row["sede_appuntamento"]
            dati["_nota_db"] = db_row["note"]
            records_list.append(dati)

        df_view = pd.DataFrame(records_list)

        with st.expander("🔍 Filtri di Ricerca Avanzati", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            comuni_disponibili = ["Tutti"]
            if "indirizzo" in df_view.columns:
                estratti = set()
                for ind in df_view["indirizzo"].dropna():
                    for c_key in ["SPILIMBERGO", "SAN MARTINO", "CODROIPO", "PORDENONE", "ZOPPOLA", "CASARSA", "SAN VITO", "MANIAGO", "BRUGNERA", "UDINE", "FANNA"]:
                        if c_key in str(ind).upper():
                            estratti.add(c_key)
                comuni_disponibili += sorted(list(estratti))

            opzioni_esito = [
                "Tutti",
                "Da Chiamare",
                "Appuntamento Confermato",
                "Non Risponde / Occupato",
                "Rifiutato / Non Interessato",
                "Da Richiamare",
                "Scartato / Fuori Provincia",
            ]

            with col_f1:
                filtro_comune = st.selectbox("🏘️ Filtra per Comune Esatto", comuni_disponibili)
            with col_f2:
                filtro_esito = st.selectbox("📌 Stato Chiamata", opzioni_esito, index=1)
            with col_f3:
                search_text = st.text_input("🔎 Cerca Cliente, CF o Telefono", "")

        filtered_df = df_view.copy()
        if filtro_comune != "Tutti" and "indirizzo" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["indirizzo"].astype(str).str.upper().str.contains(filtro_comune)]

        if filtro_esito != "Tutti":
            if filtro_esito == "Da Chiamare":
                filtered_df = filtered_df[(filtered_df["Esito Chiamata"] == "") | (filtered_df["Esito Chiamata"].isna())]
            else:
                filtered_df = filtered_df[filtered_df["Esito Chiamata"] == filtro_esito]

        if search_text:
            mask = np.column_stack([filtered_df[col].astype(str).str.contains(search_text, case=False, na=False) for col in filtered_df.columns if col not in ["_id_db", "_nota_db"]])
            filtered_df = filtered_df[mask.any(axis=1)]

        if "current_index" not in st.session_state:
            st.session_state.current_index = 0

        if len(filtered_df) == 0:
            st.warning("⚠️ Nessun record trovato con questo filtro (prova a selezionare 'Tutti' in Stato Chiamata).")
        else:
            if st.session_state.current_index >= len(filtered_df):
                st.session_state.current_index = 0

            row = filtered_df.iloc[st.session_state.current_index]
            record_id = row["_id_db"]

            tel_attuale = pulisci_telefono(row.get("telefono", "N/D"))
            nome = row.get("nome", "Cliente Sconosciuto")
            cf = row.get("codice_fiscale", "N/D")
            indirizzo = row.get("indirizzo", "N/D")
            luce = row.get("luce", "N/D")
            gas = row.get("gas", "N/D")
            data_ver = row.get("data_verifica", "N/D")
            note_det = row.get("note_dettagliate", "N/D")
            esito_file = row.get("esito_file", "N/D")
            privacy = str(row.get("privacy", "N/D")).upper()

            if privacy in ["NO", "N", "FALSE", "0", "NEGATO"]:
                st.markdown(
                    """
                <div class="privacy-alert-popup">
                    ⚠️ ATTENZIONE: QUESTO CLIENTE HA DATO PRIVACY NO! VERIFICARE IL CONSENSO!
                </div>
                """,
                    unsafe_allow_html=True,
                )

            altre_chiamate = []
            if tel_attuale != "N/D" and len(tel_attuale) >= 5:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT postazione, operatore, esito, data_ora_esito FROM clienti WHERE telefono = ? AND esito != '' AND id != ?",
                    (tel_attuale, int(record_id)),
                )
                altre_chiamate = cursor.fetchall()
                conn.close()

            col_left, col_right = st.columns([2, 1])

            with col_left:
                if altre_chiamate:
                    avviso_txt = "🚨 **ATTENZIONE: QUESTO NUMERO È STATO GIÀ CONTATTATO!**\n"
                    for post, op, est, d_ora in altre_chiamate:
                        avviso_txt += f"- Operatore **{op}** (Sede **{post}**) ha registrato l'esito: *{est}* in data {d_ora}\n"
                    st.markdown(f'<div class="warning-box">{avviso_txt}</div>', unsafe_allow_html=True)

                st.subheader(f"👤 Scheda Cliente ({st.session_state.current_index + 1} di {len(filtered_df)})")

                privacy_html = (
                    f'<span class="privacy-no">{privacy}</span>'
                    if privacy in ["NO", "N", "FALSE", "0", "NEGATO"]
                    else f'<span class="privacy-yes">{privacy}</span>'
                )

                st.markdown(
                    f"""
                <div class="card-box">
                    <div class="name-highlight">{nome}</div>
                    <div class="phone-highlight">📞 {tel_attuale}</div>
                    <hr style="margin: 10px 0;">
                    <p><b>💳 Codice Fiscale / P.IVA:</b> {cf}</p>
                    <p><b>🏠 Indirizzo / Residenza:</b> {indirizzo}</p>
                    <p><b>⚡ Stato Luce:</b> <span class="status-badge-ok">{luce}</span> | <b>🔥 Stato Gas:</b> <span class="status-badge-warn">{gas}</span></p>
                    <p><b>📌 Esito Fornitura:</b> {esito_file}</p>
                    <p><b>📅 Data Verifica:</b> {data_ver}</p>
                    <p><b>📝 Note Dettagliate:</b> {note_det}</p>
                    <p><b>🔒 Privacy Marketing:</b> {privacy_html}</p>
                    <hr style="margin: 10px 0;">
                    <p style="font-size:12px; color:#666;">Stato Chiamata Call Center: <b>{row['Esito Chiamata'] or 'Non ancora chiamato'}</b> {f"(da {row['Operatore Chiamata']} - {row['Postazione Chiamata']})" if row['Operatore Chiamata'] else ''}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col_right:
                st.subheader("⚡ Esito Chiamata")
                sede_app = st.selectbox("🏛️ Sede Appuntamento", ["Pordenone", "Spilimbergo", "San Martino", "Codroipo"])
                nota_attuale = row.get("_nota_db", "")
                if pd.isna(nota_attuale) or str(nota_attuale).lower() == "nan":
                    nota_attuale = ""
                note_input = st.text_area("✍️ Note Operatore Call Center", value=nota_attuale, key=f"note_box_{record_id}")

                st.markdown("**Registra e passa al successivo:**")
                b1, b2 = st.columns(2)
                b3, b4 = st.columns(2)

                def registra_esito(esito_testo):
                    update_call_in_db(
                        record_id,
                        esito_testo,
                        st.session_state.postazione,
                        st.session_state.username,
                        sede_app if esito_testo == "Appuntamento Confermato" else "",
                        note_input,
                    )
                    if st.session_state.current_index < len(filtered_df) - 1:
                        st.session_state.current_index += 1
                    else:
                        st.session_state.current_index = 0
                    st.rerun()

                if b1.button("1️⃣ ✅ Confermato"):
                    registra_esito("Appuntamento Confermato")
                if b2.button("2️⃣ ⏳ Non Risponde"):
                    registra_esito("Non Risponde / Occupato")
                if b3.button("3️⃣ ❌ Rifiutato"):
                    registra_esito("Rifiutato / Non Interessato")
                if b4.button("4️⃣ 🔄 Da Richiamare"):
                    registra_esito("Da Richiamare")

                if st.button("5️⃣ 🚫 Scarta / Fuori Provincia", type="secondary"):
                    registra_esito("Scartato / Fuori Provincia")

                st.markdown("---")
                n1, n2 = st.columns(2)
                if n1.button("⬅️ Precedente"):
                    if st.session_state.current_index > 0:
                        st.session_state.current_index -= 1
                        st.rerun()
                if n2.button("➡️ Successivo"):
                    if st.session_state.current_index < len(filtered_df) - 1:
                        st.session_state.current_index += 1
                        st.rerun()
