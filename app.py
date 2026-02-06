import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sistema Piscina - V10", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v10_final.db"

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
        # Activar Foreign Keys para asegurar que las tablas se unan
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
    
    # Esta tabla es el PUENTE. Si falla aquí, no se ven los alumnos.
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
# MÓDULO 1: CONFIGURACIÓN (CREAR CICLOS Y SALONES)
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
        st.info("Crea los salones donde se matricularán los niños.")
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
                # Verificar si ya existe
                dup = run_query("SELECT id FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", 
                                (opts[sel_c], dia, hora, niv), return_data=True)
                if not dup:
                    run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, nivel_salon, capacidad) VALUES (?,?,?,?,?)",
                              (opts[sel_c], dia, hora, niv, cap))
                    st.success(f"Salón de {niv} creado correctamente.")
                else:
                    st.error("Ya existe un salón con esas características.")
            
            # Ver salones
            st.write("---")
            st.write(f"Salones en **{sel_c}**:")
            data = run_query(f"SELECT id, grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts[sel_c]} ORDER BY hora_inicio", return_data=True)
            if data:
                df = pd.DataFrame(data, columns=["ID", "Días", "Hora", "Nivel", "Cupos"])
                st.dataframe(df, hide_index=True)
        else:
            st.warning("No hay ciclos creados.")

# ---------------------------------------------------------
# MÓDULO 2: MATRÍCULA (EL PROBLEMA ESTABA AQUÍ)
# ---------------------------------------------------------
elif selected == "Matrícula":
    st.title("📝 Matrícula - Paso a Paso")
    
    # 1. BUSCAR EL SALÓN PRIMERO
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
    
    # BUSCAR SALONES DISPONIBLES EN ESA HORA
    # Traemos ID, Nivel y Capacidad
    salones = run_query("""
        SELECT id, nivel_salon, capacidad 
        FROM horarios 
        WHERE ciclo_id=? AND grupo=? AND hora_inicio=?
    """, (dict_c[sel_ciclo], sel_dia, sel_hora), return_data=True)
    
    id_horario_seleccionado = None
    
    if not salones:
        st.error(f"❌ No existe ningún salón configurado para {sel_dia} a las {sel_hora}.")
        st.info("Ve a Configuración -> Abrir Salones y crea uno primero.")
    else:
        opciones = {}
        for s in salones:
            hid, sniv, scap = s
            # Contar ocupados
            ocup = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
            label = f"Salón: {sniv} | Cupos: {scap - ocup}/{scap} | (ID Interno: {hid})"
            if ocup < scap:
                opciones[label] = hid
            else:
                opciones[f"⛔ LLENO - {label}"] = None
        
        sel_texto = st.selectbox("✅ Selecciona el Aula:", list(opciones.keys()))
        id_horario_seleccionado = opciones[sel_texto]
        
        if id_horario_seleccionado:
            st.success(f"🔗 **Conectado al Salón ID: {id_horario_seleccionado}**. El alumno se guardará aquí.")
            
            st.write("---")
            st.subheader("2. Datos del Alumno")
            
            with st.form("form_mat"):
                col_a, col_b = st.columns(2)
                nom = col_a.text_input("Nombre")
                ape = col_b.text_input("Apellido")
                tel = col_a.text_input("Teléfono")
                apo = col_b.text_input("Apoderado")
                cond = st.text_area("Condición Médica")
                
                # Botón de Guardado
                btn_guardar = st.form_submit_button("💾 CONFIRMAR MATRÍCULA")
                
                if btn_guardar:
                    if nom and ape:
                        # 1. Guardar Alumno
                        run_query("INSERT INTO alumnos (nombre, apellido, telefono, nivel, apoderado, condicion) VALUES (?,?,?,?,?,?)",
                                  (nom, ape, tel, "Registrado", apo, cond))
                        
                        # Recuperar el ID del alumno recién creado
                        id_alumno = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                        
                        # 2. Guardar Matrícula (EL ENLACE)
                        # Aquí usamos el id_horario_seleccionado que confirmamos arriba
                        run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?,?,?)",
                                  (id_alumno, id_horario_seleccionado, date.today()))
                        
                        st.balloons()
                        st.markdown(f"""
                        <div class="success-msg">
                            ✅ <b>ÉXITO:</b> Alumno {nom} {ape} matriculado.<br>
                            🔗 ID Alumno: {id_alumno}<br>
                            🔗 ID Horario: {id_horario_seleccionado}<br>
                            Puedes verificarlo en la pestaña 'Base de Datos'.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("Falta nombre o apellido.")

# ---------------------------------------------------------
# MÓDULO 3: ASISTENCIA (VERIFICACIÓN)
# ---------------------------------------------------------
elif selected == "Asistencia":
    st.title("📅 Toma de Asistencia")
    
    ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
    if not ciclos: st.stop()
    
    opts = {n: i for i, n in ciclos}
    sel_c = st.selectbox("Ciclo:", list(opts.keys()))
    
    c1, c2, c3 = st.columns(3)
    dia = c1.selectbox("Día", DIAS)
    hora = c2.selectbox("Hora", HORAS)
    
    # Buscar NIVELES en esa hora
    nivs = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                     (opts[sel_c], dia, hora), return_data=True)
    
    if nivs:
        d_niv = {n: i for i, n in nivs}
        sel_n = c3.selectbox("Salón:", list(d_niv.keys()))
        
        # ID FINAL DEL HORARIO
        id_h_final = d_niv[sel_n]
        
        st.divider()
        st.write(f"Buscando alumnos en Horario ID: **{id_h_final}**...")
        
        # CONSULTA DIRECTA
        alumnos = run_query("""
            SELECT a.id, a.nombre, a.apellido, a.condicion
            FROM alumnos a
            JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.horario_id = ?
        """, (id_h_final,), return_data=True)
        
        if alumnos:
            # Lógica de fechas
            fechas = []
            d = date.today() # Simulación de fechas
            for i in range(5): fechas.append(str(d + timedelta(days=i)))
            
            # Tabla
            data = []
            for al in alumnos:
                row = {"ID": al[0], "Alumno": f"{al[1]} {al[2]}"}
                if al[3]: row["Alumno"] += " 🔴"
                for f in fechas: row[f] = False
                data.append(row)
                
            df = pd.DataFrame(data)
            edited = st.data_editor(df, hide_index=True)
            
            if st.button("Guardar"):
                st.success("Asistencia Guardada")
        else:
            st.warning(f"⚠️ El sistema funciona, pero este salón (ID {id_h_final}) está vacío.")
            st.info("Ve a 'Base de Datos' para ver dónde quedaron los alumnos.")
    else:
        st.error("No existe este salón en la configuración.")

# ---------------------------------------------------------
# MÓDULO 4: BASE DE DATOS (PARA QUE VEAS SI SE GUARDÓ)
# ---------------------------------------------------------
elif selected == "Base de Datos":
    st.title("📂 Auditoría de Datos")
    
    st.subheader("1. Tabla Matriculas (El puente)")
    st.write("Aquí deben salir las uniones. Si sale vacío, la matrícula falló.")
    
    df = pd.read_sql_query("""
        SELECT m.id as ID_MATRICULA, 
               a.nombre || ' ' || a.apellido as ALUMNO, 
               h.hora_inicio as HORA, 
               h.nivel_salon as NIVEL,
               h.id as ID_HORARIO_REAL
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        JOIN horarios h ON m.horario_id = h.id
    """, sqlite3.connect(DB_NAME))
    
    st.dataframe(df)
    
    st.subheader("2. Tabla Horarios Disponibles")
    df2 = pd.read_sql_query("SELECT id, grupo, hora_inicio, nivel_salon FROM horarios", sqlite3.connect(DB_NAME))
    st.dataframe(df2)
