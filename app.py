import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Piscina Arenas - Sistema Final", layout="wide", page_icon="🏊")

# CONSTANTES GLOBALES (Para evitar errores de escritura)
LISTA_DIAS = ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"]
LISTA_NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]
LISTA_HORAS = [
    "07:00 - 08:00", "08:00 - 09:00", "09:00 - 10:00", "10:00 - 11:00", 
    "11:00 - 12:00", "12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00",
    "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00",
    "19:00 - 20:00", "20:00 - 21:00"
]
DB_NAME = "sistema_arenas_v8_clean.db"

# ESTILOS CSS
st.markdown("""
<style>
    div.row-widget.stRadio > div {flex-direction: row;}
    .stDataFrame { border: 1px solid #ccc; }
    .success-box { padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; }
    .error-box { padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. GESTIÓN DE BASE DE DATOS
# ==========================================
def init_db():
    """Crea las tablas si no existen."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla Ciclos
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT,
                 fecha_inicio DATE)''')
    
    # Tabla Horarios (Aquí se define el Salón)
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ciclo_id INTEGER,
                 grupo TEXT,         -- Ej: Lunes-Miercoles-Viernes
                 hora_inicio TEXT,   -- Ej: 07:00 - 08:00
                 nivel_salon TEXT,   -- Ej: Básico 0
                 capacidad INTEGER,
                 FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    
    # Tabla Alumnos
    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT,
                 apellido TEXT,
                 telefono TEXT,
                 direccion TEXT,
                 nivel TEXT,         -- Nivel asignado al niño
                 apoderado TEXT,
                 fecha_registro DATE,
                 condicion TEXT)''')
    
    # Tabla Matrículas (Une Alumno con Horario)
    c.execute('''CREATE TABLE IF NOT EXISTS matriculas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_id INTEGER, -- ID único del salón
                 fecha_inicio DATE,
                 FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
                 FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
    
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_id INTEGER,
                 fecha TEXT,
                 estado TEXT,
                 UNIQUE(alumno_id, horario_id, fecha))''')
    
    # Tabla Recuperaciones
    c.execute('''CREATE TABLE IF NOT EXISTS recuperaciones (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 fecha_destino TEXT)''')
                 
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    """Ejecuta queries de forma segura."""
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
        st.error(f"Error Database: {e}")
        conn.close()
        return False

def get_fechas_clase(start_date_str, grupo):
    """Calcula las 12 fechas de clase."""
    fechas = []
    try:
        current_date = datetime.strptime(str(start_date_str), "%Y-%m-%d").date()
    except:
        current_date = date.today()

    if "Lunes" in grupo: target_days = [0, 2, 4] # L, M, V
    else: target_days = [1, 3, 5] # M, J, S
    
    # Avanzar hasta el primer día de clase válido
    while current_date.weekday() not in target_days:
        current_date += timedelta(days=1)
        
    # Generar 12 clases
    while len(fechas) < 12:
        if current_date.weekday() in target_days:
            fechas.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    return fechas

# Inicializar DB
init_db()

# ==========================================
# 2. INTERFAZ DE USUARIO
# ==========================================

# Menú Lateral
with st.sidebar:
    selected = option_menu(
        menu_title="Piscina Arenas",
        options=["1. Configuración", "2. Matrícula", "3. Asistencia", "4. Reportes", "5. Diagnóstico"],
        icons=["gear", "person-plus", "calendar-check", "file-text", "bug"],
        default_index=0,
    )

# ---------------------------------------------------------------------
# MÓDULO 1: CONFIGURACIÓN (Crear Ciclos y Aulas)
# ---------------------------------------------------------------------
if selected == "1. Configuración":
    st.header("⚙️ Configuración del Sistema")
    
    tab1, tab2 = st.tabs(["Crear Ciclo", "Crear Salones (Horarios)"])
    
    with tab1:
        st.subheader("Paso 1: Define el Periodo")
        nombre_ciclo = st.text_input("Nombre del Ciclo (Ej: Marzo 2026)")
        inicio_ciclo = st.date_input("Fecha de Inicio")
        if st.button("Guardar Ciclo"):
            if nombre_ciclo:
                run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (nombre_ciclo, inicio_ciclo))
                st.success(f"Ciclo '{nombre_ciclo}' creado exitosamente.")
            else:
                st.error("El nombre es obligatorio.")

    with tab2:
        st.subheader("Paso 2: Abre los Salones")
        
        # Selectores
        ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
        if ciclos:
            ciclo_dict = {n: i for i, n in ciclos}
            sel_ciclo = st.selectbox("Seleccionar Ciclo", list(ciclo_dict.keys()))
            id_ciclo_sel = ciclo_dict[sel_ciclo]
            
            c1, c2 = st.columns(2)
            sel_dias = c1.radio("Días", LISTA_DIAS)
            sel_hora = c2.selectbox("Hora", LISTA_HORAS)
            
            c3, c4 = st.columns(2)
            sel_nivel = c3.selectbox("Nivel del Salón", LISTA_NIVELES)
            capacidad = c4.number_input("Cupos", value=10, min_value=1)
            
            if st.button("Crear Salón"):
                # Verificar duplicados
                existe = run_query("SELECT id FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", 
                                   (id_ciclo_sel, sel_dias, sel_hora, sel_nivel), return_data=True)
                if existe:
                    st.warning("⚠️ Este salón ya existe.")
                else:
                    run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, nivel_salon, capacidad) VALUES (?,?,?,?,?)",
                              (id_ciclo_sel, sel_dias, sel_hora, sel_nivel, capacidad))
                    st.success(f"✅ Salón de {sel_nivel} a las {sel_hora} creado.")
            
            # Mostrar salones creados
            st.divider()
            st.write(f"Salones en **{sel_ciclo}**:")
            df_salones = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={id_ciclo_sel} ORDER BY hora_inicio", sqlite3.connect(DB_NAME))
            st.dataframe(df_salones, use_container_width=True)
        else:
            st.warning("Primero crea un Ciclo en la pestaña anterior.")

# ---------------------------------------------------------------------
# MÓDULO 2: MATRÍCULA
# ---------------------------------------------------------------------
elif selected == "2. Matrícula":
    st.header("📝 Matricular Alumno")
    
    # 1. Datos Personales
    with st.container():
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombres")
        apellido = col2.text_input("Apellidos")
        tlf = col1.text_input("Teléfono")
        apo = col2.text_input("Apoderado")
        nivel_asignado = st.selectbox("Nivel del Niño", LISTA_NIVELES)
        cond = st.text_area("Condición Especial (Médica/Conductual)", placeholder="Ej: TDAH, Asma... (Dejar vacío si no tiene)")

    st.divider()
    
    # 2. Buscador de Salones (Lógica Crítica para que no falle)
    st.subheader("Selección de Horario")
    
    ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
    if ciclos:
        c_dict = {n: i for i, n in ciclos}
        sel_c = st.selectbox("Ciclo", list(c_dict.keys()), key="mat_ciclo")
        id_c = c_dict[sel_c]
        
        sel_d = st.radio("Días", LISTA_DIAS, horizontal=True, key="mat_dias")
        
        # Filtramos horarios disponibles en la DB para ese ciclo y día
        horarios_disp = run_query("""
            SELECT id, hora_inicio, nivel_salon, capacidad 
            FROM horarios 
            WHERE ciclo_id=? AND grupo=? 
            ORDER BY hora_inicio
        """, (id_c, sel_d), return_data=True)
        
        if horarios_disp:
            opciones_visuales = {}
            for h in horarios_disp:
                hid, h_ini, h_niv, h_cap = h
                
                # Contar inscritos reales
                inscritos = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                
                texto = f"{h_ini} | Nivel: {h_niv} | Cupos: {inscritos}/{h_cap}"
                
                # Bloquear si está lleno
                if inscritos < h_cap:
                    opciones_visuales[texto] = hid
                else:
                    opciones_visuales[f"⛔ LLENO - {texto}"] = None
            
            sel_h_texto = st.selectbox("Salones Disponibles:", list(opciones_visuales.keys()))
            
            # Botón de Matricula
            if st.button("Confirmar Matrícula", type="primary"):
                hid_final = opciones_visuales[sel_h_texto]
                
                if hid_final and nombre and apellido:
                    # Guardar Alumno
                    run_query("INSERT INTO alumnos (nombre, apellido, telefono, nivel, apoderado, fecha_registro, condicion) VALUES (?,?,?,?,?,?,?)",
                              (nombre, apellido, tlf, nivel_asignado, apo, date.today(), cond))
                    
                    # Obtener ID del alumno creado
                    aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                    
                    # Guardar Matrícula (Relación)
                    run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)",
                              (aid, hid_final, date.today()))
                    
                    st.balloons()
                    st.success(f"✅ Alumno {nombre} {apellido} matriculado correctamente.")
                elif not hid_final:
                    st.error("El horario seleccionado está lleno.")
                else:
                    st.error("Faltan datos (Nombre/Apellido).")
        else:
            st.warning("No hay horarios creados para estos días en este ciclo.")
    else:
        st.warning("Configura un ciclo primero.")

# ---------------------------------------------------------------------
# MÓDULO 3: ASISTENCIA (CORREGIDO PARA QUE SIEMPRE MUESTRE DATOS)
# ---------------------------------------------------------------------
elif selected == "3. Asistencia":
    st.header("📅 Control de Asistencia")

    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos:
        st.warning("Sin ciclos configurados.")
        st.stop()

    # 1. Filtros Superiores
    c_dict = {n: (i, f) for i, n, f in ciclos}
    sel_c = st.selectbox("Ciclo:", list(c_dict.keys()))
    id_c, fecha_ini = c_dict[sel_c]
    
    st.write("---")
    c1, c2 = st.columns(2)
    sel_d = c1.radio("Días:", LISTA_DIAS, horizontal=True)
    
    # Obtener horas disponibles
    horas_db = run_query("SELECT DISTINCT hora_inicio FROM horarios WHERE ciclo_id=? AND grupo=? ORDER BY hora_inicio", 
                         (id_c, sel_d), return_data=True)
    
    if not horas_db:
        st.info("No hay horarios para estos días.")
    else:
        lista_h = [x[0] for x in horas_db]
        sel_h = st.radio("Hora:", lista_h, horizontal=True)
        
        # Obtener salones disponibles en esa hora
        niveles_db = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                               (id_c, sel_d, sel_h), return_data=True)
        
        if niveles_db:
            # Diccionario ID -> Nombre
            dict_salones = {n: i for i, n in niveles_db}
            sel_n = st.selectbox("Salón (Nivel):", list(dict_salones.keys()))
            id_horario_actual = dict_salones[sel_n] # ¡ESTA ES LA CLAVE! USAMOS EL ID DIRECTO
            
            # --- TABLA DE ASISTENCIA ---
            st.divider()
            
            # 1. Calcular fechas
            fechas = get_fechas_clase(fecha_ini, sel_d)
            
            # 2. Buscar alumnos matriculados en ESTE id_horario
            alumnos = run_query("""
                SELECT a.id, a.nombre, a.apellido, a.condicion 
                FROM alumnos a
                JOIN matriculas m ON a.id = m.alumno_id
                WHERE m.horario_id = ?
            """, (id_horario_actual,), return_data=True)
            
            if alumnos:
                # 3. Buscar asistencia previa
                asist_raw = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (id_horario_actual,), return_data=True)
                mapa_asist = {(a, f): e for a, f, e in asist_raw}
                
                datos_tabla = []
                for alum in alumnos:
                    aid, nom, ape, cond = alum
                    nombre_full = f"{nom} {ape}"
                    if cond: nombre_full = f"🔴 {nombre_full}" # Alerta visual
                    
                    fila = {"ID": aid, "Alumno": nombre_full}
                    
                    for f in fechas:
                        # Recuperar estado o dejar vacío
                        est = mapa_asist.get((aid, f))
                        val = False
                        if est == "Presente": val = True
                        fila[f] = val
                    
                    datos_tabla.append(fila)
                
                df = pd.DataFrame(datos_tabla)
                
                # Configurar Editor
                col_config = {"ID": None, "Alumno": st.column_config.TextColumn(disabled=True)}
                for f in fechas:
                    col_config[f] = st.column_config.CheckboxColumn(f[5:], default=False) # Muestra mes-dia
                
                st.info("Marca las casillas para 'Presente'. Desmarca para 'Falta'.")
                df_editado = st.data_editor(df, column_config=col_config, hide_index=True, use_container_width=True, height=400)
                
                # BOTÓN GUARDAR
                if st.button("💾 Guardar Asistencia", type="primary"):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    for idx, row in df_editado.iterrows():
                        aid = row['ID']
                        for f in fechas:
                            asistio = row[f]
                            estado = "Presente" if asistio else "Falta"
                            
                            # Insertar o Reemplazar
                            cursor.execute("""
                                INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado)
                                VALUES (?, ?, ?, ?)
                            """, (aid, id_horario_actual, f, estado))
                    
                    conn.commit()
                    conn.close()
                    st.success("¡Datos guardados!")
                    st.rerun()
            
            else:
                st.warning(f"El salón '{sel_n}' existe, pero no tiene alumnos matriculados aún.")
                st.markdown("[Ir a Matrícula para inscribir a alguien](#matricular-alumno)")

# ---------------------------------------------------------------------
# MÓDULO 4: REPORTES
# ---------------------------------------------------------------------
elif selected == "4. Reportes":
    st.header("📊 Reportes")
    
    busq = st.text_input("Buscar alumno por apellido:")
    if busq:
        res = run_query(f"SELECT * FROM alumnos WHERE apellido LIKE '%{busq}%'", return_data=True)
        if res:
            for r in res:
                st.markdown(f"**{r[1]} {r[2]}** (Tel: {r[3]})")
                if r[8]: st.error(f"Condición: {r[8]}")
                st.divider()

# ---------------------------------------------------------------------
# MÓDULO 5: DIAGNÓSTICO (PARA VER SI SE GUARDA)
# ---------------------------------------------------------------------
elif selected == "5. Diagnóstico":
    st.header("🔍 Diagnóstico de Base de Datos")
    st.info("Aquí puedes ver los datos crudos para verificar que se están guardando.")
    
    st.subheader("Tabla: Matrículas (Últimas 10)")
    df_m = pd.read_sql_query("""
        SELECT m.id, a.nombre, a.apellido, h.hora_inicio, h.nivel_salon 
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        JOIN horarios h ON m.horario_id = h.id
        ORDER BY m.id DESC LIMIT 10
    """, sqlite3.connect(DB_NAME))
    st.dataframe(df_m)
    
    st.subheader("Tabla: Horarios Creados")
    df_h = pd.read_sql_query("SELECT * FROM horarios", sqlite3.connect(DB_NAME))
    st.dataframe(df_h)
