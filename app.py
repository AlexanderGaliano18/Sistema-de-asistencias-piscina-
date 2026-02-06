import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Piscina Arenas - V9", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v9_blindada.db"

# --- CSS PARA MEJORAR LA VISUALIZACIÓN ---
st.markdown("""
<style>
    .metric-box {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 10px;
        margin-bottom: 10px;
    }
    div.stButton > button {width: 100%;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASE DE DATOS (CORE)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla Ciclos
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    # Tabla Horarios (Salones)
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 ciclo_id INTEGER, 
                 grupo TEXT, 
                 hora_inicio TEXT, 
                 nivel_salon TEXT, 
                 capacidad INTEGER)''')
    # Tabla Alumnos
    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 nombre TEXT, apellido TEXT, telefono TEXT, 
                 direccion TEXT, nivel TEXT, apoderado TEXT, 
                 condicion TEXT)''')
    # Tabla Matrículas (LINK)
    c.execute('''CREATE TABLE IF NOT EXISTS matriculas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_id INTEGER, 
                 fecha_registro DATE)''')
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, horario_id INTEGER, 
                 fecha TEXT, estado TEXT, 
                 UNIQUE(alumno_id, horario_id, fecha))''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute(query, params)
        if return_data:
            data = c.fetchall()
            conn.close()
            return data
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error BD: {e}")
        conn.close()
        return False

def get_stats():
    """Obtiene contadores para la barra lateral"""
    try:
        n_alumnos = run_query("SELECT COUNT(*) FROM alumnos", return_data=True)[0][0]
        n_matriculas = run_query("SELECT COUNT(*) FROM matriculas", return_data=True)[0][0]
        n_horarios = run_query("SELECT COUNT(*) FROM horarios", return_data=True)[0][0]
        return n_alumnos, n_matriculas, n_horarios
    except:
        return 0, 0, 0

init_db()

# ==========================================
# 2. BARRA LATERAL CON DIAGNÓSTICO
# ==========================================
with st.sidebar:
    st.title("🏊 Piscina Arenas")
    
    selected = option_menu(
        menu_title=None,
        options=["1. Configuración", "2. Matrícula", "3. Asistencia", "4. Base de Datos"],
        icons=["gear", "person-plus", "calendar-check", "database"],
        default_index=0,
    )
    
    st.divider()
    st.markdown("### 📊 Estado del Sistema")
    al, mat, hor = get_stats()
    st.markdown(f"""
    <div class="metric-box">
        <b>Alumnos:</b> {al}<br>
        <b>Matrículas:</b> {mat}<br>
        <b>Salones:</b> {hor}
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔄 Actualizar Contadores"):
        st.rerun()

# ==========================================
# MÓDULO 1: CONFIGURACIÓN
# ==========================================
if selected == "1. Configuración":
    st.header("⚙️ Configuración")
    
    tab1, tab2 = st.tabs(["Crear Ciclo", "Abrir Salones"])
    
    with tab1:
        c_nombre = st.text_input("Nombre Ciclo (Ej: Verano 2026)")
        c_inicio = st.date_input("Fecha Inicio")
        if st.button("Crear Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (c_nombre, c_inicio))
            st.success("Ciclo creado.")
            st.rerun()

    with tab2:
        ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
        if ciclos:
            opts_c = {n: i for i, n in ciclos}
            sel_c = st.selectbox("Ciclo:", list(opts_c.keys()))
            
            c1, c2, c3 = st.columns(3)
            dia = c1.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            hora = c2.selectbox("Hora", ["07:00-08:00", "08:00-09:00", "09:00-10:00", "15:00-16:00", "16:00-17:00"])
            niv = c3.selectbox("Nivel (Salón)", ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"])
            cap = st.number_input("Cupos", 10)
            
            if st.button(f"Abrir Salón {niv}"):
                # Evitar duplicados
                existe = run_query("SELECT id FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", 
                                   (opts_c[sel_c], dia, hora, niv), return_data=True)
                if not existe:
                    run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, nivel_salon, capacidad) VALUES (?,?,?,?,?)",
                              (opts_c[sel_c], dia, hora, niv, cap))
                    st.success("Salón Creado.")
                    st.rerun()
                else:
                    st.error("Ese salón ya existe.")
            
            # Mostrar tabla
            st.write("Salones existentes:")
            df = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts_c[sel_c]}", sqlite3.connect(DB_NAME))
            st.dataframe(df)
        else:
            st.warning("Crea un ciclo primero.")

# ==========================================
# MÓDULO 2: MATRÍCULA (FORMULARIO SEGURO)
# ==========================================
elif selected == "2. Matrícula":
    st.header("📝 Matrícula")
    
    # PASO 1: SELECCIONAR EL SALÓN (Fuera del formulario para que sea dinámico)
    st.info("Paso 1: Encuentra el salón disponible")
    
    ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
    horario_seleccionado_id = None
    
    if ciclos:
        dict_c = {n: i for i, n in ciclos}
        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_ciclo = col_f1.selectbox("Ciclo", list(dict_c.keys()))
        filtro_dia = col_f2.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
        filtro_hora = col_f3.selectbox("Hora Preferida", ["07:00-08:00", "08:00-09:00", "09:00-10:00", "15:00-16:00", "16:00-17:00"])
        
        # Buscar salones que coincidan
        salones = run_query("""
            SELECT id, nivel_salon, capacidad 
            FROM horarios 
            WHERE ciclo_id=? AND grupo=? AND hora_inicio=?
        """, (dict_c[filtro_ciclo], filtro_dia, filtro_hora), return_data=True)
        
        if salones:
            opciones = {}
            for s in salones:
                hid, niv, cap = s
                # Contar ocupados
                ocup = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                label = f"{niv} | Disponibles: {cap - ocup}/{cap}"
                if ocup < cap:
                    opciones[label] = hid
                else:
                    opciones[f"⛔ LLENO - {label}"] = None
            
            sel_salon_txt = st.selectbox("✅ Selecciona el Salón Específico:", list(opciones.keys()))
            horario_seleccionado_id = opciones[sel_salon_txt]
        else:
            st.warning("No hay salones creados con estos filtros.")

    st.divider()

    # PASO 2: DATOS DEL ALUMNO (Dentro de un FORMULARIO para asegurar guardado)
    st.info("Paso 2: Datos del Estudiante")
    
    with st.form("form_matricula"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombres")
        apellido = c2.text_input("Apellidos")
        telefono = c1.text_input("Teléfono")
        nivel_real = c2.selectbox("Nivel del Niño", ["Básico 0", "Básico 1", "Intermedio", "Avanzado"])
        condicion = st.text_area("Condición Médica (Opcional)")
        
        # Botón de envío
        submitted = st.form_submit_button("💾 CONFIRMAR MATRÍCULA")
        
        if submitted:
            if not horario_seleccionado_id:
                st.error("❌ Error: No has seleccionado un salón válido arriba (o está lleno).")
            elif not nombre or not apellido:
                st.error("❌ Error: Faltan el nombre o apellido.")
            else:
                # 1. Guardar Alumno
                run_query("INSERT INTO alumnos (nombre, apellido, telefono, nivel, condicion) VALUES (?,?,?,?,?)",
                          (nombre, apellido, telefono, nivel_real, condicion))
                id_alumno = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                
                # 2. Guardar Matrícula
                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?,?,?)",
                          (id_alumno, horario_seleccionado_id, date.today()))
                
                st.success("✅ ¡Matrícula Guardada Exitosamente!")
                # Forzar recarga para actualizar contadores
                st.rerun()

# ==========================================
# MÓDULO 3: ASISTENCIA
# ==========================================
elif selected == "3. Asistencia":
    st.header("📅 Asistencia")
    
    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
    if not ciclos:
        st.stop()
        
    dict_c = {n: (i, f) for i, n, f in ciclos}
    sel_c = st.selectbox("Ciclo:", list(dict_c.keys()))
    id_ciclo, fecha_base = dict_c[sel_c]
    
    col1, col2, col3 = st.columns(3)
    sel_d = col1.selectbox("Días:", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
    sel_h = col2.selectbox("Hora:", ["07:00-08:00", "08:00-09:00", "09:00-10:00", "15:00-16:00", "16:00-17:00"])
    
    # Buscar Niveles disponibles en esa hora
    nivs = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                     (id_ciclo, sel_d, sel_h), return_data=True)
    
    if nivs:
        dict_n = {n: i for i, n in nivs}
        sel_n = col3.selectbox("Salón:", list(dict_n.keys()))
        id_horario = dict_n[sel_n]
        
        # --- TABLA DE ALUMNOS ---
        alumnos = run_query("""
            SELECT a.id, a.nombre, a.apellido, a.condicion 
            FROM alumnos a
            JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.horario_id = ?
        """, (id_horario,), return_data=True)
        
        st.write(f"Mostrando lista para: **{sel_n}** (ID Horario: {id_horario})")
        
        if alumnos:
            # Lógica de fechas
            fechas = []
            d = datetime.strptime(str(fecha_base), "%Y-%m-%d").date()
            dias_ok = [0, 2, 4] if "Lunes" in sel_d else [1, 3, 5]
            while d.weekday() not in dias_ok: d += timedelta(days=1)
            for _ in range(12):
                fechas.append(d.strftime("%Y-%m-%d"))
                d += timedelta(days=1)
                while d.weekday() not in dias_ok: d += timedelta(days=1)

            # Recuperar asistencia
            asist = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (id_horario,), return_data=True)
            mapa = {(a, f): e for a, f, e in asist}
            
            data = []
            for alum in alumnos:
                aid, nom, ape, cond = alum
                row = {"ID": aid, "Alumno": f"{nom} {ape} {('🔴' if cond else '')}"}
                for f in fechas:
                    row[f] = True if mapa.get((aid, f)) == "Presente" else False
                data.append(row)
                
            df = pd.DataFrame(data)
            col_conf = {"ID": None}
            for f in fechas: col_conf[f] = st.column_config.CheckboxColumn(f[5:], default=False)
            
            edited = st.data_editor(df, column_config=col_conf, hide_index=True)
            
            if st.button("Guardar Asistencia"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for i, r in edited.iterrows():
                    for f in fechas:
                        est = "Presente" if r[f] else "Falta"
                        c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?,?,?,?)",
                                  (r["ID"], id_horario, f, est))
                conn.commit()
                conn.close()
                st.success("Guardado.")
        else:
            st.error("⚠️ No hay alumnos en este salón.")
            st.info("Prueba: Ve a la pestaña 'Base de Datos' y verifica que el ID del horario coincida con la matrícula.")
            
    else:
        st.warning("No existe ese salón configurado.")

# ==========================================
# MÓDULO 4: BASE DE DATOS (SUPERVISIÓN)
# ==========================================
elif selected == "4. Base de Datos":
    st.title("📂 Datos Crudos")
    st.warning("Si aquí está vacío, es que no se está guardando nada.")
    
    st.subheader("1. Tabla Matriculas (JOIN)")
    df = pd.read_sql_query("""
        SELECT m.id, a.nombre, a.apellido, h.grupo, h.hora_inicio, h.nivel_salon, h.id as ID_HORARIO
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        JOIN horarios h ON m.horario_id = h.id
    """, sqlite3.connect(DB_NAME))
    st.dataframe(df)
    
    st.subheader("2. Tabla Horarios (IDs Reales)")
    df_h = pd.read_sql_query("SELECT id, grupo, hora_inicio, nivel_salon FROM horarios", sqlite3.connect(DB_NAME))
    st.dataframe(df_h)
