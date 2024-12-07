from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta'  # Necesaria para gestionar la sesión


# Datos de ejemplo del carrito de productos
carrito = [
    {'id': 1, 'nombre': 'Producto A', 'precio': 100, 'cantidad': 2},
    {'id': 2, 'nombre': 'Producto B', 'precio': 50, 'cantidad': 1}
]

# Configuración para guardar imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Asegúrate de que la carpeta de subida existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Conexión a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('productos.db')
    conn.row_factory = sqlite3.Row
    return conn


# Ruta para inicializar la base de datos
@app.route('/initdb')
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL,
            unidades INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    return "Base de datos inicializada correctamente."


# Ruta principal: Mostrar todos los productos
@app.route('/')
def index():
    conn = get_db_connection()
    productos = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()
    return render_template('index.html', productos=productos)

# Agregar producto al carrito
@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):
    conn = get_db_connection()
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()

    if producto and producto['unidades'] > 0:
        # Reducir unidades disponibles
        nuevas_unidades = producto['unidades'] - 1
        conn.execute('UPDATE productos SET unidades = ? WHERE id = ?', (nuevas_unidades, id))
        conn.commit()

        # Verificar si el producto tiene 0 unidades y eliminarlo
        if nuevas_unidades == 0:
            conn.execute('DELETE FROM productos WHERE id = ?', (id,))
            conn.commit()

        # Agregar al carrito
        if 'carrito' not in session:
            session['carrito'] = []
        session['carrito'].append({
            'id': producto['id'],
            'nombre': producto['nombre'],
            'precio': producto['precio'],
            'cantidad': 1
        })
        session.modified = True

    conn.close()
    return redirect(url_for('index'))

# Ruta para la página de ver.html, donde los productos son agregados al carrito
@app.route('/ver', methods=['GET', 'POST'])
def ver():
    if request.method == 'POST':
        # Aquí se deberían tomar los productos de la compra, en este ejemplo es una lista estática.
        productos = [
            {'nombre': 'Producto 1', 'precio': 10, 'cantidad': 2},
            {'nombre': 'Producto 2', 'precio': 5, 'cantidad': 3}
        ]
        # Guardamos la lista de productos en la sesión
        session['carrito'] = productos
        # Redirigimos a la página de facturación
        return redirect('/facturacion')

    # Si es un GET, solo mostramos la página de ver.html
    return render_template('ver.html')

# Ver carrito de compras
@app.route('/ver_carrito')
def ver_carrito():
    total = sum(item['precio'] for item in session.get('carrito', []))
    return render_template('ver.html', carrito=session.get('carrito', []), total=total)


# Eliminar producto del carrito
@app.route('/eliminar_carrito/<int:id>')
def eliminar_carrito(id):
    if 'carrito' in session:
        for item in session['carrito']:
            if item['id'] == id:
                session['carrito'].remove(item)
                session.modified = True
                # Devolver unidad al inventario
                conn = get_db_connection()
                conn.execute('UPDATE productos SET unidades = unidades + 1 WHERE id = ?', (id,))
                conn.commit()
                conn.close()
                break
    return redirect(url_for('ver_carrito'))


# Ruta para agregar productos (CRUD)
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        unidades = int(request.form['unidades'])

        # Manejar la subida de la imagen
        imagen = request.files['imagen']
        if imagen and imagen.filename != '':
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen.filename)
            imagen.save(imagen_path)
            imagen_url = f"uploads/{imagen.filename}"  # Ruta relativa para guardar en la base de datos
        else:
            imagen_url = "uploads/default.png"  # Imagen por defecto si no se sube ninguna

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO productos (nombre, descripcion, precio, imagen, unidades) VALUES (?, ?, ?, ?, ?)',
            (nombre, descripcion, precio, imagen_url, unidades)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('agregar.html')


# Editar productos
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = get_db_connection()
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        imagen = request.form['imagen']
        unidades = int(request.form['unidades'])

        conn.execute(
            'UPDATE productos SET nombre = ?, descripcion = ?, precio = ?, imagen = ?, unidades = ? WHERE id = ?',
            (nombre, descripcion, precio, imagen, unidades, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    conn.close()
    return render_template('editar.html', producto=producto)


# Facturación: Formulario de usuario y carrito
@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        fecha = request.form['fecha']
        total = sum(item['precio'] for item in session.get('carrito', []))
        return render_template('facturacion.html', nombre=nombre, apellido=apellido, fecha=fecha,
                               carrito=session.get('carrito', []), total=total)
    return render_template('formulario.html')


# Ruta de la página de facturación
@app.route('/facturacion', methods=['GET', 'POST'])
def facturacion():
    if request.method == 'POST':
        # Obtener los datos del formulario (nombre, apellido, fecha)
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        fecha = request.form.get('fecha')

        # Recuperar el carrito de la sesión
        carrito = session.get('carrito', [])

        # Si el carrito está vacío, redirigimos a la página de ver.html
        if not carrito:
            return redirect('/ver')

        # Calcular el total
        total = sum(item['precio'] * item['cantidad'] for item in carrito)

        # Pasar los datos al template
        return render_template('facturacion.html', nombre=nombre, apellido=apellido, fecha=fecha, carrito=carrito, total=total)

    # Si es un GET, redirigir a formulario.html para que el usuario ingrese los datos
    return render_template('formulario.html')


# Ruta para buscar productos
@app.route('/buscar', methods=['GET', 'POST'])
def buscar():
    if request.method == 'POST':
        termino = request.form['termino']  # Obtener el término de búsqueda desde el formulario
        conn = get_db_connection()
        # Consulta SQL para buscar por nombre o descripción
        productos = conn.execute(
            'SELECT * FROM productos WHERE nombre LIKE ? OR descripcion LIKE ?',
            (f'%{termino}%', f'%{termino}%')  # Usar el término de búsqueda con % para la coincidencia parcial
        ).fetchall()
        conn.close()
        # Renderizar la plantilla con los productos encontrados
        return render_template('index.html', productos=productos)
    return redirect(url_for('index'))

@app.route('/quienes_somos')
def quienes_somos():
    return render_template('quienes_somos.html')


if __name__ == '__main__':
    app.run(debug=True)

