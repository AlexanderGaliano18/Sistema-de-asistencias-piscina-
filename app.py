import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Piscina Arenas - Gestión", layout="wide", page_icon="🏊")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.row-widget.stRadio > div {flex-direction: row; gap: 10px;}
    div.row-widget.stRadio > div > label {
        background-color: #f0f2f6; padding: 10px 20px; border-radius: 8px; cursor: pointer; border: 1px solid #dcdcdc;
    }
    div.row-widget.stRadio > div > label:hover {background-color: #e0e2e6;}
    div.row-widget.stRadio > div > label[data-baseweb="radio"] {background-color: #ff4b4b; color: white;}
    .stDataFrame { border: 1px solid #e6e6e6; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('piscina_arenas_final.db')
    c = conn.cursor()
    
    # Tablas Principales
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 ciclo_id INTEGER, 
                 grupo TEXT, 
                 hora_inicio TEXT, 
                 capacidad INTEGER,
                 FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    
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
    
    # Tabla Matriculas vincula Alumno con Horario
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
                 fecha TEXT, 
                 estado TEXT, 
                 UNIQUE(alumno_id, horario_id, fecha))''')
    
    # Tabla Recuperaciones
    c.execute('''CREATE TABLE IF NOT EXISTS recuperaciones_programadas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_destino_id INTEGER, 
                 fecha_destino TEXT)''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('piscina_arenas_final.db')
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

# --- FUNCIÓN: CALCULAR FECHAS ---
def calcular_fechas_clase(fecha_inicio_str, grupo):
    fechas = []
    fecha_obj = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
    
    if "Lunes" in grupo: dias_permitidos = [0, 2, 4] # L-M-V
    else: dias_permitidos = [1, 3, 5] # M-J-S
        
    while fecha_obj.weekday() not in dias_permitidos:
        fecha_obj += timedelta(days=1)
        
    while len(fechas) < 12:
        if fecha_obj.weekday() in dias_permitidos:
            fechas.append(fecha_obj.strftime("%Y-%m-%d"))
        fecha_obj += timedelta(days=1)
    return fechas

init_db()

# --- MENÚ ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=100)
    selected = option_menu(
        menu_title=None,
        options=["Asistencia", "Matrícula", "Configuración", "Recuperaciones", "Reportes"],
        icons=["calendar-check", "person-plus", "gear", "bandaid", "graph-up"],
        default_index=0,
    )

# ==========================================
# 1. ASISTENCIA
# ==========================================
if selected == "Asistencia":
    st.title("📅 Tomar Asistencia")

    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos:
        st.warning("⚠️ Primero crea un ciclo en 'Configuración'.")
        st.stop()

    c_dict = {n: (i, f) for i, n, f in ciclos}
    nombre_ciclo_sel = st.selectbox("Seleccionar Ciclo:", list(c_dict.keys()))
    id_ciclo, fecha_inicio_ciclo = c_dict[nombre_ciclo_sel]

    st.write("---")
    col_g, col_h = st.columns([1, 2])
    
    with col_g:
        grupo_sel = st.radio("Días:", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], label_visibility="collapsed")

    horarios_db = run_query("SELECT id, hora_inicio, capacidad FROM horarios WHERE ciclo_id = ? AND grupo = ?", (id_ciclo, grupo_sel), return_data=True)
    
    if not horarios_db:
        st.info("No hay horarios creados para este grupo.")
        st.stop()
        
    h_dict = {h: i for i, h, cap in horarios_db}
    with col_h:
        hora_texto = st.radio("Hora:", list(h_dict.keys()), horizontal=True, label_visibility="collapsed")
        
    id_horario = h_dict[hora_texto]
    
    st.write("---")
    
    fechas_clase = calcular_fechas_clase(fecha_inicio_ciclo, grupo_sel)
    
    # Buscar Alumnos Matriculados + Recuperaciones de HOY
    alumnos = run_query("""
        SELECT a.id, a.nombre, a.apellido, a.condicion 
        FROM alumnos a 
        JOIN matriculas m ON a.id = m.alumno_id 
        WHERE m.horario_id = ?
    """, (id_horario,), return_data=True)

    if alumnos:
        data_rows = []
        asist_data = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (id_horario,), return_data=True)
        asist_map = {(a, f): e for a, f, e in asist_data}

        for alum in alumnos:
            aid, nom, ape, cond = alum
            display_name = f"{nom} {ape}"
            if cond and cond.strip(): display_name = f"🔴 {nom} {ape} ({cond})"
            
            row = {"ID": aid, "Alumno": display_name}
            for f in fechas_clase:
                row[f] = True if asist_map.get((aid, f)) == "Presente" else False
            data_rows.append(row)
            
        df = pd.DataFrame(data_rows)
        
        column_config = {"Alumno": st.column_config.TextColumn("Estudiante", disabled=True, width="medium"), "ID": None} # Ocultar ID
        for f in fechas_clase:
            column_config[f] = st.column_config.CheckboxColumn(f[5:], default=False) # Solo muestra mes-dia

        edited_df = st.data_editor(df, column_config=column_config, height=500, use_container_width=True, hide_index=True)

        if st.button("💾 GUARDAR ASISTENCIA", type="primary", use_container_width=True):
            conn = sqlite3.connect('piscina_arenas_final.db')
            c = conn.cursor()
            for idx, row in edited_df.iterrows():
                aid = row["ID"]
                for fecha in fechas_clase:
                    estado = "Presente" if row[fecha] else "Falta"
                    c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?, ?, ?, ?)", (aid, id_horario, fecha, estado))
            conn.commit()
            conn.close()
            st.success("✅ ¡Asistencia actualizada!")
            st.rerun()
    else:
        st.info("No hay alumnos matriculados en este horario.")

# ==========================================
# 2. MATRÍCULA (NUEVO vs RE-MATRÍCULA)
# ==========================================
elif selected == "Matrícula":
    st.header("📝 Gestión de Matrículas")
    
    # PESTAÑAS PARA NO MEZCLAR LÓGICA
    tab1, tab2 = st.tabs(["🆕 Nuevo Alumno (Primera vez)", "🔄 Re-matrícula (Alumno Antiguo)"])
    
    # --- PESTAÑA 1: NUEVO ---
    with tab1:
        with st.form("form_nuevo"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombres")
            a = c2.text_input("Apellidos")
            tel = c1.text_input("Teléfono")
            apo = c2.text_input("Apoderado")
            niv = c1.selectbox("Nivel", ["Básico", "Intermedio", "Avanzado"])
            dire = c2.text_input("Dirección")
            cond = st.text_area("Condición Especial (Opcional)", placeholder="Alergias, TDAH, etc.")
            
            st.markdown("### Seleccionar Horario")
            # Selectores de Ciclo y Horario
            ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
            if ciclos:
                cd = {name: id for id, name in ciclos}
                sel_c = st.selectbox("Ciclo", list(cd.keys()), key="c_new")
                sel_g = st.radio("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], key="g_new")
                
                hors = run_query("SELECT id, hora_inicio, capacidad FROM horarios WHERE ciclo_id=? AND grupo=?", (cd[sel_c], sel_g), return_data=True)
                opciones_h = {}
                for h in hors:
                    hid, ini, cap = h
                    cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                    lbl = f"{ini} ({cnt}/{cap} cupos)"
                    if cnt < cap: opciones_h[lbl] = hid
                    else: opciones_h[f"⛔ LLENO - {lbl}"] = None
                
                sel_h_txt = st.selectbox("Horario", list(opciones_h.keys()), key="h_new")
                
                if st.form_submit_button("Matricular Nuevo Alumno"):
                    hid_fin = opciones_h[sel_h_txt]
                    if hid_fin and n and a:
                        run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion) VALUES (?,?,?,?,?,?,?,?)", 
                                  (n, a, tel, dire, niv, apo, date.today(), cond))
                        aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                        run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (aid, hid_fin, date.today()))
                        st.success(f"Alumno {n} {a} inscrito correctamente.")
                    else:
                        st.error("Verifica los datos o cupos.")
            else:
                st.warning("Crea ciclos primero.")

    # --- PESTAÑA 2: RE-MATRÍCULA ---
    with tab2:
        st.info("Utiliza esta opción para matricular a un alumno que ya existe en otro ciclo o horario.")
        search = st.text_input("🔍 Buscar Alumno por Nombre/Apellido:")
        
        if search:
            res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{search}%' OR apellido LIKE '%{search}%'", return_data=True)
            if res:
                # Diccionario para elegir alumno
                alum_opts = {f"{r[1]} {r[2]} (Nivel: {r[3]})": r[0] for r in res}
                sel_alum_txt = st.selectbox("Seleccionar Alumno Encontrado:", list(alum_opts.keys()))
                id_alumno_existente = alum_opts[sel_alum_txt]
                
                st.divider()
                st.markdown("### Asignar Nuevo Ciclo/Horario")
                
                # Reutilizamos lógica de selección de horario
                if ciclos:
                    cd2 = {name: id for id, name in ciclos}
                    sel_c2 = st.selectbox("Nuevo Ciclo", list(cd2.keys()), key="c_old")
                    sel_g2 = st.radio("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], key="g_old")
                    
                    hors2 = run_query("SELECT id, hora_inicio, capacidad FROM horarios WHERE ciclo_id=? AND grupo=?", (cd2[sel_c2], sel_g2), return_data=True)
                    opciones_h2 = {}
                    for h in hors2:
                        hid, ini, cap = h
                        cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                        lbl = f"{ini} ({cnt}/{cap} cupos)"
                        if cnt < cap: opciones_h2[lbl] = hid
                        else: opciones_h2[f"⛔ LLENO - {lbl}"] = None
                    
                    sel_h_txt2 = st.selectbox("Nuevo Horario", list(opciones_h2.keys()), key="h_old")
                    
                    if st.button("Confirmar Re-matrícula"):
                        hid_fin2 = opciones_h2[sel_h_txt2]
                        if hid_fin2:
                            # Verificar si ya está en ese horario para no duplicar
                            existe = run_query("SELECT id FROM matriculas WHERE alumno_id=? AND horario_id=?", (id_alumno_existente, hid_fin2), return_data=True)
                            if not existe:
                                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (id_alumno_existente, hid_fin2, date.today()))
                                st.success("✅ ¡Re-matrícula exitosa! El alumno ahora está en el nuevo ciclo.")
                            else:
                                st.warning("El alumno ya está matriculado en este horario específico.")
                        else:
                            st.error("Horario lleno.")
            else:
                st.warning("No se encontraron alumnos.")

# ==========================================
# 3. CONFIGURACIÓN
# ==========================================
elif selected == "Configuración":
    st.header("⚙️ Configuración")
    
    tab1, tab2 = st.tabs(["1. Crear Ciclo", "2. Crear Horarios"])
    
    with tab1:
        nc = st.text_input("Nombre Ciclo (Ej: Verano 2026)")
        fi = st.date_input("Fecha Inicio Clases")
        if st.button("Guardar Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (nc, fi))
            st.success("Ciclo Creado")
            
    with tab2:
        ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos:
            cd = {n: i for i, n in ciclos}
            c_sel = st.selectbox("Ciclo destino", list(cd.keys()))
            
            c1, c2, c3 = st.columns(3)
            grp = c1.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            
            horas_std = ["07:00 - 08:00", "08:00 - 09:00", "09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00",
                         "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00"]
            hr = c2.selectbox("Hora", horas_std)
            cap = c3.number_input("Cupos", 10)
            
            if st.button("Agregar Horario"):
                run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, capacidad) VALUES (?,?,?,?)", (cd[c_sel], grp, hr, cap))
                st.success("Horario Agregado")

# ==========================================
# 4. REPORTES
# ==========================================
elif selected == "Reportes":
    st.header("Informe Estudiante")
    busqueda = st.text_input("Buscar Apellido:")
    if busqueda:
        res = run_query(f"SELECT id, nombre, apellido, condicion FROM alumnos WHERE apellido LIKE '%{busqueda}%'", return_data=True)
        if res:
            for r in res:
                aid, n, a, c = r
                st.markdown(f"**{n} {a}**")
                if c: st.error(f"Condición: {c}")
                
                # Mostrar todos los cursos donde ha estado matriculado
                mats = run_query("""
                    SELECT c.nombre, h.grupo, h.hora_inicio, m.horario_id
                    FROM matriculas m 
                    JOIN horarios h ON m.horario_id = h.id 
                    JOIN ciclos c ON h.ciclo_id = c.id
                    WHERE m.alumno_id = ?
                """, (aid,), return_data=True)
                
                for m in mats:
                    ciclo_nom, grup, hora, hid = m
                    asist = run_query("SELECT COUNT(*) FROM asistencia WHERE alumno_id=? AND horario_id=? AND estado='Presente'", (aid, hid), return_data=True)[0][0]
                    st.text(f"Ciclo: {ciclo_nom} | {grup} {hora} | Asistencias: {asist}/12")
                
                st.divider()

# ==========================================
# 5. RECUPERACIONES
# ==========================================
elif selected == "Recuperaciones":
    st.title("Agendar Recuperación")
    alum_all = run_query("SELECT id, nombre, apellido FROM alumnos", return_data=True)
    if alum_all:
        dic = {f"{n} {a}": i for i, n, a in alum_all}
        sel = st.selectbox("Alumno", list(dic.keys()))
        fecha = st.date_input("Fecha Recuperación")
        if st.button("Agendar"):
             run_query("INSERT INTO recuperaciones_programadas (alumno_id, fecha_destino) VALUES (?, ?)", (dic[sel], fecha))
             st.success("Agendado")
