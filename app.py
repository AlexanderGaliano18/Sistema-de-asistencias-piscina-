import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sistema Piscina - V13", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v13_final.db"

DIAS = ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"]
HORAS = ["07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", 
         "11:00-12:00", "12:00-13:00", "15:00-16:00", "16:00-17:00", 
         "17:00-18:00", "18:00-19:00"]
NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]

st.markdown("""
<style>
    div.stButton > button {width: 100%; font-weight: bold;}
    .success-msg {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px;}
    .info-box {padding: 15px; background-color: #e2e3e5; border-radius: 10px; margin-bottom: 10px;}
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
            if return_data: return c.fetchall()
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error BD: {e}")
            return False

def init_db():
    run_query('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    run_query('''CREATE TABLE IF NOT EXISTS horarios (id INTEGER PRIMARY KEY AUTOINCREMENT, ciclo_id INTEGER, grupo TEXT, hora_inicio TEXT, nivel_salon TEXT, capacidad INTEGER, FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    run_query('''CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, telefono TEXT, direccion TEXT, nivel TEXT, apoderado TEXT, condicion TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS matriculas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, horario_id INTEGER, fecha_registro DATE, FOREIGN KEY(alumno_id) REFERENCES alumnos(id), FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
    run_query('''CREATE TABLE IF NOT EXISTS asistencia (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, horario_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(alumno_id, horario_id, fecha))''')
    run_query('''CREATE TABLE IF NOT EXISTS recuperaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, fecha_origen TEXT, horario_destino_id INTEGER, fecha_destino TEXT, asistio BOOLEAN DEFAULT 0)''')

def generar_fechas_clase(fecha_inicio_str, grupo):
    fechas = []
    try:
        if isinstance(fecha_inicio_str, str): curr = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        else: curr = fecha_inicio_str
    except: curr = date.today()

    target = [0, 2, 4] if "Lunes" in grupo else [1, 3, 5]
    while curr.weekday() not in target: curr += timedelta(days=1)
    while len(fechas) < 12:
        if curr.weekday() in target: fechas.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return fechas

def guardar_alumno_y_matricula(nombre, apellido, tel, dire, nivel, apo, cond, horario_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("PRAGMA foreign_keys = ON;")
            c.execute("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, condicion) VALUES (?, ?, ?, ?, ?, ?, ?)", (nombre, apellido, tel, dire, nivel, apo, cond))
            alumno_id = c.lastrowid
            c.execute("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?, ?, ?)", (alumno_id, horario_id, date.today()))
            conn.commit()
            return True, alumno_id
    except Exception as e: return False, str(e)

init_db()

# ==========================================
# 2. INTERFAZ LATERAL
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=80)
    selected = option_menu(
        menu_title="Menú",
        options=["Configuración", "Matrícula", "👨‍🎓 Estudiantes", "Asistencia", "🔄 Recuperaciones"],
        icons=["gear", "person-plus", "people", "calendar-check", "arrow-repeat"],
        default_index=0,
    )

# ---------------------------------------------------------
# MÓDULO CONFIGURACIÓN
# ---------------------------------------------------------
if selected == "Configuración":
    st.title("⚙️ Configuración")
    t1, t2 = st.tabs(["1. Ciclos", "2. Salones"])
    with t1:
        cn = st.text_input("Nombre Ciclo (Ej: Marzo 2026)")
        ci = st.date_input("Inicio de Clases")
        if st.button("Guardar Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (cn, ci))
            st.success("Ciclo creado.")
    with t2:
        ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
        if ciclos:
            opts = {n: i for i, n in ciclos}
            sc = st.selectbox("Ciclo", list(opts.keys()))
            c1, c2, c3 = st.columns(3)
            d = c1.selectbox("Días", DIAS)
            h = c2.selectbox("Hora", HORAS)
            n = c3.selectbox("Nivel", NIVELES)
            cap = st.number_input("Cupos", 10)
            if st.button("Crear Salón"):
                res = run_query("SELECT id FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", (opts[sc], d, h, n), return_data=True)
                if not res:
                    run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, nivel_salon, capacidad) VALUES (?,?,?,?,?)", (opts[sc], d, h, n, cap))
                    st.success("Salón Creado.")
                else: st.error("Ya existe.")
            st.write("---")
            df = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts[sc]} ORDER BY hora_inicio", sqlite3.connect(DB_NAME))
            st.dataframe(df, hide_index=True)

# ---------------------------------------------------------
# MÓDULO MATRÍCULA (INCLUYE RE-MATRÍCULA)
# ---------------------------------------------------------
elif selected == "Matrícula":
    st.title("📝 Gestión de Matrículas")
    tab1, tab2 = st.tabs(["🆕 Nuevo Alumno", "🔄 Re-matrícula (Antiguos)"])
    
    # NUEVO ALUMNO
    with tab1:
        ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
        if not ciclos: st.warning("Crea un ciclo."); st.stop()
        dc = {n: i for i, n in ciclos}
        sc = st.selectbox("Ciclo:", list(dc.keys()), key="nc_c")
        c1, c2 = st.columns(2)
        sd = c1.radio("Días:", DIAS, key="nc_d")
        sh = c2.selectbox("Hora:", HORAS, key="nc_h")
        
        salones = run_query("SELECT id, nivel_salon, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (dc[sc], sd, sh), return_data=True)
        
        if salones:
            ops = {}
            for s in salones:
                hid, niv, cap = s
                oc = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                lbl = f"{niv} ({cap-oc}/{cap} libres)"
                if oc < cap: ops[lbl] = hid
                else: ops[f"⛔ LLENO - {lbl}"] = None
            
            stx = st.selectbox("Selecciona Salón:", list(ops.keys()), key="nc_s")
            hid_sel = ops[stx]
            
            if hid_sel:
                st.info(f"Salón Seleccionado ID: {hid_sel}")
                with st.form("fm_new"):
                    ca, cb = st.columns(2)
                    nm = ca.text_input("Nombre")
                    ap = cb.text_input("Apellido")
                    tl = ca.text_input("Teléfono")
                    pod = cb.text_input("Apoderado")
                    dr = st.text_input("Dirección")
                    cn = st.text_area("Condición")
                    if st.form_submit_button("Matricular"):
                        if nm and ap:
                            ok, res = guardar_alumno_y_matricula(nm, ap, tl, dr, "Registrado", pod, cn, hid_sel)
                            if ok: st.success(f"Matriculado. ID: {res}")
                            else: st.error(res)
                        else: st.error("Faltan datos.")
        else: st.warning("No hay salones en este horario.")

    # RE-MATRÍCULA
    with tab2:
        st.info("Usa esto para alumnos que ya existen en el sistema.")
        busq = st.text_input("Buscar Alumno por Nombre:")
        if busq:
            res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{busq}%' OR apellido LIKE '%{busq}%'", return_data=True)
            if res:
                dic_al = {f"{r[1]} {r[2]} (Nivel: {r[3]})": r[0] for r in res}
                sel_al = st.selectbox("Seleccionar Alumno:", list(dic_al.keys()))
                id_alum = dic_al[sel_al]
                
                st.write("---")
                st.write("**Seleccionar Nuevo Horario:**")
                # Reutilizamos lógica de selección
                dc2 = {n: i for i, n in ciclos}
                sc2 = st.selectbox("Nuevo Ciclo:", list(dc2.keys()), key="rm_c")
                c1, c2 = st.columns(2)
                sd2 = c1.radio("Días:", DIAS, key="rm_d")
                sh2 = c2.selectbox("Hora:", HORAS, key="rm_h")
                
                salones2 = run_query("SELECT id, nivel_salon, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (dc2[sc2], sd2, sh2), return_data=True)
                if salones2:
                    ops2 = {}
                    for s in salones2:
                        hid, niv, cap = s
                        oc = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                        lbl = f"{niv} ({cap-oc}/{cap} libres)"
                        if oc < cap: ops2[lbl] = hid
                        else: ops2[f"⛔ LLENO - {lbl}"] = None
                    
                    stx2 = st.selectbox("Salón Destino:", list(ops2.keys()), key="rm_s")
                    if st.button("Confirmar Re-matrícula"):
                        if ops2[stx2]:
                            run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?, ?, ?)", (id_alum, ops2[stx2], date.today()))
                            st.balloons()
                            st.success("Re-matriculado exitosamente.")
                else: st.warning("No hay salones disponibles.")

# ---------------------------------------------------------
# MÓDULO ESTUDIANTES (EDICIÓN Y CONTACTO)
# ---------------------------------------------------------
elif selected == "👨‍🎓 Estudiantes":
    st.title("👨‍🎓 Directorio de Estudiantes")
    st.markdown("Busca alumnos para ver su información de contacto o editar sus datos.")
    
    search = st.text_input("🔍 Buscar por Nombre o Apellido:")
    
    if search:
        alumnos = run_query(f"SELECT * FROM alumnos WHERE nombre LIKE '%{search}%' OR apellido LIKE '%{search}%'", return_data=True)
        
        if alumnos:
            for alum in alumnos:
                # alum: id, nombre, apellido, tel, dir, nivel, apo, cond
                aid, nom, ape, tel, dire, niv, apo, cond = alum
                
                with st.expander(f"👤 {nom} {ape} (Apoderado: {apo})"):
                    # Modo visualización
                    c1, c2 = st.columns(2)
                    c1.markdown(f"📞 **Teléfono:** {tel}")
                    c2.markdown(f"🏠 **Dirección:** {dire}")
                    if cond: st.error(f"⚠️ Condición: {cond}")
                    
                    # Modo Edición
                    st.write("---")
                    st.caption("✏️ Editar Datos")
                    with st.form(f"edit_{aid}"):
                        new_tel = st.text_input("Teléfono", value=tel)
                        new_apo = st.text_input("Apoderado", value=apo)
                        new_dir = st.text_input("Dirección", value=dire)
                        new_cond = st.text_area("Condición", value=cond)
                        
                        if st.form_submit_button("Guardar Cambios"):
                            run_query("UPDATE alumnos SET telefono=?, apoderado=?, direccion=?, condicion=? WHERE id=?", 
                                      (new_tel, new_apo, new_dir, new_cond, aid))
                            st.success("Datos actualizados. Recarga para ver cambios.")
                            st.rerun()
        else:
            st.info("No se encontraron alumnos.")
    else:
        # Mostrar los ultimos 5 registrados
        st.caption("Últimos alumnos registrados:")
        recent = run_query("SELECT nombre, apellido, nivel FROM alumnos ORDER BY id DESC LIMIT 5", return_data=True)
        df = pd.DataFrame(recent, columns=["Nombre", "Apellido", "Nivel"])
        st.table(df)

# ---------------------------------------------------------
# MÓDULO ASISTENCIA
# ---------------------------------------------------------
elif selected == "Asistencia":
    st.title("📅 Toma de Asistencia")
    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
    if not ciclos: st.stop()
    dc = {n: (i, f) for i, n, f in ciclos}
    sc = st.selectbox("Ciclo:", list(dc.keys()))
    cid, cfecha = dc[sc]
    
    c1, c2, c3 = st.columns(3)
    sd = c1.selectbox("Día", DIAS)
    sh = c2.selectbox("Hora", HORAS)
    ns = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (cid, sd, sh), return_data=True)
    
    if ns:
        dn = {n: i for i, n in ns}
        sn = c3.selectbox("Salón:", list(dn.keys()))
        hid = dn[sn]
        
        st.divider()
        
        # TABLA PRINCIPAL
        al_reg = run_query("SELECT a.id, a.nombre, a.apellido, a.condicion FROM alumnos a JOIN matriculas m ON a.id = m.alumno_id WHERE m.horario_id = ?", (hid,), return_data=True)
        fechas = generar_fechas_clase(cfecha, sd)
        
        if al_reg:
            asist = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (hid,), return_data=True)
            mapa = {(r[0], r[1]): r[2] for r in asist}
            data = []
            for al in al_reg:
                row = {"ID": al[0], "Alumno": f"{al[1]} {al[2]}" + (" 🔴" if al[3] else "")}
                for f in fechas:
                    est = mapa.get((al[0], f))
                    row[f] = "✅" if est == "Presente" else ("❌" if est == "Falta" else ("🤧" if est == "Justificado" else None))
                data.append(row)
            
            df = pd.DataFrame(data)
            cfg = {"ID": None, "Alumno": st.column_config.TextColumn(disabled=True, width="medium")}
            for f in fechas: cfg[f] = st.column_config.SelectboxColumn(f[5:], options=["✅", "❌", "🤧"], width="small", required=False)
            
            st.info("Leyenda: ✅ Presente | ❌ Falta | 🤧 Justificado (Pasa a lista de recuperación)")
            edited = st.data_editor(df, column_config=cfg, hide_index=True)
            
            if st.button("Guardar Asistencia"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for i, r in edited.iterrows():
                    for f in fechas:
                        val = r[f]
                        est = "Presente" if val=="✅" else ("Falta" if val=="❌" else ("Justificado" if val=="🤧" else None))
                        if est: c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?,?,?,?)", (r["ID"], hid, f, est))
                        elif val is None: c.execute("DELETE FROM asistencia WHERE alumno_id=? AND horario_id=? AND fecha=?", (r["ID"], hid, f))
                conn.commit()
                conn.close()
                st.success("Guardado.")
        else: st.warning("Salón vacío.")
        
        # --- VISITANTES / RECUPERACIONES ---
        st.write("---")
        st.subheader("🗓️ Alumnos Recuperando Hoy")
        # Busca alumnos que tengan programada una recuperacion en este salon (hid) y la fecha de destino coincida con alguna de las fechas del ciclo o sean futuras
        visitantes = run_query("""
            SELECT r.fecha_destino, a.nombre, a.apellido, r.fecha_origen
            FROM recuperaciones r
            JOIN alumnos a ON r.alumno_id = a.id
            WHERE r.horario_destino_id = ?
            ORDER BY r.fecha_destino
        """, (hid,), return_data=True)
        
        if visitantes:
            st.table(pd.DataFrame(visitantes, columns=["Fecha Recuperación", "Nombre", "Apellido", "Faltó el día"]))
        else:
            st.caption("No hay recuperaciones programadas para este salón.")

# ---------------------------------------------------------
# MÓDULO RECUPERACIONES
# ---------------------------------------------------------
elif selected == "🔄 Recuperaciones":
    st.title("Gestión de Justificaciones y Recuperaciones")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("1. Pendientes de Programar")
        # Busca Justificados que NO estan en tabla recuperaciones
        pendientes = run_query("""
            SELECT asis.alumno_id, a.nombre, a.apellido, asis.fecha, h.hora_inicio, a.nivel
            FROM asistencia asis
            JOIN alumnos a ON asis.alumno_id = a.id
            JOIN horarios h ON asis.horario_id = h.id
            WHERE asis.estado = 'Justificado'
            AND NOT EXISTS (SELECT 1 FROM recuperaciones r WHERE r.alumno_id = asis.alumno_id AND r.fecha_origen = asis.fecha)
        """, return_data=True)
        
        if pendientes:
            for p in pendientes:
                aid, nom, ape, f_falta, hora, niv = p
                with st.expander(f"🤧 {nom} {ape} ({f_falta})"):
                    st.write(f"Nivel: {niv} | Hora Habitual: {hora}")
                    with st.form(f"rec_{aid}_{f_falta}"):
                        f_new = st.date_input("Fecha Recuperación", min_value=date.today())
                        # Buscar salones compatibles
                        h_dest = run_query(f"SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id WHERE h.nivel_salon = '{niv}'", return_data=True)
                        if not h_dest: h_dest = run_query("SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id", return_data=True)
                        
                        op_h = {f"{h[4]} {h[1]} {h[2]}": h[0] for h in h_dest}
                        sel_hd = st.selectbox("Salón Destino", list(op_h.keys()))
                        
                        if st.form_submit_button("Agendar"):
                            run_query("INSERT INTO recuperaciones (alumno_id, fecha_origen, horario_destino_id, fecha_destino) VALUES (?,?,?,?)", (aid, f_falta, op_h[sel_hd], str(f_new)))
                            st.success("Agendado.")
                            st.rerun()
        else:
            st.success("No hay justificaciones pendientes.")

    with col_b:
        st.subheader("2. Calendario de Recuperaciones")
        recups = run_query("""
            SELECT r.fecha_destino, a.nombre, a.apellido, h.hora_inicio, h.nivel_salon
            FROM recuperaciones r
            JOIN alumnos a ON r.alumno_id = a.id
            JOIN horarios h ON r.horario_destino_id = h.id
            WHERE r.fecha_destino >= ?
            ORDER BY r.fecha_destino
        """, (date.today(),), return_data=True)
        
        if recups:
            df_rec = pd.DataFrame(recups, columns=["Fecha", "Alumno", "Apellido", "Hora", "Salón"])
            st.dataframe(df_rec, hide_index=True)
        else:
            st.info("No hay recuperaciones próximas.")
