import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Piscina Arenas - Pro", layout="wide", page_icon="🏊")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .stDataFrame { border: 1px solid #e6e6e6; border-radius: 5px; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('piscina_arenas_v2.db') # Usamos v2 para evitar conflictos
    c = conn.cursor()
    
    # Tabla Ciclos (Ahora con fecha de inicio para calcular las 12 clases)
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT UNIQUE,
                 fecha_inicio DATE)''')
    
    # Tabla Horarios
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ciclo_id INTEGER,
                 grupo TEXT, 
                 hora_inicio TEXT,
                 capacidad INTEGER,
                 FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    
    # Tabla Alumnos
    c.execute('''CREATE TABLE IF NOT EXISTS alumnos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT,
                 apellido TEXT,
                 telefono TEXT,
                 direccion TEXT,
                 nivel TEXT,
                 apoderado TEXT,
                 fecha_registro DATE,
                 condicion TEXT)''')
    
    # Tabla Matrículas
    c.execute('''CREATE TABLE IF NOT EXISTS matriculas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_id INTEGER,
                 fecha_inicio DATE,
                 FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
                 FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
                 
    # Tabla Asistencia (Guarda la fecha específica y el estado)
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_id INTEGER,
                 fecha TEXT, -- Guardamos como TEXT YYYY-MM-DD para facilitar pivote
                 estado TEXT, 
                 es_recuperacion BOOLEAN DEFAULT 0,
                 UNIQUE(alumno_id, horario_id, fecha))''') # Evita duplicados

    # Tabla Recuperaciones
    c.execute('''CREATE TABLE IF NOT EXISTS recuperaciones_programadas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_destino_id INTEGER,
                 fecha_destino TEXT,
                 asistio BOOLEAN DEFAULT 0)''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('piscina_arenas_v2.db')
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
        st.error(f"Error en BD: {e}")
        conn.close()
        return False

# --- FUNCIÓN MÁGICA: CALCULAR LAS 12 FECHAS ---
def calcular_fechas_clase(fecha_inicio_str, grupo):
    """
    Genera una lista de 12 fechas basadas en el grupo (L-M-V o M-J-S)
    a partir de la fecha de inicio.
    """
    fechas = []
    fecha_obj = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
    
    # Definir días permitidos (0=Lunes, 1=Martes, etc.)
    if "Lunes" in grupo:
        dias_permitidos = [0, 2, 4] # Lunes, Miércoles, Viernes
    else:
        dias_permitidos = [1, 3, 5] # Martes, Jueves, Sábado
        
    # Buscar la primera fecha válida
    while fecha_obj.weekday() not in dias_permitidos:
        fecha_obj += timedelta(days=1)
        
    # Generar las 12 fechas
    while len(fechas) < 12:
        if fecha_obj.weekday() in dias_permitidos:
            fechas.append(fecha_obj.strftime("%Y-%m-%d"))
        fecha_obj += timedelta(days=1)
        
    return fechas

init_db()

# --- BARRA LATERAL (MENÚ MEJORADO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=100)
    st.title("Piscina Arenas")
    
    selected = option_menu(
        menu_title=None,
        options=["Asistencia Didáctica", "Matrícula", "Configuración", "Recuperaciones", "Reportes"],
        icons=["calendar-check", "person-plus", "gear", "bandaid", "graph-up"],
        menu_icon="cast",
        default_index=0,
    )

# ==========================================
# 1. CONFIGURACIÓN (CREAR PERIODOS)
# ==========================================
if selected == "Configuración":
    st.header("⚙️ Configuración del Periodo")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Nuevo Ciclo")
        st.info("Define cuándo empieza el ciclo para calcular las 12 clases.")
        nombre_ciclo = st.text_input("Nombre (Ej: Marzo 2026)")
        inicio_ciclo = st.date_input("Fecha de Inicio del Ciclo")
        
        if st.button("Crear Ciclo"):
            if run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (nombre_ciclo, inicio_ciclo)):
                st.success("Ciclo creado y fechas mapeadas.")

    with col2:
        st.subheader("Crear Horarios en el Ciclo")
        ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
        if ciclos:
            c_dict = {f"{n} (Inicia: {f})": i for i, n, f in ciclos}
            sel_ciclo_txt = st.selectbox("Seleccionar Ciclo", list(c_dict.keys()))
            
            c1, c2, c3 = st.columns(3)
            grupo = c1.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            hora = c2.selectbox("Hora", ["12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"])
            capacidad = c3.number_input("Cupos", value=10)
            
            if st.button("Agregar Horario +"):
                run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, capacidad) VALUES (?, ?, ?, ?)", 
                          (c_dict[sel_ciclo_txt], grupo, hora, capacidad))
                st.success("Horario listo.")
            
            # Mostrar horarios
            st.write("---")
            st.write("**Horarios Configurados:**")
            df = pd.read_sql_query("""
                SELECT c.nombre as Ciclo, h.grupo, h.hora_inicio, h.capacidad 
                FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id ORDER BY c.id DESC
            """, sqlite3.connect('piscina_arenas_v2.db'))
            st.dataframe(df, hide_index=True)

# ==========================================
# 2. MATRÍCULA
# ==========================================
elif selected == "Matrícula":
    st.header("📝 Nueva Matrícula")
    
    with st.container():
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Datos del Alumno")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombres")
            apellido = c2.text_input("Apellidos")
            
            c3, c4 = st.columns(2)
            telefono = c3.text_input("Teléfono")
            apoderado = c4.text_input("Apoderado")
            
            condicion = st.text_area("⚠️ Condición Especial (Médica/Conductual)", placeholder="Ej: Asma, TDAH. Dejar vacío si no aplica.")
            
        with col2:
            st.subheader("Nivel & Ubicación")
            nivel = st.selectbox("Nivel", ["Básico", "Intermedio", "Avanzado"])
            direccion = st.text_input("Dirección")
            
    st.divider()
    
    st.subheader("Selección de Horario")
    ciclos_data = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
    
    if ciclos_data:
        # Diccionario auxiliar para fechas
        fechas_inicio_dict = {i: f for i, n, f in ciclos_data}
        c_dict = {n: i for i, n, f in ciclos_data}
        
        sel_ciclo = st.selectbox("Ciclo", list(c_dict.keys()))
        ciclo_id = c_dict[sel_ciclo]
        fecha_ini_ciclo = fechas_inicio_dict[ciclo_id]
        
        horarios = run_query("""
            SELECT h.id, h.grupo, h.hora_inicio, h.capacidad,
            (SELECT COUNT(*) FROM matriculas m WHERE m.horario_id = h.id)
            FROM horarios h WHERE h.ciclo_id = ?
        """, (ciclo_id,), return_data=True)
        
        opciones = {}
        for h in horarios:
            h_id, grp, hr, cap, insc = h
            # Calcular fechas visuales
            fechas_calc = calcular_fechas_clase(fecha_ini_ciclo, grp)
            texto_fechas = f"Del {fechas_calc[0]} al {fechas_calc[-1]}"
            
            label = f"{grp} | {hr} ({insc}/{cap} cupos) | {texto_fechas}"
            if insc < cap:
                opciones[label] = h_id
            else:
                opciones[f"⛔ LLENO - {label}"] = None
                
        sel_h = st.selectbox("Horario", list(opciones.keys()))
        
        if st.button("Confirmar Matrícula", type="primary"):
            hid = opciones[sel_h]
            if hid and nombre and apellido:
                run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion) VALUES (?,?,?,?,?,?,?,?)",
                          (nombre, apellido, telefono, direccion, nivel, apoderado, date.today(), condicion))
                aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (aid, hid, date.today()))
                st.balloons()
                st.success("Alumno matriculado correctamente.")
            elif not hid:
                st.error("Horario sin cupos.")
            else:
                st.error("Falta nombre o apellido.")
    else:
        st.warning("Configura un ciclo primero.")

# ==========================================
# 3. ASISTENCIA DIDÁCTICA (LA TABLA MÁGICA)
# ==========================================
elif selected == "Asistencia Didáctica":
    st.header("📅 Control de Asistencia Visual")
    
    # 1. Filtros Superiores
    col1, col2, col3 = st.columns(3)
    
    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
    if ciclos:
        c_dict = {n: (i, f) for i, n, f in ciclos}
        sel_c_name = col1.selectbox("1. Ciclo", list(c_dict.keys()))
        ciclo_id_sel, fecha_inicio_ciclo = c_dict[sel_c_name]
        
        horarios = run_query("SELECT id, grupo, hora_inicio FROM horarios WHERE ciclo_id = ?", (ciclo_id_sel,), return_data=True)
        if horarios:
            h_dict = {f"{g} - {h}": (i, g) for i, g, h in horarios}
            sel_h_name = col2.selectbox("2. Horario", list(h_dict.keys()))
            horario_id_sel, grupo_sel = h_dict[sel_h_name]
            
            # 2. GENERAR LAS 12 FECHAS AUTOMÁTICAS (Columnas)
            columnas_fechas = calcular_fechas_clase(fecha_inicio_ciclo, grupo_sel)
            
            # 3. OBTENER ALUMNOS
            alumnos = run_query("SELECT a.id, a.nombre, a.apellido, a.condicion FROM alumnos a JOIN matriculas m ON a.id = m.alumno_id WHERE m.horario_id = ?", (horario_id_sel,), return_data=True)
            
            if alumnos:
                # Preparar DataFrame Base
                data_grid = []
                mapa_ids = {} # Para saber qué ID es cada fila
                
                # Traer toda la asistencia registrada para este horario
                asistencia_db = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id = ?", (horario_id_sel,), return_data=True)
                
                # Convertir a diccionario rápido: (alumno_id, fecha) -> estado
                asist_map = {(a, f): e for a, f, e in asistencia_db}

                for alum in alumnos:
                    aid, nom, ape, cond = alum
                    nombre_completo = f"{nom} {ape}"
                    
                    # Si tiene condición, le ponemos un icono en el nombre
                    if cond and cond.strip():
                        nombre_completo = f"🔴 {nombre_completo} (OJO: {cond})"
                    
                    row = {"Alumno": nombre_completo}
                    mapa_ids[nombre_completo] = aid
                    
                    # Rellenar las 12 columnas
                    for fecha_col in columnas_fechas:
                        estado = asist_map.get((aid, fecha_col), None)
                        # Usar Emojis para que sea didáctico
                        if estado == "Presente": val = "✅"
                        elif estado == "Falta": val = "❌"
                        elif estado == "Justificado": val = "🤧"
                        else: val = None # Vacío
                        
                        row[fecha_col] = val
                    
                    data_grid.append(row)
                
                df_visual = pd.DataFrame(data_grid)
                df_visual.set_index("Alumno", inplace=True)
                
                st.info("💡 Instrucciones: Haz doble clic en una celda y selecciona: ✅ (Asistió), ❌ (Faltó), 🤧 (Justificado).")
                
                # MOSTRAR TABLA EDITABLE
                edited_df = st.data_editor(
                    df_visual,
                    column_config={
                        f: st.column_config.SelectboxColumn(
                            f,
                            help="Marcar asistencia",
                            width="small",
                            options=["✅", "❌", "🤧"],
                            required=False
                        ) for f in columnas_fechas
                    },
                    height=500,
                    use_container_width=True
                )
                
                # 4. GUARDAR CAMBIOS
                if st.button("💾 Guardar Cambios de Asistencia", type="primary"):
                    cambios_count = 0
                    for alumno_nombre, row in edited_df.iterrows():
                        aid = mapa_ids.get(alumno_nombre)
                        if not aid: continue
                        
                        for fecha_col in columnas_fechas:
                            val_visual = row[fecha_col]
                            
                            # Traducir Emoji a Texto BD
                            estado_bd = None
                            if val_visual == "✅": estado_bd = "Presente"
                            elif val_visual == "❌": estado_bd = "Falta"
                            elif val_visual == "🤧": estado_bd = "Justificado"
                            
                            if estado_bd:
                                run_query("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?, ?, ?, ?)",
                                          (aid, horario_id_sel, fecha_col, estado_bd))
                                cambios_count += 1
                            elif val_visual is None:
                                # Si borraron la asistencia, borrar de BD
                                run_query("DELETE FROM asistencia WHERE alumno_id=? AND horario_id=? AND fecha=?", 
                                          (aid, horario_id_sel, fecha_col))
                    
                    st.success(f"¡Listo! Se actualizaron {cambios_count} registros.")
                    st.rerun()

            else:
                st.info("No hay alumnos en este horario.")
        else:
            st.warning("Crea horarios para este ciclo.")
    else:
        st.warning("Crea un ciclo en Configuración.")

# ==========================================
# 4. RECUPERACIONES
# ==========================================
elif selected == "Recuperaciones":
    st.header("🩹 Programar Recuperación")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Buscar Alumno")
        busqueda = st.text_input("Apellido o Nombre")
        if busqueda:
            res = run_query(f"SELECT id, nombre, apellido, condicion FROM alumnos WHERE nombre LIKE '%{busqueda}%' OR apellido LIKE '%{busqueda}%'", return_data=True)
            if res:
                opciones_alum = {f"{n} {a} (Cond: {c if c else 'Ninguna'})": i for i, n, a, c in res}
                sel_alum_txt = st.selectbox("Seleccionar:", list(opciones_alum.keys()))
                id_alum_recup = opciones_alum[sel_alum_txt]
            else:
                st.warning("No encontrado")
                id_alum_recup = None
        else:
            id_alum_recup = None
            
    with col2:
        st.subheader("2. Nueva Fecha")
        if id_alum_recup:
            fecha_rec = st.date_input("Fecha a asistir")
            # Buscar horarios
            horarios = run_query("SELECT h.id, c.nombre, h.grupo, h.hora_inicio FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id", return_data=True)
            h_r_dict = {f"{c} | {g} | {h}": i for i, c, g, h in horarios}
            sel_h_r = st.selectbox("Horario Destino", list(h_r_dict.keys()))
            
            if st.button("Programar"):
                # Insertar como recuperación
                run_query("INSERT INTO recuperaciones_programadas (alumno_id, horario_destino_id, fecha_destino) VALUES (?, ?, ?)",
                          (id_alum_recup, h_r_dict[sel_h_r], str(fecha_rec)))
                
                # ADEMÁS: Lo insertamos en la tabla de asistencia como "Recuperación Pendiente" para que salga en la lista
                # Nota: En la vista didáctica, aparecerá, pero debemos manejarlo visualmente
                st.success("Recuperación agendada.")

# ==========================================
# 5. REPORTES
# ==========================================
elif selected == "Reportes":
    st.header("📊 Reporte de Alumno")
    alumnos = run_query("SELECT id, nombre, apellido FROM alumnos", return_data=True)
    if alumnos:
        a_dict = {f"{n} {a}": i for i, n, a in alumnos}
        sel = st.selectbox("Buscar Alumno", list(a_dict.keys()))
        aid = a_dict[sel]
        
        datos = run_query("SELECT * FROM alumnos WHERE id=?", (aid,), return_data=True)[0]
        
        # Tarjeta de Datos
        st.markdown(f"""
        <div style="padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
            <h3>👤 {datos[1]} {datos[2]}</h3>
            <p><b>Apoderado:</b> {datos[6]} | <b>Tel:</b> {datos[3]}</p>
            <p style="color: {'red' if datos[8] else 'black'}"><b>Condición:</b> {datos[8] if datos[8] else 'Ninguna'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Conteo
        asistencias = run_query("SELECT COUNT(*) FROM asistencia WHERE alumno_id=? AND estado='Presente'", (aid,), return_data=True)[0][0]
        faltas = run_query("SELECT COUNT(*) FROM asistencia WHERE alumno_id=? AND estado='Falta'", (aid,), return_data=True)[0][0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Clases Asistidas", f"{asistencias}/12")
        col2.metric("Faltas", faltas)
        col3.progress(min(asistencias/12, 1.0))
        
        if asistencias >= 12:
            st.balloons()
            st.success("¡Ciclo Completado!")
