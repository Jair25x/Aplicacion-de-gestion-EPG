🎓 Aplicación de Gestión EPG - (Escuela de Posgrado)
🌟 Descripción del Proyecto
Esta es una aplicación web ligera desarrollada con Flask para la gestión centralizada de las operaciones de la Escuela de Posgrado (EPG). Su objetivo es optimizar los flujos de trabajo relacionados con el personal docente y la documentación académica.

Funcionalidades Principales:
Docentes: Gestión de la información completa del personal docente.

Programación de Cursos: Planificación y control de la programación académica por periodos.

Cartas de Invitación: Generación automatizada de cartas de invitación para los docentes.

Exportación de Datos: Herramientas para la exportación de reportes a formatos CSV (datos tabulares) y Word (documentación oficial).

🚀 Instalación y Ejecución Local
Sigue estos pasos para poner en marcha la aplicación en tu entorno de desarrollo local.

Requisitos
Python 3.10+ (Versión recomendada).

Git (Para clonar y gestionar versiones).

Instalación Rápida
Ejecuta los siguientes comandos en tu terminal, ubicándote en el directorio raíz del proyecto:

Bash

# 1. Crear el entorno virtual
python -m venv venv

# 2. Activar el entorno virtual (depende de tu shell)
source venv/Scripts/activate          # Recomendado (Git Bash / PowerShell)
# o
# .venv\Scripts\activate              # CMD (Windows)

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Inicializar la base de datos SQLite (crea el archivo docentes.db)
python init_db.py

# 5. Ejecutar la aplicación
python app.py
La aplicación se ejecutará y estará accesible en tu navegador en: 🔗 http://127.0.0.1:5000

☁️ Inicialización y Subida a GitHub
Esta sección detalla los pasos para enlazar tu proyecto local con el repositorio remoto.

1. Inicializar el Repositorio Local
Navega hasta la carpeta raíz del proyecto (gestion-docentes-app) en tu terminal (Git Bash es recomendado):

Bash

# Inicializa Git en el directorio
git init

# Verifica qué archivos detecta Git (debe ignorar venv/, *.db, etc. gracias a .gitignore)
git status
2. Configurar el Enlace Remoto
El repositorio remoto de este proyecto es: https://github.com/Jair25x/Aplicacion-de-gestion-EPG.git

Bash

# Enlaza el repositorio local con el remoto
git remote add origin https://github.com/Jair25x/Aplicacion-de-gestion-EPG.git

# Opcional: Verifica que el remoto se haya configurado correctamente
git remote -v
Deberías ver una salida similar a:

origin  https://github.com/Jair25x/Aplicacion-de-gestion-EPG.git (fetch)
origin  https://github.com/Jair25x/Aplicacion-de-gestion-EPG.git (push)
3. Primer Commit y Subida (Push)
Añade todos los archivos rastreables (no ignorados por .gitignore), realiza el primer commit y súbelo.

Bash

# Añade todos los archivos al staging area
git add .

# Realiza el primer commit
git commit -m "chore: initial import of EPG management app"

# Renombra la rama principal a 'main' (estándar de GitHub)
git branch -M main

# Sube los archivos a GitHub y establece 'origin/main' como la rama de seguimiento
git push -u origin main
Una vez finalizado, puedes visitar la URL del repositorio para confirmar que todo el código ha sido subido correctamente.