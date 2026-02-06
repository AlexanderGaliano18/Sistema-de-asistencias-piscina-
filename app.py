import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sistema Piscina - V11", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v11_fixed.db"

# Listas Estándar
DIAS = ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"]
HORAS = ["07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", 
         "11:00-12:00", "12:00-13:00", "15:00-16:00", "16:00-17:00", 
         "17:00-18:00", "18:00-19:00"]
NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]

# CSS
st.markdown("""
<style>
    div.stButton > button {width: 100%; font-weight: bold;}
    .success-msg {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px;}
    .error-msg {padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASE DE DATOS
# ==========================================
def run_query(query, params=(), return_data=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON;")
        try:
            c.execute(query, params)
            if return_data:
                return c.fetchall()
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error BD: {e}")
            return False

def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    
    run_query('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 ciclo_id INTEGER, 
                 grupo TEXT, 
                 hora_inicio TEXT, 
                 nivel_salon TEXT, 
                 capacidad INTEGER,
                 FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    
    run_query('''CREATE TABLE IF NOT EXISTS alumnos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 nombre TEXT, apellido TEXT, telefono TEXT, 
                 direccion TEXT, nivel TEXT, apoderado TEXT, 
                 condicion TEXT)''')
    
    run_query('''CREATE TABLE IF NOT EXISTS matriculas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_id INTEGER, 
                 fecha_registro DATE,
                 FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
                 FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
    
    run_query('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, horario_id INTEGER, 
                 fecha TEXT, estado TEXT, 
                 UNIQUE(alumno_id, horario_id, fecha))''')

# --- FUNCIÓN ESPECIAL TRANSACCIONAL (SOLUCIONA EL ERROR DE ID 0) ---
def guardar_alumno_y_matricula(nombre, apellido, tel, dire, nivel, apo, cond, horario_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("PRAGMA foreign_keys = ON;")
            
            # 1. Insertar Alumno
            c.execute("""
                INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, condicion) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nombre, apellido, tel, dire, nivel, apo, cond))
            
            # 2. Capturar el ID (Dentro de la misma conexión, ahora sí funciona)
            alumno_id = c.lastrowid
            
            # 3. Insertar Matrícula
            c.execute("""
                INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) 
                VALUES (?, ?, ?)
            """, (alumno_id, horario_id, date.today()))
            
            conn.commit()
            return True, alumno_id
    except Exception as e:
        return False, str(e)

init_db()

# ==========================================
# 2. INTERFAZ
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=80)
    selected = option_menu(
        menu_title="Menú",
        options=["Configuración", "Matrícula", "Asistencia", "Base de Datos"],
        icons=["gear", "person-plus", "calendar-check", "database"],
        default_index=0,
    )

# ---------------------------------------------------------
# MÓDULO 1: CONFIGURACIÓN
# ---------------------------------------------------------
if selected == "Configuración":
    st.title("⚙️ Configuración")
    tab1, tab2 = st.tabs(["1. Crear Ciclo", "2. Abrir Salones"])
    
    with tab1:
        c_nom = st.text_input("Nombre del Ciclo (Ej: Verano 2026)")
        c_ini = st.date_input("Inicio de Clases")
        if st.button("Guardar Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (c_nom, c_ini))
            st.success("Ciclo creado.")
            
    with tab2:
        ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
        if ciclos:
            opts = {n: i for i, n in ciclos}
            sel_c = st.selectbox("Seleccionar Ciclo", list(opts.keys()))
            
            c1, c2, c3 = st.columns(3)
            dia = c1.selectbox("Días", DIAS)
            hora = c2.selectbox("Hora", HORAS)
            niv = c3.selectbox("Nivel (Salón)", NIVELES)
            cap = st.number_input("Cupos", 10)
            
            if st.button("Crear Salón"):
                dup = run_query("SELECT id FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", 
                                (opts[sel_c], dia, hora, niv), return_data=True)
                if not dup:
                    run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, nivel_salon, capacidad) VALUES (?,?,?,?,?)",
                              (opts[sel_c], dia, hora, niv, cap))
                    st.success(f"Salón de {niv} creado correctamente.")
                else:
                    st.error("Ya existe un salón con esas características.")
            
            st.write("---")
            data = run_query(f"SELECT id, grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts[sel_c]} ORDER BY hora_inicio", return_data=True)
            if data:
                df = pd.DataFrame(data, columns=["ID", "Días", "Hora", "Nivel", "Cupos"])
                st.dataframe(df, hide_index=True)
        else:
            st.warning("No hay ciclos creados.")

# ---------------------------------------------------------
# MÓDULO 2: MATRÍCULA (AQUÍ ESTÁ EL ARREGLO)
# ---------------------------------------------------------
elif selected == "Matrícula":
    st.title("📝 Matrícula")
    
    st.subheader("1. Selecciona el Horario")
    ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos:
        st.warning("Falta configurar ciclos.")
        st.stop()
        
    dict_c = {n: i for i, n in ciclos}
    sel_ciclo = st.selectbox("Ciclo:", list(dict_c.keys()))
    
    c1, c2 = st.columns(2)
    sel_dia = c1.radio("Días:", DIAS)
    sel_hora = c2.selectbox("Hora Preferida:", HORAS)
    
    salones = run_query("""
        SELECT id, nivel_salon, capacidad 
        FROM horarios 
        WHERE ciclo_id=? AND grupo=? AND hora_inicio=?
    """, (dict_c[sel_ciclo], sel_dia, sel_hora), return_data=True)
    
    id_horario_seleccionado = None
    
    if not salones:
        st.error(f"❌ No existe ningún salón configurado para {sel_dia} a las {sel_hora}.")
    else:
        opciones = {}
        for s in salones:
            hid, sniv, scap = s
            ocup = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
            label = f"Salón: {sniv} | Cupos: {scap - ocup}/{scap}"
            if ocup < scap:
                opciones[label] = hid
            else:
                opciones[f"⛔ LLENO - {label}"] = None
        
        sel_texto = st.selectbox("✅ Selecciona el Aula:", list(opciones.keys()))
        id_horario_seleccionado = opciones[sel_texto]
        
        if id_horario_seleccionado:
            st.success(f"🔗 Conectado al Salón ID: {id_horario_seleccionado}")
            
            st.write("---")
            st.subheader("2. Datos del Alumno")
            
            with st.form("form_mat"):
                col_a, col_b = st.columns(2)
                nom = col_a.text_input("Nombre")
                ape = col_b.text_input("Apellido")
                tel = col_a.text_input("Teléfono")
                apo = col_b.text_input("Apoderado")
                dire = col_a.text_input("Dirección")
                cond = st.text_area("Condición Médica")
                
                # Botón de Guardado
                btn_guardar = st.form_submit_button("💾 CONFIRMAR MATRÍCULA")
                
                if btn_guardar:
                    if nom and ape and id_horario_seleccionado:
                        # USAMOS LA NUEVA FUNCIÓN TRANSACCIONAL
                        exito, resultado = guardar_alumno_y_matricula(
                            nom, ape, tel, dire, "Registrado", apo, cond, id_horario_seleccionado
                        )
                        
                        if exito:
                            st.balloons()
                            st.markdown(f"""
                            <div class="success-msg">
                                ✅ <b>ÉXITO TOTAL:</b> Alumno {nom} {ape} matriculado.<br>
                                🔗 ID Alumno Generado: {resultado}<br>
                                Verifica en la pestaña 'Asistencia'.
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.error(f"Error al guardar: {resultado}")
                    else:
                        st.error("Faltan datos obligatorios.")

# ---------------------------------------------------------
# MÓDULO 3: ASISTENCIA
# ---------------------------------------------------------
elif selected == "Asistencia":
    st.title("📅 Asistencia")
    
    ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
    if not ciclos: st.stop()
    
    opts = {n: i for i, n in ciclos}
    sel_c = st.selectbox("Ciclo:", list(opts.keys()))
    
    c1, c2, c3 = st.columns(3)
    dia = c1.selectbox("Día", DIAS)
    hora = c2.selectbox("Hora", HORAS)
    
    nivs = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                     (opts[sel_c], dia, hora), return_data=True)
    
    if nivs:
        d_niv = {n: i for i, n in nivs}
        sel_n = c3.selectbox("Salón:", list(d_niv.keys()))
        id_h_final = d_niv[sel_n]
        
        st.divider()
        
        alumnos = run_query("""
            SELECT a.id, a.nombre, a.apellido, a.condicion
            FROM alumnos a
            JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.horario_id = ?
        """, (id_h_final,), return_data=True)
        
        if alumnos:
            fechas = []
            d = date.today()
            for i in range(12): fechas.append(str(d + timedelta(days=i))) # Fechas simuladas
            
            # Buscar asistencia guardada
            asist_data = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (id_h_final,), return_data=True)
            mapa_asist = {(row[0], row[1]): row[2] for row in asist_data}

            data = []
            for al in alumnos:
                aid = al[0]
                row = {"ID": aid, "Alumno": f"{al[1]} {al[2]}"}
                if al[3]: row["Alumno"] += " 🔴"
                
                for f in fechas:
                    estado_guardado = mapa_asist.get((aid, f))
                    row[f] = True if estado_guardado == "Presente" else False
                data.append(row)
                
            df = pd.DataFrame(data)
            col_conf = {"ID": None}
            for f in fechas: col_conf[f] = st.column_config.CheckboxColumn(f, default=False)
            
            edited = st.data_editor(df, column_config=col_conf, hide_index=True)
            
            if st.button("Guardar Asistencia"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for i, r in edited.iterrows():
                    aid = r["ID"]
                    for f in fechas:
                        est = "Presente" if r[f] else "Falta"
                        c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?,?,?,?)",
                                  (aid, id_h_final, f, est))
                conn.commit()
                conn.close()
                st.success("Guardado.")
        else:
            st.warning(f"El salón existe (ID {id_h_final}), pero no tiene alumnos.")
    else:
        st.error("No existe este salón.")

# ---------------------------------------------------------
# MÓDULO 4: BASE DE DATOS
# ---------------------------------------------------------
elif selected == "Base de Datos":
    st.title("📂 Datos Crudos")
    df = pd.read_sql_query("""
        SELECT m.id, a.nombre, a.apellido, h.hora_inicio, h.nivel_salon
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        JOIN horarios h ON m.horario_id = h.id
    """, sqlite3.connect(DB_NAME))
    st.dataframe(df)
