import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN GENERAL
# ==========================================
st.set_page_config(page_title="Piscina Arenas - V14", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v14_gestion.db"

# Listas de referencia
DIAS = ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"]
HORAS = ["07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", 
         "11:00-12:00", "12:00-13:00", "15:00-16:00", "16:00-17:00", 
         "17:00-18:00", "18:00-19:00"]
NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]

# Estilos CSS
st.markdown("""
<style>
    div.stButton > button {width: 100%; font-weight: bold;}
    .success-box {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom:10px;}
    .warning-box {padding: 10px; background-color: #fff3cd; color: #856404; border-radius: 5px; margin-bottom:10px;}
    .error-box {padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom:10px;}
    .recup-box {border: 2px solid #28a745; padding: 10px; border-radius: 5px; margin-top: 20px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. GESTIÓN DE BASE DE DATOS
# ==========================================
def run_query(query, params=(), return_data=False):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON;") # Activar llaves foráneas
        try:
            c.execute(query, params)
            if return_data: return c.fetchall()
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error BD: {e}")
            return False

def init_db():
    # Tablas Base
    run_query('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    run_query('''CREATE TABLE IF NOT EXISTS horarios (id INTEGER PRIMARY KEY AUTOINCREMENT, ciclo_id INTEGER, grupo TEXT, hora_inicio TEXT, nivel_salon TEXT, capacidad INTEGER, FOREIGN KEY(ciclo_id) REFERENCES ciclos(id))''')
    run_query('''CREATE TABLE IF NOT EXISTS alumnos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, telefono TEXT, direccion TEXT, nivel TEXT, apoderado TEXT, condicion TEXT)''')
    run_query('''CREATE TABLE IF NOT EXISTS matriculas (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, horario_id INTEGER, fecha_registro DATE, FOREIGN KEY(alumno_id) REFERENCES alumnos(id), FOREIGN KEY(horario_id) REFERENCES horarios(id))''')
    run_query('''CREATE TABLE IF NOT EXISTS asistencia (id INTEGER PRIMARY KEY AUTOINCREMENT, alumno_id INTEGER, horario_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(alumno_id, horario_id, fecha))''')
    
    # Tabla Recuperaciones (Visitantes)
    run_query('''CREATE TABLE IF NOT EXISTS recuperaciones (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 fecha_origen TEXT, 
                 horario_destino_id INTEGER, 
                 fecha_destino TEXT, 
                 asistio BOOLEAN DEFAULT 0)''')
                 
    # NUEVA TABLA: INCIDENTES
    run_query('''CREATE TABLE IF NOT EXISTS incidentes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 fecha DATE, 
                 detalle TEXT, 
                 gravedad TEXT)''')

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

# Función segura para borrar alumno y todo su rastro
def eliminar_alumno_total(aid):
    run_query("DELETE FROM asistencia WHERE alumno_id=?", (aid,))
    run_query("DELETE FROM matriculas WHERE alumno_id=?", (aid,))
    run_query("DELETE FROM recuperaciones WHERE alumno_id=?", (aid,))
    run_query("DELETE FROM incidentes WHERE alumno_id=?", (aid,))
    run_query("DELETE FROM alumnos WHERE id=?", (aid,))
    return True

init_db()

# ==========================================
# 2. MENÚ PRINCIPAL
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=80)
    selected = option_menu(
        menu_title="Menú",
        options=["Configuración", "Matrícula", "👨‍🎓 Estudiantes", "Asistencia", "🔄 Recuperaciones", "⛑️ Incidentes"],
        icons=["gear", "person-plus", "people", "calendar-check", "arrow-repeat", "bandaid"],
        default_index=0,
    )

# ---------------------------------------------------------
# MÓDULO 1: CONFIGURACIÓN
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
            # Opción para borrar salones vacíos
            st.subheader("Listado de Salones")
            salones_df = run_query(f"SELECT id, grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts[sc]} ORDER BY hora_inicio", return_data=True)
            if salones_df:
                for s in salones_df:
                    sid, sgr, sho, sni, sca = s
                    c_del1, c_del2 = st.columns([4, 1])
                    c_del1.text(f"{sgr} | {sho} | {sni}")
                    if c_del2.button("🗑️", key=f"del_sal_{sid}"):
                        # Verificar si tiene matriculas
                        cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (sid,), return_data=True)[0][0]
                        if cnt == 0:
                            run_query("DELETE FROM horarios WHERE id=?", (sid,))
                            st.rerun()
                        else:
                            st.error("No puedes borrar: tiene alumnos.")
        else: st.warning("Crea un ciclo primero.")

# ---------------------------------------------------------
# MÓDULO 2: MATRÍCULA
# ---------------------------------------------------------
elif selected == "Matrícula":
    st.title("📝 Matrícula")
    tab1, tab2 = st.tabs(["🆕 Nuevo Alumno", "🔄 Re-matrícula"])
    
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
                st.success(f"Salón ID: {hid_sel}")
                with st.form("fm_new"):
                    ca, cb = st.columns(2)
                    nm = ca.text_input("Nombre")
                    ap = cb.text_input("Apellido")
                    tl = ca.text_input("Teléfono")
                    pod = cb.text_input("Apoderado")
                    dr = st.text_input("Dirección")
                    cn = st.text_area("Condición Médica/Especial")
                    if st.form_submit_button("Matricular"):
                        if nm and ap:
                            run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, condicion) VALUES (?, ?, ?, ?, ?, ?, ?)", (nm, ap, tl, dr, "Registrado", pod, cn))
                            aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                            run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?, ?, ?)", (aid, hid_sel, date.today()))
                            st.balloons()
                            st.success(f"Matriculado. ID: {aid}")
                        else: st.error("Faltan datos.")
        else: st.warning("No hay salones.")

    with tab2:
        st.info("Re-inscribir alumno antiguo en nuevo ciclo.")
        busq = st.text_input("Buscar Alumno:")
        if busq:
            res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{busq}%' OR apellido LIKE '%{busq}%'", return_data=True)
            if res:
                dic_al = {f"{r[1]} {r[2]} ({r[3]})": r[0] for r in res}
                sel_al = st.selectbox("Alumno:", list(dic_al.keys()))
                id_alum = dic_al[sel_al]
                
                # Selector simplificado
                dc2 = {n: i for i, n in ciclos}
                sc2 = st.selectbox("Ciclo Destino:", list(dc2.keys()), key="rm_c")
                c1, c2 = st.columns(2)
                sd2 = c1.radio("Días:", DIAS, key="rm_d")
                sh2 = c2.selectbox("Hora:", HORAS, key="rm_h")
                
                salones2 = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (dc2[sc2], sd2, sh2), return_data=True)
                if salones2:
                    ops2 = {f"{s[1]}": s[0] for s in salones2}
                    stx2 = st.selectbox("Salón:", list(ops2.keys()), key="rm_s")
                    if st.button("Confirmar Re-matrícula"):
                        run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_registro) VALUES (?, ?, ?)", (id_alum, ops2[stx2], date.today()))
                        st.success("Re-matriculado.")
                else: st.warning("No hay salón.")

# ---------------------------------------------------------
# MÓDULO 3: ESTUDIANTES (FICHA COMPLETA + BORRAR)
# ---------------------------------------------------------
elif selected == "👨‍🎓 Estudiantes":
    st.title("👨‍🎓 Gestión de Estudiantes")
    st.markdown("Busca para ver ficha completa, editar o eliminar.")
    
    search = st.text_input("🔍 Nombre o Apellido:")
    if search:
        alumnos = run_query(f"SELECT * FROM alumnos WHERE nombre LIKE '%{search}%' OR apellido LIKE '%{search}%'", return_data=True)
        if alumnos:
            for alum in alumnos:
                aid, nom, ape, tel, dire, niv, apo, cond = alum
                
                # TARJETA DEL ESTUDIANTE
                with st.expander(f"👤 {nom} {ape} | {niv}", expanded=True):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"**📞 Teléfono:** {tel}")
                        st.markdown(f"**🏠 Dirección:** {dire}")
                    with col_info2:
                        st.markdown(f"**🛡️ Apoderado:** {apo}")
                        if cond: st.error(f"⚠️ **CONDICIÓN:** {cond}")
                        else: st.success("Salud: Sin condiciones reportadas")

                    st.write("---")
                    
                    # PESTAÑAS DENTRO DE LA TARJETA
                    tb_edit, tb_del = st.tabs(["✏️ Editar Datos", "🗑️ Eliminar"])
                    
                    with tb_edit:
                        with st.form(f"ed_{aid}"):
                            nt = st.text_input("Teléfono", value=tel)
                            nd = st.text_input("Dirección", value=dire)
                            na = st.text_input("Apoderado", value=apo)
                            nc = st.text_area("Condición", value=cond)
                            if st.form_submit_button("Guardar Cambios"):
                                run_query("UPDATE alumnos SET telefono=?, direccion=?, apoderado=?, condicion=? WHERE id=?", (nt, nd, na, nc, aid))
                                st.success("Actualizado.")
                                st.rerun()

                    with tb_del:
                        st.markdown("""
                        <div class="error-box">
                        <b>ZONA DE PELIGRO:</b> Esto borrará al alumno, sus asistencias y matrículas. No se puede deshacer.
                        </div>
                        """, unsafe_allow_html=True)
                        clave = st.text_input("Escribe 'borrar' para confirmar:", key=f"pass_{aid}")
                        if st.button("CONFIRMAR ELIMINACIÓN", key=f"btn_del_{aid}"):
                            if clave == "borrar":
                                eliminar_alumno_total(aid)
                                st.success("Alumno eliminado.")
                                st.rerun()
                            else:
                                st.error("Palabra clave incorrecta.")
        else: st.info("No encontrado.")

# ---------------------------------------------------------
# MÓDULO 4: ASISTENCIA (CORREGIDO VISITANTES)
# ---------------------------------------------------------
elif selected == "Asistencia":
    st.title("📅 Asistencia y Visitantes")
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
        
        # 1. TABLA REGULARES
        st.subheader("📋 Alumnos Matriculados")
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
            
            edited = st.data_editor(df, column_config=cfg, hide_index=True)
            
            if st.button("Guardar Asistencia Regulares"):
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
        else: st.warning("Salón sin alumnos matriculados.")
        
        # 2. SECCIÓN VISITANTES (RECUPERACIONES) - CORREGIDO
        st.markdown("""<div class="recup-box">""", unsafe_allow_html=True)
        st.subheader("🟢 Alumnos Visitantes (Recuperación)")
        st.markdown("Alumnos de otros horarios que vienen a recuperar clase HOY o en estas fechas.")
        
        # Busca recuperaciones asignadas a ESTE horario (hid)
        visitantes = run_query("""
            SELECT r.id, r.fecha_destino, a.nombre, a.apellido, r.asistio
            FROM recuperaciones r
            JOIN alumnos a ON r.alumno_id = a.id
            WHERE r.horario_destino_id = ?
            ORDER BY r.fecha_destino
        """, (hid,), return_data=True)
        
        if visitantes:
            # Mostramos una tabla simple para marcar su asistencia
            vis_data = []
            for v in visitantes:
                rid, f_dest, nom, ape, asistio = v
                vis_data.append({
                    "RID": rid,
                    "Fecha": f_dest,
                    "Alumno": f"{nom} {ape}",
                    "Asistió": True if asistio else False
                })
            
            df_vis = pd.DataFrame(vis_data)
            edited_vis = st.data_editor(df_vis, column_config={
                "RID": None,
                "Asistió": st.column_config.CheckboxColumn("¿Vino?", default=False)
            }, hide_index=True, key="editor_visitantes")
            
            if st.button("Confirmar Asistencia Visitantes"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for i, r in edited_vis.iterrows():
                    # Actualizar tabla recuperaciones
                    c.execute("UPDATE recuperaciones SET asistio=? WHERE id=?", (1 if r["Asistió"] else 0, r["RID"]))
                conn.commit()
                conn.close()
                st.success("Visitantes actualizados.")
        else:
            st.info("No hay alumnos recuperando clase en este salón.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# MÓDULO 5: RECUPERACIONES
# ---------------------------------------------------------
elif selected == "🔄 Recuperaciones":
    st.title("Gestión de Justificaciones")
    
    # Pendientes
    st.subheader("1. Faltas Justificadas (Pendientes de Agendar)")
    pendientes = run_query("""
        SELECT asis.alumno_id, a.nombre, a.apellido, asis.fecha, h.grupo, a.nivel
        FROM asistencia asis
        JOIN alumnos a ON asis.alumno_id = a.id
        JOIN horarios h ON asis.horario_id = h.id
        WHERE asis.estado = 'Justificado'
        AND NOT EXISTS (SELECT 1 FROM recuperaciones r WHERE r.alumno_id = asis.alumno_id AND r.fecha_origen = asis.fecha)
    """, return_data=True)
    
    if pendientes:
        for p in pendientes:
            aid, nom, ape, f_falta, grup, niv = p
            with st.form(f"rec_{aid}_{f_falta}"):
                st.markdown(f"**{nom} {ape}** faltó el {f_falta} ({grup})")
                f_new = st.date_input("Fecha Recuperación", min_value=date.today())
                
                # Buscar salones compatibles
                h_dest = run_query(f"SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id WHERE h.nivel_salon = '{niv}'", return_data=True)
                if not h_dest: h_dest = run_query("SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id", return_data=True)
                
                op_h = {f"{h[4]} | {h[1]} {h[2]} ({h[3]})": h[0] for h in h_dest}
                sel_hd = st.selectbox("Salón Destino", list(op_h.keys()))
                
                if st.form_submit_button("Agendar"):
                    run_query("INSERT INTO recuperaciones (alumno_id, fecha_origen, horario_destino_id, fecha_destino) VALUES (?,?,?,?)", (aid, f_falta, op_h[sel_hd], str(f_new)))
                    st.success("Agendado.")
                    st.rerun()
    else: st.success("No hay pendientes.")

    # Lista
    st.write("---")
    st.subheader("2. Calendario de Recuperaciones")
    hist = run_query("""
        SELECT r.fecha_destino, a.nombre, a.apellido, h.hora_inicio, h.nivel_salon, r.asistio
        FROM recuperaciones r
        JOIN alumnos a ON r.alumno_id = a.id
        JOIN horarios h ON r.horario_destino_id = h.id
        ORDER BY r.fecha_destino
    """, return_data=True)
    if hist:
        dfh = pd.DataFrame(hist, columns=["Fecha", "Alumno", "Apellido", "Hora", "Salón", "Asistió"])
        dfh["Asistió"] = dfh["Asistió"].apply(lambda x: "Sí" if x else "Pendiente/No")
        st.dataframe(dfh)

# ---------------------------------------------------------
# MÓDULO 6: INCIDENTES (NUEVO)
# ---------------------------------------------------------
elif selected == "⛑️ Incidentes":
    st.title("⛑️ Reporte de Incidentes")
    st.markdown("Registro de accidentes, caídas o situaciones de emergencia.")
    
    col_form, col_hist = st.columns([1, 2])
    
    with col_form:
        st.subheader("Nuevo Reporte")
        with st.form("form_incidente"):
            # Buscar alumno
            nm_inc = st.text_input("Buscar Alumno (Nombre):")
            alum_sel_id = None
            if nm_inc:
                res = run_query(f"SELECT id, nombre, apellido FROM alumnos WHERE nombre LIKE '%{nm_inc}%'", return_data=True)
                if res:
                    dic_inc = {f"{r[1]} {r[2]}": r[0] for r in res}
                    sel_nm = st.selectbox("Seleccionar:", list(dic_inc.keys()))
                    alum_sel_id = dic_inc[sel_nm]
            
            f_inc = st.date_input("Fecha del Incidente")
            det_inc = st.text_area("Detalles del suceso", placeholder="Ej: El alumno resbaló al borde de la piscina...")
            grav = st.selectbox("Gravedad", ["Leve", "Moderada", "Grave (Hospital)", "Crítica"])
            
            if st.form_submit_button("Registrar Incidente"):
                if alum_sel_id and det_inc:
                    run_query("INSERT INTO incidentes (alumno_id, fecha, detalle, gravedad) VALUES (?,?,?,?)", (alum_sel_id, f_inc, det_inc, grav))
                    st.error("Incidente Registrado.")
                else:
                    st.warning("Busca un alumno y escribe detalles.")

    with col_hist:
        st.subheader("Historial de Incidentes")
        data_inc = run_query("""
            SELECT i.fecha, a.nombre, a.apellido, i.gravedad, i.detalle 
            FROM incidentes i JOIN alumnos a ON i.alumno_id = a.id 
            ORDER BY i.id DESC
        """, return_data=True)
        if data_inc:
            for row in data_inc:
                f, n, a, g, d = row
                color = "orange" if g == "Moderada" else ("red" if "Grave" in g else "green")
                st.markdown(f"""
                <div style="border-left: 5px solid {color}; padding: 10px; background: #f9f9f9; margin-bottom: 10px;">
                    <b>{f} | {n} {a}</b> <span style="color:{color}">({g})</span><br>
                    {d}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sin incidentes reportados.")
