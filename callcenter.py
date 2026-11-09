from datetime import datetime
import json
import os
import sqlite3
import subprocess
import sys

# --- AUTO-INSTALLAZIONE AUTOMATICA LIBRERIE AL PRIMO AVVIO ---
REQUIRED_PACKAGES = ["streamlit", "pandas", "openpyxl", "numpy"]


def install_missing_packages():
  for package in REQUIRED_PACKAGES:
    try:
      __import__(package)
    except ImportError:
      print(
          f"Libreria mancante rilevata: '{package}'. Installazione in corso..."
      )
      subprocess.check_call(
          [sys.executable, "-m", "pip", "install", package]
      )


install_missing_packages()

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Call Center - Multi-Agenzia",
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

    .stButton>button { width: 100%; height: 52px; font-size: 16px; font-weight: bold; border-radius: 8px; }
    
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
  conn.commit()
  conn.close()


init_db()


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
      "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE"
      " ?",
      (operatore, f"{today_str}%"),
  )
  chiamate_oggi = cursor.fetchone()[0] or 0
  cursor.execute(
      "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE"
      " ? AND esito = 'Appuntamento Confermato'",
      (operatore, f"{today_str}%"),
  )
  appuntamenti_oggi = cursor.fetchone()[0] or 0
  conn.close()
  return chiamate_oggi, appuntamenti_oggi


def get_month_stats(operatore):
  conn = sqlite3.connect(DB_NAME)
  month_str = datetime.now().strftime("%Y-%m")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE"
      " ?",
      (operatore, f"{month_str}%"),
  )
  chiamate_mese = cursor.fetchone()[0] or 0
  cursor.execute(
      "SELECT COUNT(*) FROM clienti WHERE operatore = ? AND data_ora_esito LIKE"
      " ? AND esito = 'Appuntamento Confermato'",
      (operatore, f"{month_str}%"),
  )
  appuntamenti_mese = cursor.fetchone()[0] or 0
  conn.close()
  return chiamate_mese, appuntamenti_mese


def update_call_in_db(
    record_id, esito, postazione, operatore, sede_appuntamento, note
):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  cursor.execute(
      """
        UPDATE clienti 
        SET esito = ?, data_ora_esito = ?, postazione = ?, operatore = ?, sede_appuntamento = ?, note = ?
        WHERE id = ?
    """,
      (
          esito,
          timestamp,
          postazione,
          operatore,
          sede_appuntamento,
          note,
          int(record_id),
      ),
  )
  conn.commit()
  conn.close()


def pulisci_telefono(tel):
  if pd.isna(tel) or not tel:
    return "N/D"
  t_str = str(tel).strip()
  if t_str.endswith(".0"):
    t_str = t_str[:-2]
  return t_str


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

# CONTROLLO UTENTI IN DATABASE
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()
cursor.execute("SELECT username FROM utenti")
utenti_esistenti = [row[0] for row in cursor.fetchall()]
conn.close()

# SE NON CI SONO UTENTI O SI FORZA LA NUOVA INSTALLAZIONE
if len(utenti_esistenti) == 0 or st.session_state.force_setup:
  st.markdown(
      "<h1 style='text-align: center; color: #0284c7;'>⚙️ Inizializzazione Nuova"
      " Agenzia</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center;'>Configura l'Account Master Amministratore"
      " per iniziare ad usare la tua piattaforma.</p>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.markdown('<div class="setup-box">', unsafe_allow_html=True)
    st.subheader("🔑 Crea il tuo Account Master")

    setup_user = st.text_input(
        "Username Amministratore / Titolare",
        value="",
        placeholder="es. Mario Rossi",
    )
    setup_pass = st.text_input(
        "Password Master Segreta", type="password", placeholder="Scegli password"
    )
    setup_postazione = st.text_input(
        "Nome Sede Principale", value="Sede Principale"
    )

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
              (
                  setup_user.strip(),
                  setup_pass.strip(),
                  "ADMIN",
                  setup_postazione.strip(),
              ),
          )
          conn.commit()
          conn.close()

          st.session_state.force_setup = False
          st.success(
              "✅ Account Master creato con successo! Ora puoi accedere."
          )
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("❌ Questo Username è già presente. Scegline un altro.")
        except Exception as e:
          st.error(f"Errore: {e}")
      else:
        st.warning("⚠️ Compila sia Username che Password.")

    if len(utenti_esistenti) > 0:
      st.markdown("---")
      if st.button("🔙 Torna al Login"):
        st.session_state.force_setup = False
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
  st.stop()

# LOGIN NORMALE
if not st.session_state.logged_in:
  st.markdown(
      "<h2 style='text-align: center; color: #003366;'>📞 Accesso Call Center"
      " Agenzia</h2>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)

    selected_user = st.selectbox("👤 Seleziona Utente", utenti_esistenti)
    login_pass = st.text_input("🔑 Inserisci Password", type="password")

    if st.button("🚀 Accedi"):
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT ruolo, postazione FROM utenti WHERE username = ? AND"
          " password = ?",
          (selected_user, login_pass),
      )
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

    with st.expander("🆕 Prima volta qui? Configura una Nuova Agenzia"):
      if st.button("⚙️ Avvia Configurazione Iniziale"):
        st.session_state.force_setup = True
        st.rerun()

  st.stop()

# --- BARRA LATERALE ---
st.sidebar.title(f"👤 {st.session_state.username}")
st.sidebar.markdown(f"**Ruolo:** {st.session_state.role}")
st.sidebar.markdown(f"**Postazione:** {st.session_state.postazione}")

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
    ind = str(d.get("Indirizzo residenza", ""))
    comune_trovato = "ALTRO"
    for c_key in [
        "SPILIMBERGO",
        "SAN MARTINO",
        "CODROIPO",
        "PORDENONE",
        "ZOPPOLA",
        "CASARSA",
        "SAN VITO",
        "MANIAGO",
    ]:
      if c_key in ind.upper():
        comune_trovato = c_key
        break
    comuni_list.append({"comune": comune_trovato, "esito": r["esito"]})

  df_c_stat = pd.DataFrame(comuni_list)
  df_da_chiamare = df_c_stat[
      (df_c_stat["esito"] == "") | (df_c_stat["esito"].isna())
  ]
  if not df_da_chiamare.empty:
    for com, num in df_da_chiamare["comune"].value_counts().items():
      st.sidebar.markdown(
          f"📍 **{com}**: <span style='color: #d9534f; font-weight: bold;'>{num}"
          " da chiamare</span>",
          unsafe_allow_html=True,
      )

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Esci / Logout"):
  st.session_state.logged_in = False
  st.rerun()

# 2. MASTER ACCOUNT
if st.session_state.role == "ADMIN":
  st.markdown(
      '<div class="main-title">🛠️ Master Account - Amministrazione</div>',
      unsafe_allow_html=True,
  )

  with st.expander("👥 Gestione Collaboratori & Password", expanded=False):
    st.markdown(
        "Crea liberamente i profili degli operatori e assegna username e"
        " password a tua scelta."
    )
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
              (
                  new_username.strip(),
                  new_password.strip(),
                  new_ruolo,
                  new_postazione.strip(),
              ),
          )
          conn.commit()
          conn.close()
          st.success(
              f"✅ Operatore **{new_username}** registrato con successo!"
          )
          st.rerun()
        except sqlite3.IntegrityError:
          st.error("❌ Questo Username è già esistente.")
      else:
        st.warning("⚠️ Compila tutti i campi.")

  with st.expander(
      "📥 Caricamento e Sincronizzazione File Excel", expanded=False
  ):
    uploaded_file = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])
    if uploaded_file and st.button("🚀 Importa Liste nel Database Centrale"):
      try:
        excel_file = pd.ExcelFile(uploaded_file)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clienti")
        count_tot = 0

        for sheet in excel_file.sheet_names:
          df_sheet = pd.read_excel(uploaded_file, header=3, sheet_name=sheet)
          df_sheet.columns = [str(c).strip() for c in df_sheet.columns]

          for _, row in df_sheet.iterrows():
            row_dict = row.to_dict()
            row_dict = {
                str(k): ("" if pd.isna(v) else str(v))
                for k, v in row_dict.items()
            }

            tel = pulisci_telefono(row_dict.get("Telefono", ""))
            nome = str(row_dict.get("Cliente", "")).strip()
            if not nome or nome.lower() in ["nan", ""]:
              nome = str(row_dict.get("Referente Titolare", "")).strip()
            if not nome or nome.lower() in ["nan", ""]:
              nome = "Cliente Sconosciuto"

            cf = str(row_dict.get("Codice fiscale", "")).strip()
            if not cf or cf.lower() in ["nan", ""]:
              cf = str(row_dict.get("Partita IVA", "")).strip()
            if not cf or cf.lower() in ["nan", ""]:
              cf = "N/D"

            dati_str = json.dumps(row_dict, ensure_ascii=False)
            cursor.execute(
                """
                        INSERT INTO clienti (foglio, telefono, nome, codice_fiscale, dati_json, esito)
                        VALUES (?, ?, ?, ?, ?, '')
                    """,
                (sheet, tel, nome, cf, dati_str),
            )
            count_tot += 1

        conn.commit()
        conn.close()
        st.success(f"✅ Importazione completata! Caricati {count_tot} record.")
      except Exception as e:
        st.error(f"Errore durante l'importazione: {e}")

  st.markdown("---")
  st.subheader(
      "📈 Controllo Statistiche e Barre Attività per Singolo Operatore"
  )

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("SELECT username FROM utenti WHERE ruolo = 'OPERATORE'")
  operatori_disponibili = [r[0] for r in cursor.fetchall()]
  conn.close()

  if not operatori_disponibili:
    st.info(
        "Nessun operatore registrato. Crea prima un account operatore nel pannello"
        " sopra."
    )
  else:
    selected_op_stat = st.selectbox(
        "👤 Seleziona Operatore da Monitorare", operatori_disponibili
    )

    # Calcoli giornalieri e mensili per l'operatore selezionato
    c_oggi, a_oggi = get_today_stats(selected_op_stat)
    c_mese, a_mese = get_month_stats(selected_op_stat)

    target_calls_day = 100
    target_apps_day = 4
    target_calls_month = 2000
    target_apps_month = 80

    pct_c_oggi = min(int((c_oggi / target_calls_day) * 100), 100)
    pct_a_oggi = min(int((a_oggi / target_apps_day) * 100), 100)
    pct_c_mese = min(int((c_mese / target_calls_month) * 100), 100)
    pct_a_mese = min(int((a_mese / target_apps_month) * 100), 100)

    st.markdown(
        f"#### 📅 Statistiche Giornaliere di: `{selected_op_stat}`"
    )
    col_m1, col_m2 = st.columns(2)
    with col_m1:
      st.markdown(
          f"""
                <div class="energy-container">
                    <div class="energy-title">
                        <span>⚡ Chiamate Oggi: <b>{c_oggi} / {target_calls_day}</b></span>
                        <span>{pct_c_oggi}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill-calls" style="width: {pct_c_oggi}%;"></div>
                    </div>
                </div>
                """,
          unsafe_allow_html=True,
      )
    with col_m2:
      st.markdown(
          f"""
                <div class="energy-container">
                    <div class="energy-title">
                        <span>🎯 Appuntamenti Oggi: <b>{a_oggi} / {target_apps_day}</b></span>
                        <span>{pct_a_oggi}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill-apps" style="width: {pct_a_oggi}%;"></div>
                    </div>
                </div>
                """,
          unsafe_allow_html=True,
      )

    st.markdown(f"#### 📆 Statistiche Mensili di: `{selected_op_stat}`")
    col_m3, col_m4 = st.columns(2)
    with col_m3:
      st.markdown(
          f"""
                <div class="energy-container">
                    <div class="energy-title">
                        <span>⚡ Chiamate Mese: <b>{c_mese} / {target_calls_month}</b></span>
                        <span>{pct_c_mese}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill-calls" style="width: {pct_c_mese}%;"></div>
                    </div>
                </div>
                """,
          unsafe_allow_html=True,
      )
    with col_m4:
      st.markdown(
          f"""
                <div class="energy-container">
                    <div class="energy-title">
                        <span>🎯 Appuntamenti Mese: <b>{a_mese} / {target_apps_month}</b></span>
                        <span>{pct_a_mese}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill-apps" style="width: {pct_a_mese}%;"></div>
                    </div>
                </div>
                """,
          unsafe_allow_html=True,
      )

  st.markdown("---")
  st.subheader("📊 Report Attività Globale in Tempo Reale")
  conn = sqlite3.connect(DB_NAME)
  df_report = pd.read_sql_query(
      "SELECT operatore, postazione, foglio, esito, COUNT(*) as conteggio FROM"
      " clienti WHERE esito != '' GROUP BY operatore, postazione, foglio, esito",
      conn,
  )
  conn.close()
  if not df_report.empty:
    st.dataframe(df_report, use_container_width=True)
  else:
    st.info("Nessuna chiamata registrata finora.")

# 3. INTERFACCIA OPERATORE
else:
  st.markdown(
      f'<div class="main-title">📞 Operatore: <span'
      f' style="color:#0056b3;">{st.session_state.username}</span> (Sede:'
      f" {st.session_state.postazione})</div>",
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

  n_calls_month, n_apps_month = get_month_stats(st.session_state.username)
  st.markdown(
      f"""
        <div style="background: #eef2f6; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 13px; color: #1e293b;">
            📅 <b>Il tuo riepilogo del Mese in corso:</b> Chiamate effettuate: <b>{n_calls_month}</b> | Appuntamenti confermati: <b>{n_apps_month}</b>
        </div>
    """,
      unsafe_allow_html=True,
  )

  df_db = get_all_shared_dataframe()

  if df_db.empty:
    st.warning(
        "⚠️ Nessun dato nel database. Accedi come Master e carica il file"
        " Excel."
    )
  else:
    records_list = []
    for _, db_row in df_db.iterrows():
      try:
        dati = json.loads(db_row["dati_json"])
      except:
        dati = {}
      dati["_id_db"] = db_row["id"]
      dati["_origine_foglio"] = db_row["foglio"]
      dati["Esito Chiamata"] = db_row["esito"]
      dati["Data Ora Esito"] = db_row["data_ora_esito"]
      dati["Postazione Chiamata"] = db_row["postazione"]
      dati["Operatore Chiamata"] = db_row["operatore"]
      dati["Sede Appuntamento"] = db_row["sede_appuntamento"]
      dati["_nota_db"] = db_row["note"]
      if "Telefono" in dati:
        dati["Telefono"] = pulisci_telefono(dati["Telefono"])
      records_list.append(dati)

    df_view = pd.DataFrame(records_list)

    with st.expander("🔍 Filtri di Ricerca Avanzati", expanded=True):
      col_f1, col_f2, col_f3 = st.columns(3)
      comuni_disponibili = ["Tutti"]
      if "Indirizzo residenza" in df_view.columns:
        estratti = set()
        for ind in df_view["Indirizzo residenza"].dropna():
          for c_key in [
              "SPILIMBERGO",
              "SAN MARTINO",
              "CODROIPO",
              "PORDENONE",
              "ZOPPOLA",
              "CASARSA",
              "SAN VITO",
              "MANIAGO",
          ]:
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
      ]

      with col_f1:
        filtro_comune = st.selectbox(
            "🏘️ Filtra per Comune Esatto", comuni_disponibili
        )
      with col_f2:
        filtro_esito = st.selectbox("📌 Stato Chiamata", opzioni_esito)
      with col_f3:
        search_text = st.text_input("🔎 Cerca Cliente, CF o Telefono", "")

    filtered_df = df_view.copy()
    if filtro_comune != "Tutti":
      filtered_df = filtered_df[
          filtered_df["Indirizzo residenza"]
          .astype(str)
          .str.upper()
          .str.contains(filtro_comune)
      ]

    if filtro_esito != "Tutti":
      if filtro_esito == "Da Chiamare":
        filtered_df = filtered_df[
            (filtered_df["Esito Chiamata"] == "")
            | (filtered_df["Esito Chiamata"].isna())
        ]
      else:
        filtered_df = filtered_df[
            filtered_df["Esito Chiamata"] == filtro_esito
        ]

    if search_text:
      mask = np.column_stack([
          filtered_df[col]
          .astype(str)
          .str.contains(search_text, case=False, na=False)
          for col in filtered_df.columns
          if col not in ["_id_db", "_origine_foglio", "_nota_db"]
      ])
      filtered_df = filtered_df[mask.any(axis=1)]

    if "current_index" not in st.session_state:
      st.session_state.current_index = 0

    if len(filtered_df) == 0:
      st.warning("⚠️ Nessun record trovato con i filtri selezionati.")
    else:
      if st.session_state.current_index >= len(filtered_df):
        st.session_state.current_index = 0

      row = filtered_df.iloc[st.session_state.current_index]
      record_id = row["_id_db"]

      def val_safe(key, default="N/D"):
        v = row.get(key, default)
        if pd.isna(v) or str(v).strip().lower() in ["nan", "n/d", ""]:
          return default
        return str(v).strip()

      tel_attuale = pulisci_telefono(row.get("Telefono", "N/D"))
      nome = val_safe("Cliente", "")
      if nome == "N/D" or not nome:
        nome = val_safe("Referente Titolare", "N/D")
      cf = val_safe("Codice fiscale", "")
      if cf == "N/D":
        cf = val_safe("Partita IVA", "N/D")
      indirizzo = val_safe("Indirizzo residenza", "N/D")
      luce = val_safe("STATO LUCE", "N/D")
      gas = val_safe("STATO GAS", "N/D")
      cessazione = val_safe("DATA CESSAZIONE / SW OUT", "N/D")
      privacy = val_safe("PRIVACY", "N/D").upper()

      if privacy in ["NO", "N", "FALSE", "0"]:
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
            "SELECT postazione, operatore, esito, data_ora_esito FROM clienti"
            " WHERE telefono = ? AND esito != '' AND id != ?",
            (tel_attuale, int(record_id)),
        )
        altre_chiamate = cursor.fetchall()
        conn.close()

      col_left, col_right = st.columns([2, 1])

      with col_left:
        if altre_chiamate:
          avviso_txt = (
              "🚨 **ATTENZIONE: QUESTO NUMERO È STATO GIÀ CONTATTATO!**\n"
          )
          for post, op, est, d_ora in altre_chiamate:
            avviso_txt += f"- Operatore **{op}** (Sede **{post}**) ha registrato l'esito: *{est}* in data {d_ora}\n"
          st.markdown(
              f'<div class="warning-box">{avviso_txt}</div>',
              unsafe_allow_html=True,
          )

        st.subheader(
            f"👤 Scheda Cliente ({st.session_state.current_index + 1} di"
            f" {len(filtered_df)}) | Origine: {row.get('_origine_foglio','')}"
        )

        privacy_html = (
            f'<span class="privacy-no">{privacy}</span>'
            if privacy in ["NO", "N", "FALSE", "0"]
            else f'<span class="privacy-yes">{privacy}</span>'
        )

        st.markdown(
            f"""
                <div class="card-box">
                    <div class="name-highlight">{nome}</div>
                    <div class="phone-highlight">📞 {tel_attuale}</div>
                    <hr style="margin: 10px 0;">
                    <p><b>💳 Codice Fiscale / P.IVA:</b> {cf}</p>
                    <p><b>🏠 Indirizzo:</b> {indirizzo}</p>
                    <p><b>⚡ Stato Luce:</b> <span class="status-badge-ok">{luce}</span> | <b>🔥 Stato Gas:</b> <span class="status-badge-warn">{gas}</span></p>
                    <p><b>📅 Data Cessazione / SW Out:</b> {cessazione}</p>
                    <p><b>🔒 Privacy:</b> {privacy_html}</p>
                    <hr style="margin: 10px 0;">
                    <p style="font-size:12px; color:#666;">Stato Attuale: <b>{row['Esito Chiamata'] or 'Non ancora chiamato'}</b> {f"(da {row['Operatore Chiamata']} - {row['Postazione Chiamata']})" if row['Operatore Chiamata'] else ''}</p>
                </div>
                """,
            unsafe_allow_html=True,
        )

      with col_right:
        st.subheader("⚡ Esito Chiamata")
        sede_app = st.selectbox(
            "🏛️ Sede Appuntamento",
            ["Pordenone", "Spilimbergo", "San Martino", "Codroipo"],
        )

        nota_attuale = row.get("_nota_db", "")
        if pd.isna(nota_attuale) or str(nota_attuale).lower() == "nan":
          nota_attuale = ""
        note_input = st.text_area(
            "✍️ Note Operatore",
            value=nota_attuale,
            key=f"note_box_{record_id}",
        )

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
