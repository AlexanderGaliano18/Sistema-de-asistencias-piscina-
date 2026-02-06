import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Piscina Arenas - Gestión", layout="wide", page_icon="🏊")

# --- LISTA DE NIVELES ESTÁNDAR ---
NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]

# --- ESTILOS CSS ---
st.markdown("""
<style>
    div.row-widget.stRadio > div {
        flex-direction: row;
        align-items: stretch;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: #f0f2f6;
        padding: 10px 15px;
        margin-right: 10px;
        border-radius: 8px;
        border: 1px solid #dcdcdc;
        cursor: pointer;
        text-align: center;
        font-weight: bold;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-baseweb="radio"] {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
    }
    .stDataFrame { border: 1px solid #e6e6e6; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('piscina_arenas_v7_final.db') 
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS horarios (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 ciclo_id INTEGER, 
                 grupo TEXT, 
                 hora_inicio TEXT, 
                 capacidad INTEGER,
                 nivel_salon TEXT,
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS matriculas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_id INTEGER, 
                 fecha_inicio DATE,
                 FOREIGN KEY(alumno_id) REFERENCES alumnos(id),
                 FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_id INTEGER, 
                 fecha TEXT, 
                 estado TEXT, 
                 UNIQUE(alumno_id, horario_id, fecha))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS recuperaciones_programadas (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 horario_destino_id INTEGER, 
                 fecha_destino TEXT)''')
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('piscina_arenas_v7_final.db')
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
    if "Lunes" in grupo: dias_permitidos = [0, 2, 4] 
    else: dias_permitidos = [1, 3, 5] 
    while fecha_obj.weekday() not in dias_permitidos: fecha_obj += timedelta(days=1)
    while len(fechas) < 12:
        if fecha_obj.weekday() in dias_permitidos: fechas.append(fecha_obj.strftime("%Y-%m-%d"))
        fecha_obj += timedelta(days=1)
    return fechas

init_db()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=100)
    selected = option_menu(
        menu_title=None,
        options=["Asistencia", "Matrícula", "Promoción", "Configuración", "Reportes", "🔍 Diagnóstico"],
        icons=["calendar-check", "person-plus", "graph-up-arrow", "gear", "clipboard-data", "search"],
        default_index=0,
    )

# ==========================================
# 1. ASISTENCIA
# ==========================================
if selected == "Asistencia":
    st.title("📅 Toma de Asistencia")

    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos:
        st.warning("⚠️ Primero crea un ciclo en Configuración.")
        st.stop()

    c_dict = {n: (i, f) for i, n, f in ciclos}
    nombre_ciclo_sel = st.selectbox("Seleccionar Ciclo:", list(c_dict.keys()))
    id_ciclo, fecha_inicio_ciclo = c_dict[nombre_ciclo_sel]
    
    st.write("---")

    # SELECCIÓN ESTILO "ATTENDANCE FLOW"
    grupo_sel = st.radio("1. Días:", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], horizontal=True)
    
    horas_disp = run_query("SELECT DISTINCT hora_inicio FROM horarios WHERE ciclo_id=? AND grupo=? ORDER BY hora_inicio", 
                           (id_ciclo, grupo_sel), return_data=True)
    
    if not horas_disp:
        st.info("⚠️ No hay horarios para estos días.")
    else:
        lista_horas = [h[0] for h in horas_disp]
        hora_sel = st.radio("2. Hora:", lista_horas, horizontal=True)
        
        # BUSCAR SALONES EN ESA HORA
        niveles_disp = run_query("SELECT DISTINCT nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?",
                                 (id_ciclo, grupo_sel, hora_sel), return_data=True)
        
        if niveles_disp:
            lista_niveles = [n[0] for n in niveles_disp]
            st.write("3. Selecciona el Salón:")
            nivel_sel = st.selectbox("Salón (Nivel):", lista_niveles, label_visibility="collapsed")
            
            # --- TABLA ASISTENCIA ---
            fechas_clase = calcular_fechas_clase(fecha_inicio_ciclo, grupo_sel)
            
            alumnos = run_query("""
                SELECT a.id, a.nombre, a.apellido, a.condicion, m.horario_id 
                FROM alumnos a 
                JOIN matriculas m ON a.id = m.alumno_id 
                JOIN horarios h ON m.horario_id = h.id
                WHERE h.ciclo_id = ? AND h.grupo = ? AND h.hora_inicio = ? AND h.nivel_salon = ?
            """, (id_ciclo, grupo_sel, hora_sel, nivel_sel), return_data=True)
            
            if alumnos:
                ids_horarios = list(set([al[4] for al in alumnos]))
                placeholders = ','.join(['?']*len(ids_horarios))
                asist_data = run_query(f"SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id IN ({placeholders})", tuple(ids_horarios), return_data=True)
                asist_map = {(a, f): e for a, f, e in asist_data}
                
                data_rows = []
                for alum in alumnos:
                    aid, nom, ape, cond, hid_real = alum
                    nombre_mostrar = f"{nom} {ape}"
                    if cond and cond.strip(): nombre_mostrar = f"🔴 {nom} {ape} ({cond})"
                    
                    row = {"ID": aid, "HID": hid_real, "Alumno": nombre_mostrar}
                    for f in fechas_clase:
                        estado = asist_map.get((aid, f))
                        val = "✅" if estado == "Presente" else ("❌" if estado == "Falta" else ("🤧" if estado == "Justificado" else None))
                        row[f] = val
                    data_rows.append(row)
                    
                df = pd.DataFrame(data_rows)
                col_cfg = {"Alumno": st.column_config.TextColumn("Estudiante", disabled=True, width="medium"), "ID": None, "HID": None}
                for f in fechas_clase:
                    col_cfg[f] = st.column_config.SelectboxColumn(f[5:], options=["✅", "❌", "🤧"], width="small", required=False)
                
                st.success(f"Mostrando alumnos de: {nivel_sel}")
                edited_df = st.data_editor(df, column_config=col_cfg, height=400, use_container_width=True, hide_index=True)
                
                if st.button("💾 GUARDAR ASISTENCIA", type="primary", use_container_width=True):
                    conn = sqlite3.connect('piscina_arenas_v7_final.db')
                    c = conn.cursor()
                    for idx, row in edited_df.iterrows():
                        aid = row["ID"]
                        hid = row["HID"]
                        for f in fechas_clase:
                            val = row[f]
                            est_bd = "Presente" if val=="✅" else ("Falta" if val=="❌" else ("Justificado" if val=="🤧" else None))
                            if est_bd:
                                c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?, ?, ?, ?)", (aid, hid, f, est_bd))
                            elif val is None:
                                c.execute("DELETE FROM asistencia WHERE alumno_id=? AND horario_id=? AND fecha=?", (aid, hid, f))
                    conn.commit()
                    conn.close()
                    st.success("¡Guardado!")
                    st.rerun()
            else:
                st.info("⚠️ No se encontraron alumnos matriculados en este salón.")
        else:
            st.warning("No hay niveles configurados en esta hora.")

# ==========================================
# 2. MATRÍCULA (AHORA SÍ, IGUAL QUE ASISTENCIA)
# ==========================================
elif selected == "Matrícula":
    st.header("📝 Matrícula")
    tab1, tab2 = st.tabs(["🆕 Nuevo Alumno", "🔄 Re-matrícula"])
    
    with tab1:
        # PRIMERO LOS DATOS PERSONALES
        st.subheader("1. Datos del Alumno")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nombres")
        a = c2.text_input("Apellidos")
        tel = c1.text_input("Teléfono")
        apo = c2.text_input("Apoderado")
        dire = c1.text_input("Dirección")
        cond = st.text_area("Condición Especial (Opcional)", placeholder="Ej: TDAH...")
        
        st.divider()
        st.subheader("2. Selección de Horario y Nivel")
        
        # PASO 1: CICLO
        ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos:
            cd = {name: id for id, name in ciclos}
            sel_c = st.selectbox("Ciclo", list(cd.keys()))
            
            # PASO 2: DÍAS (Igual que asistencia)
            sel_g = st.radio("Días de Clase", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], horizontal=True)
            
            # PASO 3: HORA
            hors = run_query("SELECT DISTINCT hora_inicio FROM horarios WHERE ciclo_id=? AND grupo=? ORDER BY hora_inicio", 
                             (cd[sel_c], sel_g), return_data=True)
            
            if hors:
                lista_horas = [h[0] for h in hors]
                sel_h = st.radio("Hora", lista_horas, horizontal=True)
                
                # PASO 4: SALONES DISPONIBLES EN ESA HORA (Aquí estaba la falla antes)
                # Ahora mostramos TODOS los salones disponibles en esa hora, no filtramos por un nivel pre-seleccionado
                salones_query = run_query("""
                    SELECT id, nivel_salon, capacidad 
                    FROM horarios 
                    WHERE ciclo_id=? AND grupo=? AND hora_inicio=?
                """, (cd[sel_c], sel_g, sel_h), return_data=True)
                
                opciones_salon = {}
                if salones_query:
                    for s in salones_query:
                        hid, niv_s, cap = s
                        cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                        
                        label = f"{niv_s} (Cupos: {cnt}/{cap})"
                        if cnt < cap:
                            opciones_salon[label] = (hid, niv_s) # Guardamos ID y nombre del nivel
                        else:
                            opciones_salon[f"⛔ LLENO - {label}"] = None
                    
                    st.write("Selecciona el Salón:")
                    sel_salon_txt = st.selectbox("Aulas disponibles:", list(opciones_salon.keys()))
                    
                    # BOTÓN FINAL
                    if st.button("Matricular Alumno", type="primary"):
                        if sel_salon_txt and opciones_salon[sel_salon_txt]:
                            hid_final, nivel_asignado = opciones_salon[sel_salon_txt]
                            
                            if n and a:
                                # Guardamos el alumno CON EL NIVEL DEL SALÓN SELECCIONADO
                                run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion) VALUES (?,?,?,?,?,?,?,?)", 
                                          (n, a, tel, dire, nivel_asignado, apo, date.today(), cond))
                                aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (aid, hid_final, date.today()))
                                st.balloons()
                                st.success(f"✅ Alumno inscrito correctamente en {nivel_asignado}.")
                            else:
                                st.error("Falta llenar nombre o apellido.")
                        else:
                            st.error("El salón seleccionado está lleno o no es válido.")
                else:
                    st.warning("No hay salones creados para esta hora exacta.")
            else:
                st.warning("No hay horarios para estos días.")
        else:
            st.warning("Crea ciclos primero.")

    with tab2:
        st.subheader("Re-matrícula de Alumno Antiguo")
        search = st.text_input("Buscar Alumno:")
        if search:
            res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{search}%' OR apellido LIKE '%{search}%'", return_data=True)
            if res:
                opts = {f"{r[1]} {r[2]} (Nivel Actual: {r[3]})": (r[0], r[3]) for r in res}
                sel_txt = st.selectbox("Seleccionar:", list(opts.keys()))
                id_alum, nivel_actual = opts[sel_txt]
                
                if ciclos:
                    cd2 = {name: id for id, name in ciclos}
                    sc2 = st.selectbox("Ciclo Destino", list(cd2.keys()), key="rm_c")
                    sg2 = st.radio("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], horizontal=True, key="rm_g")
                    
                    h2 = run_query("SELECT DISTINCT hora_inicio FROM horarios WHERE ciclo_id=? AND grupo=? ORDER BY hora_inicio", 
                                   (cd2[sc2], sg2), return_data=True)
                    if h2:
                        lh2 = [h[0] for h in h2]
                        sh2 = st.radio("Hora", lh2, horizontal=True, key="rm_h")
                        
                        # Buscar salones
                        sal2 = run_query("SELECT id, nivel_salon, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                                         (cd2[sc2], sg2, sh2), return_data=True)
                        op2 = {}
                        for s in sal2:
                            hid, niv_s, cap = s
                            cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                            lbl = f"{niv_s} ({cnt}/{cap})"
                            if cnt < cap: op2[lbl] = hid
                            else: op2[f"⛔ LLENO - {lbl}"] = None
                        
                        sel_sal2 = st.selectbox("Salón:", list(op2.keys()), key="rm_sal")
                        
                        if st.button("Confirmar Re-matrícula"):
                            if sel_sal2 and op2[sel_sal2]:
                                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (id_alum, op2[sel_sal2], date.today()))
                                st.success("Re-matriculado.")

# ==========================================
# 3. PROMOCIÓN
# ==========================================
elif selected == "Promoción":
    st.header("🚀 Promover Nivel")
    busq = st.text_input("Buscar Alumno:")
    if busq:
        res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{busq}%' OR apellido LIKE '%{busq}%'", return_data=True)
        if res:
            dic_al = {f"{r[1]} {r[2]} (Actual: {r[3]})": r for r in res}
            sel_al = st.selectbox("Alumno:", list(dic_al.keys()))
            id_a, nom, ape, niv_viejo = dic_al[sel_al]
            
            idx_act = NIVELES.index(niv_viejo) if niv_viejo in NIVELES else 0
            idx_new = min(idx_act + 1, len(NIVELES) - 1)
            
            c1, c2 = st.columns(2)
            new_niv = c1.selectbox("Nuevo Nivel:", NIVELES, index=idx_new)
            
            if st.button("Guardar Cambio de Nivel"):
                run_query("UPDATE alumnos SET nivel = ? WHERE id = ?", (new_niv, id_a))
                st.success(f"Nivel actualizado a {new_niv}.")

# ==========================================
# 4. CONFIGURACIÓN
# ==========================================
elif selected == "Configuración":
    st.header("⚙️ Configuración")
    tab1, tab2 = st.tabs(["1. Ciclos", "2. Salones"])
    
    with tab1:
        nc = st.text_input("Nombre Ciclo (Ej: Marzo 2026)")
        fi = st.date_input("Inicio Clases")
        if st.button("Crear Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (nc, fi))
            st.success("Ciclo Creado.")
            
    with tab2:
        ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos:
            cd = {n: i for i, n in ciclos}
            c_sel = st.selectbox("Ciclo", list(cd.keys()))
            
            c1, c2, c3, c4 = st.columns(4)
            grp = c1.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            horas = ["07:00 - 08:00", "08:00 - 09:00", "09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00",
                     "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00"]
            hr = c2.selectbox("Hora", horas)
            ns = c3.selectbox("Nivel (Salón)", NIVELES)
            cap = c4.number_input("Cupos", 5)
            
            if st.button("Crear Salón"):
                run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, capacidad, nivel_salon) VALUES (?,?,?,?,?)", 
                          (cd[c_sel], grp, hr, cap, ns))
                st.success(f"Salón {ns} creado.")
            
            st.write("Salones creados:")
            df = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={cd[c_sel]} ORDER BY hora_inicio", sqlite3.connect('piscina_arenas_v7_final.db'))
            st.dataframe(df)

# ==========================================
# 5. REPORTES
# ==========================================
elif selected == "Reportes":
    st.header("Informe")
    b = st.text_input("Apellido:")
    if b:
        r = run_query(f"SELECT * FROM alumnos WHERE apellido LIKE '%{b}%'", return_data=True)
        for d in r:
            st.markdown(f"**{d[1]} {d[2]}** - Nivel: {d[5]}")
            if d[8]: st.error(f"Condición: {d[8]}")
            st.divider()

# ==========================================
# 6. DIAGNÓSTICO
# ==========================================
elif selected == "🔍 Diagnóstico":
    st.header("🔍 Diagnóstico")
    st.subheader("Últimos Matriculados")
    df_m = pd.read_sql_query("""
        SELECT a.nombre, a.apellido, a.nivel, h.grupo, h.hora_inicio, h.nivel_salon
        FROM matriculas m
        JOIN alumnos a ON m.alumno_id = a.id
        JOIN horarios h ON m.horario_id = h.id
        ORDER BY m.id DESC LIMIT 10
    """, sqlite3.connect('piscina_arenas_v7_final.db'))
    st.dataframe(df_m)
