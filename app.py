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
    div.row-widget.stRadio > div {flex-direction: row; gap: 10px;}
    div.row-widget.stRadio > div > label {
        background-color: #f0f2f6; padding: 10px 20px; border-radius: 8px; cursor: pointer; border: 1px solid #dcdcdc;
    }
    div.row-widget.stRadio > div > label:hover {background-color: #e0e2e6;}
    div.row-widget.stRadio > div > label[data-baseweb="radio"] {background-color: #ff4b4b; color: white;}
    .stDataFrame { border: 1px solid #e6e6e6; border-radius: 5px; }
    .big-font { font-size:20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('piscina_arenas_v4.db') # Nueva versión de BD
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS ciclos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_inicio DATE)''')
    
    # AHORA EL HORARIO TIENE 'NIVEL' (Actúa como Salón)
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
    
    # Parche por si acaso
    try: c.execute("ALTER TABLE horarios ADD COLUMN nivel_salon TEXT")
    except: pass
    
    conn.commit()
    conn.close()

def run_query(query, params=(), return_data=False):
    conn = sqlite3.connect('piscina_arenas_v4.db')
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
        options=["Asistencia", "Matrícula", "Promoción de Nivel", "Configuración", "Recuperaciones", "Reportes"],
        icons=["calendar-check", "person-plus", "graph-up-arrow", "gear", "bandaid", "clipboard-data"],
        default_index=0,
    )

# ==========================================
# 1. ASISTENCIA
# ==========================================
if selected == "Asistencia":
    st.title("📅 Asistencia por Salón")

    ciclos = run_query("SELECT id, nombre, fecha_inicio FROM ciclos ORDER BY id DESC", return_data=True)
    if not ciclos:
        st.warning("⚠️ Primero crea un ciclo.")
        st.stop()

    c_dict = {n: (i, f) for i, n, f in ciclos}
    nombre_ciclo_sel = st.selectbox("Ciclo:", list(c_dict.keys()))
    id_ciclo, fecha_inicio_ciclo = c_dict[nombre_ciclo_sel]

    st.write("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        grupo_sel = st.radio("Días:", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], label_visibility="collapsed")
    
    # Filtro dinámico de horas disponibles para ese grupo
    horas_disp = run_query("SELECT DISTINCT hora_inicio FROM horarios WHERE ciclo_id=? AND grupo=?", (id_ciclo, grupo_sel), return_data=True)
    
    if not horas_disp:
        st.info("No hay horarios.")
        st.stop()
        
    lista_horas = [h[0] for h in horas_disp]
    with col2:
        hora_texto = st.selectbox("Hora:", lista_horas)

    # AQUÍ ESTÁ EL CAMBIO: Ahora seleccionamos el NIVEL (Salón) dentro de esa hora
    salones_disp = run_query("SELECT id, nivel_salon FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=?", 
                             (id_ciclo, grupo_sel, hora_texto), return_data=True)
    
    if salones_disp:
        salon_dict = {s[1]: s[0] for s in salones_disp}
        with col3:
            nivel_salon = st.selectbox("Salón (Nivel):", list(salon_dict.keys()))
        id_horario = salon_dict[nivel_salon]
        
        # --- TABLA DE ASISTENCIA ---
        fechas_clase = calcular_fechas_clase(fecha_inicio_ciclo, grupo_sel)
        alumnos = run_query("SELECT a.id, a.nombre, a.apellido, a.condicion FROM alumnos a JOIN matriculas m ON a.id = m.alumno_id WHERE m.horario_id = ?", (id_horario,), return_data=True)

        if alumnos:
            data_rows = []
            asist_data = run_query("SELECT alumno_id, fecha, estado FROM asistencia WHERE horario_id=?", (id_horario,), return_data=True)
            asist_map = {(a, f): e for a, f, e in asist_data}

            for alum in alumnos:
                aid, nom, ape, cond = alum
                disp = f"{nom} {ape}"
                if cond and cond.strip(): disp = f"🔴 {nom} {ape} ({cond})"
                row = {"ID": aid, "Alumno": disp}
                for f in fechas_clase: row[f] = True if asist_map.get((aid, f)) == "Presente" else False
                data_rows.append(row)
                
            df = pd.DataFrame(data_rows)
            col_cfg = {"Alumno": st.column_config.TextColumn("Estudiante", disabled=True, width="medium"), "ID": None}
            for f in fechas_clase: col_cfg[f] = st.column_config.CheckboxColumn(f[5:], default=False)

            st.divider()
            edited_df = st.data_editor(df, column_config=col_cfg, height=400, use_container_width=True, hide_index=True)

            if st.button("💾 GUARDAR ASISTENCIA", type="primary", use_container_width=True):
                conn = sqlite3.connect('piscina_arenas_v4.db')
                c = conn.cursor()
                for idx, row in edited_df.iterrows():
                    aid = row["ID"]
                    for fecha in fechas_clase:
                        est = "Presente" if row[fecha] else "Falta"
                        c.execute("INSERT OR REPLACE INTO asistencia (alumno_id, horario_id, fecha, estado) VALUES (?, ?, ?, ?)", (aid, id_horario, fecha, est))
                conn.commit()
                conn.close()
                st.success("Guardado.")
                st.rerun()
        else:
            st.info(f"No hay alumnos en el salón {nivel_salon} a esta hora.")
    else:
        st.warning("No hay salones configurados para esta hora.")


# ==========================================
# 2. MATRÍCULA
# ==========================================
elif selected == "Matrícula":
    st.header("📝 Gestión de Matrículas")
    tab1, tab2 = st.tabs(["🆕 Nuevo Alumno", "🔄 Re-matrícula"])
    
    # --- NUEVO ALUMNO ---
    with tab1:
        with st.form("form_new"):
            c1, c2 = st.columns(2)
            n, a = c1.text_input("Nombres"), c2.text_input("Apellidos")
            tel, apo = c1.text_input("Teléfono"), c2.text_input("Apoderado")
            
            # SELECCIÓN DE NIVEL OBLIGATORIA
            niv = st.selectbox("Nivel Asignado", NIVELES)
            
            dire = c1.text_input("Dirección")
            cond = st.text_area("Condición Especial", placeholder="Ej: TDAH...")
            
            st.markdown("### 🔎 Buscar Salón Disponible")
            ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
            if ciclos:
                cd = {name: id for id, name in ciclos}
                sel_c = st.selectbox("Ciclo", list(cd.keys()))
                sel_g = st.radio("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
                
                # FILTRO CLAVE: Solo mostramos horarios del NIVEL seleccionado
                hors = run_query("SELECT id, hora_inicio, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND nivel_salon=?", 
                                 (cd[sel_c], sel_g, niv), return_data=True)
                
                opciones_h = {}
                if hors:
                    for h in hors:
                        hid, ini, cap = h
                        cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                        lbl = f"{ini} - {niv} (Cupos: {cnt}/{cap})"
                        if cnt < cap: opciones_h[lbl] = hid
                        else: opciones_h[f"⛔ LLENO - {lbl}"] = None
                    sel_h = st.selectbox("Horarios disponibles para este nivel:", list(opciones_h.keys()))
                else:
                    st.warning(f"No hay salones de {niv} creados en este horario/ciclo.")
                    sel_h = None

                if st.form_submit_button("Matricular"):
                    if sel_h and opciones_h[sel_h]:
                        run_query("INSERT INTO alumnos (nombre, apellido, telefono, direccion, nivel, apoderado, fecha_registro, condicion) VALUES (?,?,?,?,?,?,?,?)", 
                                  (n, a, tel, dire, niv, apo, date.today(), cond))
                        aid = run_query("SELECT last_insert_rowid()", return_data=True)[0][0]
                        run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (aid, opciones_h[sel_h], date.today()))
                        st.success("Matriculado en su nivel correcto.")
                    else:
                        st.error("Datos faltantes o sin cupo.")

    # --- RE-MATRÍCULA ---
    with tab2:
        search = st.text_input("Buscar Alumno:")
        if search:
            res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{search}%' OR apellido LIKE '%{search}%'", return_data=True)
            if res:
                opts = {f"{r[1]} {r[2]} (Nivel Actual: {r[3]})": (r[0], r[3]) for r in res}
                sel_txt = st.selectbox("Seleccionar:", list(opts.keys()))
                id_alum, nivel_actual = opts[sel_txt]
                
                st.info(f"Buscando salones para nivel: **{nivel_actual}**")
                
                if ciclos:
                    cd2 = {name: id for id, name in ciclos}
                    sc2 = st.selectbox("Ciclo Destino", list(cd2.keys()), key="rm_c")
                    sg2 = st.radio("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"], key="rm_g")
                    
                    # FILTRO POR NIVEL ACTUAL
                    h2 = run_query("SELECT id, hora_inicio, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND nivel_salon=?", 
                                   (cd2[sc2], sg2, nivel_actual), return_data=True)
                    op2 = {}
                    if h2:
                        for h in h2:
                            hid, ini, cap = h
                            cnt = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid,), return_data=True)[0][0]
                            lbl = f"{ini} - {nivel_actual} ({cnt}/{cap})"
                            if cnt < cap: op2[lbl] = hid
                            else: op2[f"⛔ LLENO - {lbl}"] = None
                        sh2 = st.selectbox("Horario:", list(op2.keys()), key="rm_h")
                        
                        if st.button("Confirmar Re-matrícula"):
                            if sh2 and op2[sh2]:
                                run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (id_alum, op2[sh2], date.today()))
                                st.success("Re-matriculado.")
                    else:
                        st.warning(f"No existen horarios de {nivel_actual} en esa selección.")

# ==========================================
# 3. PROMOCIÓN DE NIVEL (NUEVO)
# ==========================================
elif selected == "Promoción de Nivel":
    st.header("🚀 Promover Alumno de Nivel")
    st.markdown("Aquí puedes subir de nivel a un alumno y moverlo al salón correspondiente.")
    
    busq_prom = st.text_input("Buscar Alumno a Promover:")
    if busq_prom:
        res = run_query(f"SELECT id, nombre, apellido, nivel FROM alumnos WHERE nombre LIKE '%{busq_prom}%' OR apellido LIKE '%{busq_prom}%'", return_data=True)
        if res:
            dic_al = {f"{r[1]} {r[2]} (Actual: {r[3]})": r for r in res}
            sel_al = st.selectbox("Seleccionar Alumno:", list(dic_al.keys()))
            datos_alum = dic_al[sel_al] # (id, nom, ape, nivel)
            id_a, nivel_viejo = datos_alum[0], datos_alum[3]
            
            # Determinar siguiente nivel lógico
            try:
                idx_actual = NIVELES.index(nivel_viejo)
                idx_nuevo = min(idx_actual + 1, len(NIVELES) - 1)
                nivel_sugerido = NIVELES[idx_nuevo]
            except:
                nivel_sugerido = NIVELES[0]
            
            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Nivel Actual:** {nivel_viejo}")
                nuevo_nivel = st.selectbox("Promover a:", NIVELES, index=NIVELES.index(nivel_sugerido) if nivel_sugerido in NIVELES else 0)
            
            with col_b:
                st.markdown("**¿Qué hacemos con su horario?**")
                # Opción inteligente: Buscar si hay un horario igual (mismo ciclo, mismo dia, misma hora) pero del NUEVO nivel
                # 1. Obtener matricula actual vigente (la ultima)
                mat_actual = run_query("""
                    SELECT m.id, h.ciclo_id, h.grupo, h.hora_inicio 
                    FROM matriculas m JOIN horarios h ON m.horario_id = h.id 
                    WHERE m.alumno_id = ? ORDER BY m.id DESC LIMIT 1
                """, (id_a,), return_data=True)
                
                nuevo_horario_id = None
                
                if mat_actual:
                    mid, cid, grp, hora = mat_actual[0]
                    st.write(f"Asiste actualmente: {grp} a las {hora}")
                    
                    # Buscar el equivalente en el nuevo nivel
                    horario_equiv = run_query("SELECT id, capacidad FROM horarios WHERE ciclo_id=? AND grupo=? AND hora_inicio=? AND nivel_salon=?", 
                                              (cid, grp, hora, nuevo_nivel), return_data=True)
                    
                    if horario_equiv:
                        hid_eq, cap_eq = horario_equiv[0]
                        cnt_eq = run_query("SELECT COUNT(*) FROM matriculas WHERE horario_id=?", (hid_eq,), return_data=True)[0][0]
                        if cnt_eq < cap_eq:
                            st.success(f"✅ ¡Hay cupo en el mismo horario para {nuevo_nivel}!")
                            nuevo_horario_id = hid_eq
                        else:
                            st.error(f"El salón de {nuevo_nivel} a esa hora está lleno.")
                    else:
                        st.warning(f"No existe un salón de {nuevo_nivel} a esa hora. Deberás re-matricularlo manualmente después.")
                else:
                    st.warning("El alumno no tiene matrícula activa.")

            st.write("---")
            if st.button("🚀 Confirmar Promoción", type="primary"):
                # 1. Actualizar Nivel en Alumno
                run_query("UPDATE alumnos SET nivel = ? WHERE id = ?", (nuevo_nivel, id_a))
                msg = f"Alumno promovido a {nuevo_nivel}."
                
                # 2. Mover de salón automáticamente si se encontró
                if nuevo_horario_id:
                    run_query("INSERT INTO matriculas (alumno_id, horario_id, fecha_inicio) VALUES (?,?,?)", (id_a, nuevo_horario_id, date.today()))
                    msg += " Y movido al nuevo salón automáticamente."
                else:
                    msg += " Ve a 'Matrícula' para asignarle un nuevo horario."
                
                st.balloons()
                st.success(msg)

# ==========================================
# 4. CONFIGURACIÓN (CREAR SALONES)
# ==========================================
elif selected == "Configuración":
    st.header("⚙️ Configuración de Salones")
    
    tab1, tab2 = st.tabs(["1. Ciclos", "2. Salones (Horarios+Nivel)"])
    
    with tab1:
        nc = st.text_input("Nombre Ciclo (Ej: Abril 2026)")
        fi = st.date_input("Inicio de Clases")
        if st.button("Crear Ciclo"):
            run_query("INSERT INTO ciclos (nombre, fecha_inicio) VALUES (?, ?)", (nc, fi))
            st.success("Hecho.")
            
    with tab2:
        st.info("Aquí defines los 'carriles' o 'salones'. Ejemplo: A las 9:00 AM hay un grupo de Básico 0 y otro de Avanzado.")
        ciclos = run_query("SELECT id, nombre FROM ciclos", return_data=True)
        if ciclos:
            cd = {n: i for i, n in ciclos}
            c_sel = st.selectbox("Ciclo", list(cd.keys()))
            
            c1, c2, c3, c4 = st.columns(4)
            grp = c1.selectbox("Días", ["Lunes-Miércoles-Viernes", "Martes-Jueves-Sábado"])
            
            horas_std = ["07:00 - 08:00", "08:00 - 09:00", "09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00",
                         "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00"]
            hr = c2.selectbox("Hora", horas_std)
            
            # SELECCIÓN DE NIVEL PARA ESTE HORARIO
            niv_salon = c3.selectbox("Nivel del Salón", NIVELES)
            
            cap = c4.number_input("Cupos", 5) # Cupos más chicos por carril
            
            if st.button("Crear Salón"):
                run_query("INSERT INTO horarios (ciclo_id, grupo, hora_inicio, capacidad, nivel_salon) VALUES (?,?,?,?,?)", 
                          (cd[c_sel], grp, hr, cap, niv_salon))
                st.success(f"Salón de {niv_salon} creado a las {hr}")
                
            st.write("---")
            st.markdown("**Salones Configurados en este Ciclo:**")
            df = pd.read_sql_query(f"SELECT grupo, hora_inicio, nivel_salon, capacidad FROM horarios WHERE ciclo_id={cd[c_sel]} ORDER BY hora_inicio", sqlite3.connect('piscina_arenas_v4.db'))
            st.dataframe(df)

# ==========================================
# 5. RECUPERACIONES
# ==========================================
elif selected == "Recuperaciones":
    st.title("Agendar Recuperación")
    alum_all = run_query("SELECT id, nombre, apellido, nivel FROM alumnos", return_data=True)
    if alum_all:
        dic = {f"{n} {a} ({lv})": (i, lv) for i, n, a, lv in alum_all}
        sel = st.selectbox("Alumno", list(dic.keys()))
        id_a, niv_a = dic[sel]
        
        fecha = st.date_input("Fecha Recuperación")
        
        # Mostrar solo horarios COMPATIBLES CON SU NIVEL
        st.write(f"Buscando salones de nivel: {niv_a}")
        horarios = run_query(f"SELECT h.id, c.nombre, h.grupo, h.hora_inicio FROM horarios h JOIN ciclos c ON h.ciclo_id = c.id WHERE h.nivel_salon = '{niv_a}'", return_data=True)
        
        if horarios:
            h_r_dict = {f"{c} | {g} | {h}": i for i, c, g, h in horarios}
            sel_h_r = st.selectbox("Salón Destino", list(h_r_dict.keys()))
            if st.button("Agendar"):
                 run_query("INSERT INTO recuperaciones_programadas (alumno_id, horario_destino_id, fecha_destino) VALUES (?, ?, ?)", (id_a, h_r_dict[sel_h_r], str(fecha)))
                 st.success("Agendado")
        else:
            st.error("No hay salones de este nivel disponibles para recuperar.")

# ==========================================
# 6. REPORTES
# ==========================================
elif selected == "Reportes":
    st.header("Historial")
    busqueda = st.text_input("Apellido:")
    if busqueda:
        res = run_query(f"SELECT id, nombre, apellido, nivel, condicion FROM alumnos WHERE apellido LIKE '%{busqueda}%'", return_data=True)
        if res:
            for r in res:
                aid, n, a, niv, c = r
                st.markdown(f"### {n} {a}")
                st.info(f"Nivel Actual: {niv}")
                if c: st.error(f"Condición: {c}")
                
                mats = run_query("""
                    SELECT c.nombre, h.grupo, h.hora_inicio, h.nivel_salon, m.horario_id
                    FROM matriculas m JOIN horarios h ON m.horario_id = h.id JOIN ciclos c ON h.ciclo_id = c.id
                    WHERE m.alumno_id = ? ORDER BY m.id DESC
                """, (aid,), return_data=True)
                
                for m in mats:
                    ciclo, grp, hr, n_sal, hid = m
                    asist = run_query("SELECT COUNT(*) FROM asistencia WHERE alumno_id=? AND horario_id=? AND estado='Presente'", (aid, hid), return_data=True)[0][0]
                    st.write(f"- {ciclo} | {grp} {hr} ({n_sal}) | Asistencias: {asist}/12")
                st.divider()
