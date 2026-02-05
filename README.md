
# Sistema de Gestión - Piscina Arenasbeta
🏊

Aplicación web desarrollada en Python y Streamlit para la gestión de matrículas, horarios y asistencias de la academia de natación "Piscina Arenas".

## Funcionalidades Principales

1.  **Gestión de Ciclos y Horarios:** Creación dinámica de ciclos (ej. 2026-1) y horarios (L-M-V / M-J-S) con control de capacidad.
2.  **Matrícula:** Inscripción de niños con validación de cupos disponibles. Registro de datos completos (Apoderado, nivel, teléfono, etc.).
3.  **Control de Asistencia:**
    * Listado diario por horario.
    * Barra de búsqueda rápida de alumnos.
    * Estados: Presente, Falta, Justificado.
    * Contador de clases (Meta: 12 clases por matrícula).
4.  **Sistema de Recuperación:**
    * Permite programar una clase de recuperación en una fecha y horario diferente.
    * El alumno aparece automáticamente en la lista de asistencia del día de recuperación con una alerta visual.

## Requisitos

* Python 3.8 o superior
* Librerías listadas en `packages.txt`

## Instalación y Ejecución

1.  **Clonar el repositorio o descargar los archivos:**
    Asegúrate de tener `app.py` y `packages.txt` en la misma carpeta.

2.  **Instalar dependencias:**
    Abre una terminal en la carpeta del proyecto y ejecuta:
    ```bash
    pip install -r packages.txt
    ```

3.  **Ejecutar la aplicación:**
    En la terminal, ejecuta:
    ```bash
    streamlit run app.py
    ```

4.  **Usar el programa:**
    Se abrirá automáticamente una pestaña en tu navegador (usualmente en `http://localhost:8501`).

## Estructura de Datos

El sistema utiliza una base de datos **SQLite** local (`piscina_arenas.db`) que se crea automáticamente la primera vez que ejecutas el programa. No requiere configuración adicional de servidores.

---
Desarrollado para Piscina Arenas.
