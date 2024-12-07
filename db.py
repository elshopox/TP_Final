import sqlite3

# Crear la base de datos
conn = sqlite3.connect('productos.db')
cursor = conn.cursor()

# Crear la tabla de productos
cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    precio REAL NOT NULL,
    imagen TEXT,
    unidades INTEGER NOT NULL
)
''')

conn.commit()
conn.close()
