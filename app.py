import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Piscina Arenas - Gestión", layout="wide", page_icon="🏊")

# --- GESTIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('piscina_arenas.db')
    c = conn.cursor()
    
    # Tabla Ciclos (Ej: 2026-1)
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT UNIQUE)''')
    
    # Tabla Horarios
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ciclo_id INTEGER,
                 grupo TEXT, -- L-M-V o M-J-S
                 hora_inicio TEXT,
                 capacidad INTEGER,
                 FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    
    # Tabla Alumnos (Incluye campo 'condicion')
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
                 
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_id INTEGER,
                 fecha DATE,
                 estado TEXT, -- Presente, Falta, Recuperación
                 es_recuperacion BOOLEAN DEFAULT 0)''')

    # Tabla Programación de Recuperaciones
    c.execute('''CREATE TABLE IF NOT EXISTS recuperaciones_programadas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 alumno_id INTEGER,
                 horario_destino_id INTEGER,
                 fecha_destino DATE,
                 asistio BOOLEAN DEFAULT 0)''')
    
    # PARCHE DE SEGURIDAD: Agregar columna condicion si la tabla ya existía sin ella
    try:
        c.execute("ALTER TABLE alumnos ADD COLUMN condicion TEXT")
    except:
        pass # La columna ya existe, ignoramos el error

    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('piscina_arenas.db')
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
        st.error(f"Error en base de datos: {e}")
        conn.close()
        return False

# Inicializar DB al arrancar
init_db()

# --- INTERFAZ DE USUARIO ---

st.title("🏊 Piscina Arenas - Sistema de Gestión")

# Crear menú lateral
menu = st.sidebar.selectbox("Menú Principal", 
                            ["Asistencia", "Matrícula", "Configuración (Horarios/Ciclos)", "Recuperaciones", "Reportes"])

# --- MÓDULO CONFIGURACIÓN ---
if menu == "Configuración (Horarios/Ciclos)":
    st.header("Configuración de Ciclos y Horarios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Crear Nuevo Ciclo")
        nuevo_ciclo = st.text_input("Nombre del Ciclo (Ej: 2026-1)")
        if st.button("Crear Ciclo"):
            if run_query("INSERT INTO ciclos (nombre) VALUES (?)", (nuevo_ciclo,)):
                st.success(f"Ciclo {nuevo_ciclo} creado.")
    
    with col2:
        st.subheader("2. Crear Horario")
        ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos:
            ciclo_dict = {nombre: id for id, nombre in ciclos}
            sel_ciclo = st.selectbox("Seleccionar Ciclo", list(ciclo_dict.keys()))
            
            grupo = st.selectbox("Grupo de Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            hora = st.selectbox("Hora", ["12:00 - 13:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00", "16:00 - 17:00"])
            capacidad = st.number_input("Capacidad de Cupos", min_value=1, value=10)
            
            if st.button("Agregar Horario"):
                run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, capacidad) VALUES (?, ?, ?, ?)", 
                          (ciclo_dict[sel_ciclo], grupo, hora, capacidad))
                st.success("Horario agregado.")
        else:
            st.warning("Primero crea un ciclo.")

    st.divider()
    st.subheader("Horarios Existentes")
    if ciclos:
        df_horarios = pd.read_sql_query("""
            SELECT h.id, c.nombre as Ciclo, h.grupo, h.hora_inicio, h.capacidad 
            FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id
        """, sqlite3.connect('piscina_arenas.db'))
        st.dataframe(df_horarios)

# --- MÓDULO MATRÍCULA ---
elif menu == "Matrícula":
    st.header("Inscripción de Alumnos")
    
    with st.form("form_matricula"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombres del Niño")
            apellido = st.text_input("Apellidos")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
        with col2:
            nivel = st.selectbox("Nivel", ["Básico", "Intermedio", "Avanzado"])
            apoderado = st.text_input("Nombre Apoderado")
            # CAMPO DE CONDICIÓN
            condicion = st.text_area("Condición Especial / Observaciones Médicas (Opcional)", 
                                     placeholder="Ej: Asma, TDAH, Alergia al cloro, etc. Dejar vacío si no aplica.")
            
        st.divider()
        st.write("Selección de Horario")
        
        # Obtener horarios con cupos disponibles
        ciclos_disp = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos_disp:
            c_dict = {n: i for i, n in ciclos_disp}
            sel_ciclo_mat = st.selectbox("Ciclo", list(c_dict.keys()))
            
            horarios_data = run_query("""
                SELECT h.id, h.grupo, h.hora_inicio, h.capacidad, 
                (SELECT COUNT(*) FROM matriculas m WHERE m.horario_id = h.id) as inscritos
                FROM horarios h WHERE h.ciclo_id = ?
            """, (c_dict[sel_ciclo_mat],), return_data=True)
            
            opciones_horario = {}
            for h in horarios_data:
                h_id, grp, hora, cap, insc = h
                label = f"{grp} | {hora} | Cupos: {insc}/{cap}"
                if insc < cap:
                    opciones_horario[label] = h_id
                else:
                    opciones_horario[f"AGOTADO - {label}"] = None
            
            sel_horario_txt = st.selectbox("Horario Disponible", options=list(opciones_horario.keys()))
            
            submitted = st.form_submit_button("Matricular Alumno")
            
            if submitted:
                h_selected_id = opciones_horario[sel_horario_txt]
                if h_selected_id and nombre and apellido:
                    # Insertar Alumno con CONDICIÓN
                    run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (nombre, apellido, telefono, direccion, nivel, apoderado, date.today(), condicion))
                    
                    alumno_id = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                    
                    # Matricular
                    run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?, ?, ?)",
                              (alumno_id, h_selected_id, date.today()))
                    st.success(f"Alumno {nombre} {apellido} matriculado exitosamente.")
                elif not h_selected_id:
                    st.error("El horario seleccionado está lleno.")
                else:
                    st.error("Faltan datos obligatorios.")
        else:
            st.warning("No hay ciclos configurados.")

# --- MÓDULO ASISTENCIA ---
elif menu == "Asistencia":
    st.header("Control de Asistencia")
    
    col_a, col_b, col_c = st.columns(3)
    fecha_hoy = col_a.date_input("Fecha", date.today())
    
    # Selectores para filtrar la lista
    ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
    if ciclos:
        c_dict = {n: i for i, n in ciclos}
        sel_ciclo_asist = col_b.selectbox("Ciclo", list(c_dict.keys()))
        
        horarios_asist = run_query("SELECT id, grupo, hora_inicio FROM horarios WHERE ciclo_id = ?", (c_dict[sel_ciclo_asist],), return_data=True)
        h_dict = {f"{g} - {h}": i for i, g, h in horarios_asist}
        sel_horario_asist = col_c.selectbox("Horario", list(h_dict.keys()))
        horario_id_actual = h_dict[sel_horario_asist]
        
        # BUSCADOR
        st.write("---")
        search_term = st.text_input("🔍 Buscar alumno por nombre...", "")
        
        # Lógica principal: Traer alumnos matriculados + Alumnos en recuperación para este día
        # SE INCLUYE EL CAMPO 'condicion'
        query_alumnos = """
            SELECT a.id, a.nombre, a.apellido, a.condicion, 'Matriculado' as tipo
            FROM alumnos a
            JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.horario_id = ?
            UNION
            SELECT a.id, a.nombre, a.apellido, a.condicion, 'RECUPERACIÓN' as tipo
            FROM alumnos a
            JOIN recuperaciones_programadas rp ON a.id = rp.alumno_id
            WHERE rp.horario_destino_id = ? AND rp.fecha_destino = ?
        """
        
        alumnos_lista = run_query(query_alumnos, (horario_id_actual, horario_id_actual, fecha_hoy), return_data=True)
        
        if alumnos_lista:
            # Convertir a DataFrame incluyendo columna Condicion
            df_asist = pd.DataFrame(alumnos_lista, columns=['ID', 'Nombre', 'Apellido', 'Condicion_Medica', 'Tipo'])
            
            # Filtro de búsqueda
            if search_term:
                df_asist = df_asist[df_asist['Nombre'].str.contains(search_term, case=False) | df_asist['Apellido'].str.contains(search_term, case=False)]
            
            st.subheader(f"Lista de Clase ({len(df_asist)} alumnos)")
            
            # Formulario de asistencia
            with st.form("asistencia_form"):
                estados = {}
                for index, row in df_asist.iterrows():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    
                    # LOGICA DE VISUALIZACIÓN DE CONDICIÓN
                    tiene_condicion = row['Condicion_Medica'] and row['Condicion_Medica'].strip() != ""
                    
                    with col1:
                        if tiene_condicion:
                            # NOMBRE EN ROJO CON ALERTA
                            st.markdown(f"🔴 :red[**{row['Nombre']} {row['Apellido']}**]")
                            st.caption(f"⚠️ **OJO:** {row['Condicion_Medica']}")
                        else:
                            st.markdown(f"**{row['Nombre']} {row['Apellido']}**")
                    
                    with col2:
                        if row['Tipo'] == 'RECUPERACIÓN':
                            st.warning("Recupera hoy")
                        else:
                            if tiene_condicion:
                                st.caption("Regular (Con Obs.)")
                            else:
                                st.caption("Regular")
                                
                    with col3:
                        # Verificar si ya se tomó asistencia antes
                        prev_asist = run_query("SELECT estado FROM asistencia WHERE alumno_id=? AND fecha=? AND horario_id=?", 
                                               (row['ID'], fecha_hoy, horario_id_actual), return_data=True)
                        default_idx = 0
                        if prev_asist:
                            est = prev_asist[0][0]
                            if est == 'Presente': default_idx = 0
                            elif est == 'Falta': default_idx = 1
                            elif est == 'Justificado': default_idx = 2
                        
                        estados[row['ID']] = st.radio(f"Estado {row['ID']}", ["Presente", "Falta", "Justificado"], 
                                                      index=default_idx, horizontal=True, key=row['ID'], label_visibility="collapsed")
                
                if st.form_submit_button("Guardar Asistencia"):
                    for alum_id, estado in estados.items():
                        # Upsert lógica simplificada: borrar previo e insertar nuevo
                        run_query("DELETE FROM asistencia WHERE alumno_id=? AND fecha=? AND horario_id=?", (alum_id, fecha_hoy, horario_id_actual))
                        
                        es_recup = 1 if df_asist[df_asist['ID'] == alum_id]['Tipo'].values[0] == 'RECUPERACIÓN' else 0
                        
                        run_query("INSERT INTO asistencia (alumno_id, horario_id, fecha, estado, es_recuperacion) VALUES (?, ?, ?, ?, ?)",
                                  (alum_id, horario_id_actual, fecha_hoy, estado, es_recup))
                        
                    st.success("Asistencia guardada correctamente.")
        else:
            st.info("No hay alumnos inscritos en este horario o recuperaciones programadas.")

# --- MÓDULO RECUPERACIONES ---
elif menu == "Recuperaciones":
    st.header("Programar Recuperación de Clases")
    st.markdown("Selecciona un alumno que faltó para asignarle un horario en otro día.")
    
    # 1. Buscar Alumno
    alumnos_all = run_query("SELECT id, nombre, apellido FROM alumnos", return_data=True)
    if alumnos_all:
        alum_dict = {f"{n} {a} (ID: {i})": i for i, n, a in alumnos_all}
        sel_alum = st.selectbox("Seleccionar Alumno", list(alum_dict.keys()))
        alum_id = alum_dict[sel_alum]
        
        # 2. Elegir día y hora de recuperación
        st.subheader("Datos de la Recuperación")
        col1, col2 = st.columns(2)
        fecha_recup = col1.date_input("Fecha a recuperar")
        
        # Traer horarios disponibles
        horarios_disp = run_query("""
             SELECT h.id, c.nombre, h.grupo, h.hora_inicio 
             FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id
        """, return_data=True)
        
        h_recup_dict = {f"{c} | {g} | {h}": i for i, c, g, h in horarios_disp}
        sel_h_recup = col2.selectbox("Horario donde asistirá", list(h_recup_dict.keys()))
        
        if st.button("Programar Recuperación"):
            run_query("INSERT INTO recuperaciones_programadas (alumno_id, horario_destino_id, fecha_destino) VALUES (?, ?, ?)",
                      (alum_id, h_recup_dict[sel_h_recup], fecha_recup))
            st.success("Recuperación programada. El alumno aparecerá en la lista de asistencia de ese día marcado como 'RECUPERACIÓN'.")

# --- MÓDULO REPORTES ---
elif menu == "Reportes":
    st.header("Información del Alumno")
    alumnos_all = run_query("SELECT id, nombre, apellido FROM alumnos", return_data=True)
    if alumnos_all:
        alum_dict = {f"{n} {a} (ID: {i})": i for i, n, a in alumnos_all}
        sel_alum = st.selectbox("Ver historial de:", list(alum_dict.keys()))
        id_sel = alum_dict[sel_alum]
        
        # Datos básicos
        datos = run_query("SELECT * FROM alumnos WHERE id=?", (id_sel,), return_data=True)[0]
        # datos: id, nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion
        
        st.write(f"**Apoderado:** {datos[6]} | **Tel:** {datos[3]} | **Nivel:** {datos[5]}")
        
        if datos[8] and datos[8].strip() != "":
            st.error(f"⚠️ **CONDICIÓN ESPECIAL:** {datos[8]}")
        
        # Historial de Asistencia
        st.subheader("Historial de Asistencia")
        historial = run_query("""
            SELECT fecha, estado, es_recuperacion 
            FROM asistencia WHERE alumno_id = ? ORDER BY fecha DESC
        """, (id_sel,), return_data=True)
        
        if historial:
            df_hist = pd.DataFrame(historial, columns=['Fecha', 'Estado', 'Es Recuperación'])
            df_hist['Es Recuperación'] = df_hist['Es Recuperación'].apply(lambda x: 'Sí' if x else 'No')
            st.table(df_hist)
            
            # Conteo de clases (Regla de 12)
            total_asistencias = len(df_hist[df_hist['Estado'] == 'Presente'])
            st.metric("Clases Asistidas", f"{total_asistencias} / 12")
            if total_asistencias >= 12:
                st.success("🎉 Ciclo completado")
            else:
                st.info(f"Faltan {12 - total_asistencias} clases para completar el ciclo.")
