import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from streamlit_option_menu import option_menu

# ==========================================
# 0. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Sistema Piscina - V12 Pro", layout="wide", page_icon="🏊")
DB_NAME = "piscina_v12_pro.db"

DIAS = ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"]
HORAS = ["07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", 
         "11:00-12:00", "12:00-13:00", "15:00-16:00", "16:00-17:00", 
         "17:00-18:00", "18:00-19:00"]
NIVELES = ["Básico 0", "Básico 1", "Básico 2", "Intermedio", "Avanzado"]

st.markdown("""
<style>
    div.stButton > button {width: 100%; font-weight: bold;}
    .success-msg {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px;}
    .warning-msg {padding: 10px; background-color: #fff3cd; color: #856404; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. BASE DE DATOS Y LÓGICA
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
    
    # TABLA NUEVA PARA RECUPERACIONES
    # Vincula al alumno con un horario de destino específico y una fecha específica
    run_query('''CREATE TABLE IF NOT EXISTS recuperaciones (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 alumno_id INTEGER, 
                 fecha_origen TEXT,     -- Fecha que faltó
                 horario_destino_id INTEGER, -- Salón donde pagará la clase
                 fecha_destino TEXT,    -- Día que irá
                 asistio BOOLEAN DEFAULT 0)''')

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
    except Exception as e:
        return False, str(e)

# --- LÓGICA DE FECHAS CORREGIDA ---
def generar_fechas_clase(fecha_inicio_str, grupo):
    """Genera 12 fechas saltando los días que no tocan."""
    fechas = []
    try:
        # Asegurarnos de que sea objeto date
        if isinstance(fecha_inicio_str, str):
            curr = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        else:
            curr = fecha_inicio_str
    except:
        curr = date.today()

    # Definir días objetivo (0=Lunes, 1=Martes...)
    if "Lunes" in grupo: 
        target = [0, 2, 4] # L-M-V
    else: 
        target = [1, 3, 5] # M-J-S
    
    # Avanzar hasta encontrar el primer día válido
    while curr.weekday() not in target:
        curr += timedelta(days=1)
        
    # Generar las 12 clases
    while len(fechas) < 12:
        if curr.weekday() in target:
            fechas.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
        
    return fechas

init_db()

# ==========================================
# 2. INTERFAZ
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2972/2972199.png", width=80)
    selected = option_menu(
        menu_title="Menú",
        options=["Configuración", "Matrícula", "Asistencia", "🔄 Recuperaciones", "Base de Datos"],
        icons=["gear", "person-plus", "calendar-check", "arrow-repeat", "database"],
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
        st.info("Crea los salones (Horarios con Nivel)")
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
            
            # Ver tabla
            st.write("---")
            df = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={opts[sc]} ORDER BY hora_inicio", sqlite3.connect(DB_NAME))
            st.dataframe(df, hide_index=True)

# ---------------------------------------------------------
# MÓDULO MATRÍCULA
# ---------------------------------------------------------
elif selected == "Matrícula":
    st.title("📝 Matrícula")
    
    ciclos = run_query("SELECT id, nombre FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos: 
        st.warning("Crea un ciclo primero.")
        st.stop()
        
    dc = {n: i for i, n in ciclos}
    sc = st.selectbox("Ciclo:", list(dc.keys()))
    
    c1, c2 = st.columns(2)
    sd = c1.radio("Días:", DIAS)
    sh = c2.selectbox("Hora:", HORAS)
    
    # BUSCAR SALONES
    salones = run_query("SELECT id, nivel_salon, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (dc[sc], sd, sh), return_data=True)
    
    hid_sel = None
    if not salones:
        st.error("No hay salones en este horario.")
    else:
        ops = {}
        for s in salones:
            hid, niv, cap = s
            oc = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
            lbl = f"{niv} ({cap-oc}/{cap} libres)"
            if oc < cap: ops[lbl] = hid
            else: ops[f"⛔ LLENO - {lbl}"] = None
        
        stx = st.selectbox("Selecciona Salón:", list(ops.keys()))
        hid_sel = ops[stx]
        
        if hid_sel:
            st.info(f"Salón ID: {hid_sel} seleccionado.")
            st.markdown("### Datos del Alumno")
            with st.form("fm"):
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
                        if ok: st.success(f"Alumno matriculado. ID: {res}")
                        else: st.error(res)
                    else: st.error("Faltan datos.")

# ---------------------------------------------------------
# MÓDULO ASISTENCIA (CON VISUALIZACIÓN DE RECUPERACIONES)
# ---------------------------------------------------------
elif selected == "Asistencia":
    st.title("📅 Asistencia")
    
    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos", return_data=True)
    if not ciclos: st.stop()
    
    dc = {n: (i, f) for i, n, f in ciclos}
    sc = st.selectbox("Ciclo:", list(dc.keys()))
    cid, cfecha = dc[sc]
    
    c1, c2, c3 = st.columns(3)
    sd = c1.selectbox("Día", DIAS)
    sh = c2.selectbox("Hora", HORAS)
    
    # Buscar salones
    ns = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", (cid, sd, sh), return_data=True)
    
    if ns:
        dn = {n: i for i, n in ns}
        sn = c3.selectbox("Salón:", list(dn.keys()))
        hid = dn[sn]
        
        st.divider()
        
        # 1. ALUMNOS REGULARES
        al_reg = run_query("""
            SELECT a.id, a.nombre, a.apellido, a.condicion
            FROM alumnos a JOIN matriculas m ON a.id = m.alumno_id
            WHERE m.horario_id = ?
        """, (hid,), return_data=True)
        
        # 2. GENERAR FECHAS (YA CORREGIDAS PARA NO SER SEGUIDAS)
        fechas = generar_fechas_clase(cfecha, sd)
        
        # 3. ALUMNOS DE RECUPERACIÓN (VISITANTES HOY)
        # Buscamos alumnos que tengan una recuperación programada en ESTE salón (hid) en alguna de las fechas mostradas
        # Nota: Esto es visualización avanzada.
        
        if al_reg:
            # Traer historial asistencia
            asist = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (hid,), return_data=True)
            mapa = {(r[0], r[1]): r[2] for r in asist}
            
            # --- CONSTRUIR TABLA ---
            data = []
            for al in al_reg:
                aid, nom, ape, cond = al
                row = {"ID": aid, "Alumno": f"{nom} {ape}"}
                if cond: row["Alumno"] += " 🔴"
                
                # Columnas de fechas
                for f in fechas:
                    est = mapa.get((aid, f))
                    # Convertir estado a símbolo
                    val = "✅" if est == "Presente" else ("❌" if est == "Falta" else ("🤧" if est == "Justificado" else None))
                    row[f] = val
                data.append(row)
                
            # Verificar si hay recuperaciones para hoy (extra logic visual)
            # Para simplificar la tabla editable, nos enfocamos en los matriculados primero
            # Pero mostraremos una alerta si alguien viene a recuperar hoy
            
            df = pd.DataFrame(data)
            
            # Configurar columnas
            cfg = {"ID": None, "Alumno": st.column_config.TextColumn(disabled=True, width="medium")}
            for f in fechas:
                # El selectbox ahora incluye Justificado (🤧)
                cfg[f] = st.column_config.SelectboxColumn(f[5:], options=["✅", "❌", "🤧"], width="small", required=False)
            
            st.info("Leyenda: ✅ Presente | ❌ Falta | 🤧 Justificado (Requiere Recuperación)")
            
            edited = st.data_editor(df, column_config=cfg, hide_index=True)
            
            if st.button("Guardar Asistencia"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                justificados_count = 0
                
                for i, r in edited.iterrows():
                    aid = r["ID"]
                    for f in fechas:
                        val = r[f]
                        est = None
                        if val == "✅": est = "Presente"
                        elif val == "❌": est = "Falta"
                        elif val == "🤧": est = "Justificado"
                        
                        if est:
                            c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?,?,?,?)", (aid, hid, f, est))
                            if est == "Justificado":
                                justificados_count += 1
                        elif val is None:
                            c.execute("DELETE FROM asistencia WHERE alumno_id=? AND horario_id=? AND fecha=?", (aid, hid, f))
                
                conn.commit()
                conn.close()
                st.success("Asistencia guardada.")
                if justificados_count > 0:
                    st.warning(f"⚠️ Has marcado {justificados_count} justificaciones. Ve a la pestaña 'Recuperaciones' para reprogramar esas clases.")
        else:
            st.warning("Salón vacío.")
            
        # --- SECCIÓN: VISITANTES POR RECUPERACIÓN ---
        st.write("---")
        st.subheader("🔄 Alumnos recuperando clase en este salón")
        hoy_str = date.today().strftime("%Y-%m-%d")
        
        # Buscar en tabla recuperaciones quien viene a este HID hoy o en fechas futuras
        visitantes = run_query("""
            SELECT r.fecha_destino, a.nombre, a.apellido, r.fecha_origen
            FROM recuperaciones r
            JOIN alumnos a ON r.alumno_id = a.id
            WHERE r.horario_destino_id = ?
            ORDER BY r.fecha_destino
        """, (hid,), return_data=True)
        
        if visitantes:
            for v in visitantes:
                f_dest, nom, ape, f_orig = v
                st.markdown(f"📅 **{f_dest}**: El alumno **{nom} {ape}** vendrá a recuperar su falta del día {f_orig}.")
        else:
            st.caption("No hay recuperaciones programadas en este salón.")

# ---------------------------------------------------------
# MÓDULO NUEVO: GESTIÓN DE RECUPERACIONES
# ---------------------------------------------------------
elif selected == "🔄 Recuperaciones":
    st.title("Gestionar Clases Justificadas")
    
    st.markdown("""
    Aquí aparecen los alumnos a los que les pusiste **🤧 Justificado** y aún no tienen fecha de recuperación asignada.
    """)
    
    # 1. BUSCAR JUSTIFICACIONES PENDIENTES
    # Lógica: Buscar en asistencia "Justificado" DONDE NO EXISTA una entrada en tabla recuperaciones con esa fecha de origen
    pendientes = run_query("""
        SELECT asis.alumno_id, a.nombre, a.apellido, asis.fecha, h.grupo, h.hora_inicio, asis.horario_id, a.nivel
        FROM asistencia asis
        JOIN alumnos a ON asis.alumno_id = a.id
        JOIN horarios h ON asis.horario_id = h.id
        WHERE asis.estado = 'Justificado'
        AND NOT EXISTS (
            SELECT 1 FROM recuperaciones r 
            WHERE r.alumno_id = asis.alumno_id AND r.fecha_origen = asis.fecha
        )
    """, return_data=True)
    
    if pendientes:
        st.warning(f"Hay {len(pendientes)} clases pendientes de recuperar.")
        
        for p in pendientes:
            aid, nom, ape, fecha_falta, grup, hora, hid_origen, nivel_alum = p
            
            with st.expander(f"🔴 {nom} {ape} - Faltó el {fecha_falta} ({grup} {hora})"):
                st.write(f"Nivel del alumno: **{nivel_alum}**")
                st.write("Asignar clase de recuperación:")
                
                # Formulario para agendar
                with st.form(f"recup_{aid}_{fecha_falta}"):
                    c1, c2 = st.columns(2)
                    fecha_nueva = c1.date_input("Fecha de Recuperación", min_value=date.today())
                    
                    # Buscar horarios compatibles (mismo nivel preferiblemente)
                    # Aquí traemos todos los horarios del sistema que coincidan con el nivel del alumno o general
                    # Para simplificar, mostramos horarios activos del sistema
                    
                    horarios_dest = run_query("""
                        SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre
                        FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id
                        WHERE h.nivel_salon = ? 
                    """, (nivel_alum,), return_data=True)
                    
                    if not horarios_dest:
                        # Si no hay de su nivel, mostramos todos
                        horarios_dest = run_query("SELECT h.id, h.grupo, h.hora_inicio, h.nivel_salon, c.nombre FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id", return_data=True)
                    
                    opciones_h = {f"{h[4]} | {h[1]} {h[2]} ({h[3]})": h[0] for h in horarios_dest}
                    
                    sel_h_dest = c2.selectbox("Salón Destino", list(opciones_h.keys()))
                    id_h_dest = opciones_h[sel_h_dest]
                    
                    if st.form_submit_button("Agendar Recuperación"):
                        run_query("""
                            INSERT INTO recuperaciones (alumno_id, fecha_origen, horario_destino_id, fecha_destino)
                            VALUES (?, ?, ?, ?)
                        """, (aid, fecha_falta, id_h_dest, str(fecha_nueva)))
                        st.success(f"Recuperación agendada para el {fecha_nueva}. Desaparecerá de esta lista.")
                        st.rerun()
    else:
        st.success("✅ ¡Todo al día! No hay justificaciones pendientes de programar.")

    st.divider()
    st.subheader("Historial de Recuperaciones Programadas")
    hist = run_query("""
        SELECT a.nombre, a.apellido, r.fecha_origen, r.fecha_destino, h.hora_inicio
        FROM recuperaciones r
        JOIN alumnos a ON r.alumno_id = a.id
        JOIN horarios h ON r.horario_destino_id = h.id
        ORDER BY r.id DESC
    """, return_data=True)
    
    if hist:
        df_hist = pd.DataFrame(hist, columns=["Alumno", "Apellido", "Faltó el", "Recupera el", "Hora"])
        st.dataframe(df_hist)

# ---------------------------------------------------------
# MÓDULO BASE DE DATOS
# ---------------------------------------------------------
elif selected == "Base de Datos":
    st.title("📂 Datos")
    st.write("Matrículas:")
    df = pd.read_sql_query("SELECT m.id, a.nombre, h.nivel_salon FROM matriculas m JOIN alumnos a ON m.alumno_id=a.id JOIN horarios h ON m.horario_id=h.id", sqlite3.connect(DB_NAME))
    st.dataframe(df)
