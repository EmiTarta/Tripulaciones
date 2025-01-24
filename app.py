from flask import Flask, request, jsonify
from pymongo import MongoClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import json
import os
import pytz
from datetime import datetime
from google.oauth2 import service_account
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()
# Crea una instancia de la aplicación Flask
app = Flask(__name__)
# Variable global para almacenar la conexión a la base de datos MongoDB
db = None

# Obtiene las credenciales de la cuenta de servicio de Google Cloud desde la variable de entorno
credenciales_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
# Variable global para almacenar el servicio de Google Drive autenticado
servicio = None

def autenticar_drive():
    """
    Autentica en la API de Google Drive utilizando las credenciales proporcionadas
    y devuelve un objeto de servicio para interactuar con la API.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive']


    credenciales_dict = json.loads(credenciales_json)
    credenciales = service_account.Credentials.from_service_account_info(
        credenciales_dict, scopes=SCOPES
    )
    servicio = build('drive', 'v3', credentials=credenciales)
    return servicio


def obtener_servicio_drive():
    """
    Obtiene el servicio de Google Drive autenticado. Si aún no se ha autenticado,
    llama a la función `autenticar_drive()`.
    """
    global servicio
    if servicio is None:
        servicio = autenticar_drive()
    return servicio


def init_db():
    """
    Inicializa la conexión a la base de datos MongoDB utilizando la URI proporcionada
    en la variable de entorno.
    """
    global db
    try:
        churro = os.getenv("MONGODB_URI")
        client = MongoClient(churro)
        print("Conexión a MongoDB establecida.")
        db = client["ProyectoUPV"]
        print("Base de datos seleccionada:", db.name)
    except Exception as e:
        print(f"Error al conectar a MongoDB: {e}")
        db = None


# Crear una carpeta en Google Drive
def crear_carpeta(servicio, nombre_carpeta, carpeta_padre_id=None):
    """
    Crea una nueva carpeta en Google Drive.

    Args:
        servicio: Objeto de servicio de Google Drive autenticado.
        nombre_carpeta: Nombre de la nueva carpeta.
        carpeta_padre_id: ID de la carpeta padre (opcional).

    Returns:
        str: ID de la carpeta creada.

    Raises:
        Exception: Si ocurre un error al crear la carpeta.
    """
    try:
        metadatos_carpeta = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder',
        }
        if carpeta_padre_id:
            metadatos_carpeta['parents'] = [carpeta_padre_id]

        carpeta = servicio.files().create(body=metadatos_carpeta, fields='id').execute()
        print(f"Carpeta creada: {nombre_carpeta} (ID: {carpeta.get('id')})")
        return carpeta.get('id')
    except Exception as e:
        print(f"Error al crear carpeta en Google Drive: {e}")
        raise


def crear_estructura_completa(servicio, nombre_principal, cantidad_albumes, cantidad_marcos, cantidad_negativos):
    """
    Crea una estructura jerárquica de carpetas en Google Drive y registra la información en MongoDB.

    Args:
        servicio: Objeto de servicio de Google Drive autenticado.
        nombre_principal: Nombre de la carpeta principal.
        cantidad_albumes: Número de subcarpetas de tipo "album" a crear.
        cantidad_marcos: Número de subcarpetas de tipo "marco" a crear.
        cantidad_negativos: Número de subcarpetas de tipo "negativo" a crear.

    Returns:
        dict: Diccionario que representa la estructura creada, incluyendo IDs de carpetas.

    Raises:
        Exception: Si ocurre un error al crear la estructura.
    """
    try:
        estructura_creada = {
            "nRegistro": nombre_principal,
            "carpeta_principal_id": None,
            "subcarpetas": []
        }
        # Crear carpeta principal
        carpeta_main_id = crear_carpeta(servicio, nombre_principal, carpeta_padre_id='1bPAWz9cOhe9_sO-M_jGPaoInEqYTfzCE')
        estructura_creada["carpeta_principal_id"] = carpeta_main_id
        print("Carpeta Main creada")

        # Crear subcarpetas
        subcarpetas_main = ["M", "O", "S", "R", "F"]
        for tipo_subcarpeta in subcarpetas_main:
            n_registro_subcarpeta = f"{nombre_principal}-{tipo_subcarpeta}"
            subcarpeta_id = crear_carpeta(servicio, n_registro_subcarpeta, carpeta_main_id)

            subcarpeta = {
                "nRegistro": n_registro_subcarpeta,
                "id_subcarpeta": subcarpeta_id,
                "tipo": tipo_subcarpeta,
                "subcarpetas_internas": []
            }

            if tipo_subcarpeta != "R" and tipo_subcarpeta != "F":
                # Subcarpetas internas fijas
                subcarpetas_fijas = ["Z", "D"]
                for tipo_fija in subcarpetas_fijas:
                    n_registro_fija = f"{n_registro_subcarpeta}-{tipo_fija}"
                    subcarpeta_fija_id = crear_carpeta(servicio, n_registro_fija, subcarpeta_id)
                    subcarpeta_interna = {
                        "nRegistro": n_registro_fija,
                        "subcarpetas_internas_id": subcarpeta_fija_id,
                        "tipo": tipo_fija,
                        "imagenes": []
                    }
                    subcarpeta["subcarpetas_internas"].append(subcarpeta_interna)

                # Subcarpetas dinámicas
                for i in range(1, cantidad_albumes + 1):
                    n_registro_album = f"{n_registro_subcarpeta}-A{i:02d}"
                    album_id = crear_carpeta(servicio, n_registro_album, subcarpeta_id)
                    subcarpeta_interna = {
                        "nRegistro": n_registro_album,
                        "subcarpetas_internas_id": album_id,
                        "tipo": "A",
                        "imagenes": []
                    }
                    subcarpeta["subcarpetas_internas"].append(subcarpeta_interna)

                # Subcarpetas de marcos
                for i in range(1, cantidad_marcos + 1):
                    n_registro_marco = f"{n_registro_subcarpeta}-MC{i:02d}"
                    marco_id = crear_carpeta(servicio, n_registro_marco, subcarpeta_id)
                    subcarpeta_interna = {
                        "nRegistro": n_registro_marco,
                        "subcarpetas_internas_id": marco_id,
                        "tipo": "MC",
                        "imagenes": []
                    }
                    subcarpeta["subcarpetas_internas"].append(subcarpeta_interna)

                # Subcarpetas de negativos
                for i in range(1, cantidad_negativos + 1):
                    n_registro_negativo = f"{n_registro_subcarpeta}-NG{i:02d}"
                    negativo_id = crear_carpeta(servicio, n_registro_negativo, subcarpeta_id)
                    subcarpeta_interna = {
                        "nRegistro": n_registro_negativo,
                        "subcarpetas_internas_id": negativo_id,
                        "tipo": "NG",
                        "imagenes": []
                    }
                    subcarpeta["subcarpetas_internas"].append(subcarpeta_interna)

            estructura_creada["subcarpetas"].append(subcarpeta)

        print("Estructura completa creada")
        return estructura_creada
    except Exception as e:
        print(f"Error al crear estructura en Google Drive: {e}")
        raise
# Zona horaria de España
spain_timezone = pytz.timezone("Europe/Madrid")


def crear_estructura_en_mongodb(db, estructura_creada):
    """
    Inserta la información de la estructura creada en la base de datos MongoDB.

    Args:
        db: Objeto de conexión a la base de datos MongoDB.
        estructura_creada: Diccionario que representa la estructura creada.

    Returns:
        bool: True si la inserción fue exitosa, False en caso contrario.
    """
    try:
        if db is None:
            print("Error: Conexión a MongoDB no inicializada.")
            return False
        print("Datos a insertar en MongoDB:", estructura_creada)

        lote = {
            "nRegistro": estructura_creada["nRegistro"],
            "carpeta_principal_id": estructura_creada["carpeta_principal_id"],
            "subCarpetas": [],
            "created_at": datetime.now(spain_timezone)
        }
        lote_id = db.lotes.insert_one(lote).inserted_id
        print(f"Lote insertado con ID: {lote_id}")

        for subcarpeta in estructura_creada["subcarpetas"]:
            subcarpeta_doc = {
                "nRegistro": subcarpeta["nRegistro"],
                "id_subcarpeta": subcarpeta["id_subcarpeta"],
                "tipo": subcarpeta["tipo"],
                "subCarpetasInternas": [],
                "created_at": datetime.now(spain_timezone)
                                        }
            subcarpeta_id = db.subcarpetas.insert_one(subcarpeta_doc).inserted_id
            print(f"Subcarpeta insertada con ID: {subcarpeta_id}")

            db.lotes.update_one(
                {"_id": lote_id},
                {"$push": {"subCarpetas": subcarpeta["id_subcarpeta"]}}
            )

            for subcarpeta_interna in subcarpeta["subcarpetas_internas"]:
                subcarpeta_interna_doc = {
                    "nRegistro": subcarpeta_interna["nRegistro"],
                    "subcarpetas_internas_id": subcarpeta_interna["subcarpetas_internas_id"],
                    "tipo": subcarpeta_interna["tipo"],
                    "imagenes": subcarpeta_interna["imagenes"],
                    "created_at": datetime.now(spain_timezone) 
                }
                db.subcarpetainternas.insert_one(subcarpeta_interna_doc)

                db.subcarpetas.update_one(
                    {"_id": subcarpeta_id},
                    {"$push": {"subCarpetasInternas": subcarpeta_interna["subcarpetas_internas_id"]}}
                )
        print("Estructura almacenada en MongoDB con éxito.")
        return True
    except Exception as e:
        print(f"Error al crear la estructura en MongoDB: {e}")
        return False


def obtener_id_subcarpeta_interna(db, nRegistro):
    # obtener_id_subcarpeta_interna(db, nRegistro, tipo_carpeta, tipo_subcarpeta_interna)
    """
    Obtiene el ID de una subcarpeta interna dentro de una subcarpeta específica desde MongoDB.

    Args:
        db: Objeto de conexión a la base de datos MongoDB.
        nRegistro: Identificador único de la estructura.

    Returns:
        str: ID de la subcarpeta interna, o None si no se encuentra.
    """
    # Validar entradas
    if not nRegistro:
        print("Error: Faltan parámetros necesarios (nRegistro)")
        return None

    try:
        # Realizar la consulta en la colección 'subcarpetainternas'
        resultado = db['subcarpetainternas'].find_one(
            {
                "nRegistro": nRegistro,
            },
            {
                "subcarpetas_internas_id": 1,  # Solo devuelve el campo subcarpetas_internas_id
                "_id": 0  # Excluye el campo _id que MongoDB devuelve por defecto
            }
        )

        # Procesar el resultado
        if resultado:
            print(f"Subcarpeta interna encontrada: {resultado['subcarpetas_internas_id']}")
            return resultado['subcarpetas_internas_id']
        else:
            print(f"No se encontró una subcarpeta interna para nRegistro: {nRegistro}")
            return None
        
    except Exception as e:
        print(f"Error al buscar en la base de datos: {e}")
        return None
    

# Función para subir múltiples archivos
def subir_multiples_archivos(servicio, archivos, subcarpetas_internas_id):
    """
    Sube múltiples archivos a una carpeta específica en Google Drive.

    Args:
        servicio: Objeto de servicio de Google Drive autenticado.
        archivos: Lista de archivos a subir.
        subcarpetas_internas_id: ID de la carpeta de destino.

    Returns:
        list: Lista de IDs de los archivos subidos.
    """
    resultados = []

    for archivo in archivos:
        try:
            # Extraer información del archivo recibido
            nombre_archivo = archivo.filename
            contenido_archivo = archivo.read()
            mime_type = archivo.content_type  # Tipo MIME del archivo (por ejemplo, 'image/jpeg')

            # Preparar el archivo para subirlo a Google Drive
            media = MediaIoBaseUpload(io.BytesIO(contenido_archivo), mimetype=mime_type)

            metadatos_archivo = {
                'name': nombre_archivo,
                'parents': [subcarpetas_internas_id]
            }

            # Subir el archivo a Google Drive
            archivo_subido = servicio.files().create(body=metadatos_archivo, media_body=media, fields='id').execute()
            archivo_id = archivo_subido.get('id')
            # Guardar el resultado de la subida
            resultados.append(archivo_id)

        except Exception as e:
            print(f"Error al subir el archivo '{archivo.filename}': {e}")
    
    print("Subida de multiples archivos exitosa")
    return resultados


# Actualizar la colección subcarpetainternas en MongoDB
def actualizar_imagenes_en_mongo(db, nRegistro, ids_imagenes):
    """
    Actualiza la colección "subcarpetainternas" en MongoDB con los IDs de las imágenes subidas.

    Args:
        db: Objeto de conexión a la base de datos MongoDB.
        nRegistro: Identificador único de la estructura.
        ids_imagenes: Lista de IDs de las imágenes subidas.
    """
    try:
         # Crear una lista de objetos con id_imagen y created_at
        imagenes_con_timestamp = [
            {"id_imagen": id_imagen, "created_at": datetime.now(spain_timezone)}
            for id_imagen in ids_imagenes
        ]

        resultado = db['subcarpetainternas'].update_one(
            {"nRegistro": nRegistro},
            {"$push": {"imagenes": {"$each": imagenes_con_timestamp}}}
        )
        if resultado.modified_count > 0:
            print(f"Imágenes actualizadas en MongoDB para nRegistro: {nRegistro}")
        else:
            print(f"No se actualizó ninguna imagen en MongoDB para nRegistro: {nRegistro}")
    except Exception as e:
        print(f"Error al actualizar imágenes en MongoDB: {e}")


init_db()


@app.route('/crear_estructura_completa', methods=['GET'])
def crear_estructura_endpoint():
    """
    Endpoint para crear la estructura de carpetas en Google Drive y actualizar MongoDB.
    """
    try:
        if db is None:
            return jsonify({"error": "La conexión con la base de datos no está inicializada"}), 500

        nombre_principal = request.args.get('nombre_principal')
        cantidad_albumes = request.args.get('cantidad_albumes', default=0, type=int)
        cantidad_marcos = request.args.get('cantidad_marcos', default=0, type=int)
        cantidad_negativos = request.args.get('cantidad_negativos', default=0, type=int)

        if not nombre_principal or cantidad_albumes <= 0:
            return jsonify({"error": "Faltan parámetros requeridos o valores no válidos"}), 400

        servicio = obtener_servicio_drive()
        estructura_creada = crear_estructura_completa(servicio, nombre_principal, cantidad_albumes, cantidad_marcos, cantidad_negativos)
        print("Estructura creada para MongoDB:", estructura_creada)

        if crear_estructura_en_mongodb(db, estructura_creada):
            return jsonify({
                "mensaje": "Estructura creada con éxito y almacenada en la base de datos",
                "estructura_creada": estructura_creada
            }), 200
        else:
            return jsonify({
                "mensaje": "Estructura creada en Drive pero no se pudo almacenar en la base de datos",
                "estructura_creada": estructura_creada
            }), 500

    except Exception as e:
        print(f"Error en el endpoint: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


@app.route('/subir_archivos', methods=['POST'])
def subir_archivos():
    """
    Endpoint para recibir y subir múltiples archivos a Google Drive.
    """
    try:
        # Verificar que se han enviado archivos
        if 'archivo' not in request.files:
            return jsonify({"error": "No se proporcionaron archivos"}), 400

        archivos = request.files.getlist('archivo')  # Obtener los archivos enviados
        nRegistro = request.form.get('nRegistro')  # ID de la carpeta destino

        if not nRegistro:
            return jsonify({"error": "Se requiere el ID de la carpeta destino"}), 400

        # Obtener el ID de dicha carpeta
        subcarpetas_internas_id = obtener_id_subcarpeta_interna(db, nRegistro)
        if not subcarpetas_internas_id:
            return jsonify({"error": f"No se encontró subcarpetas_internas_id para nRegistro: {nRegistro}"}), 404
        # Autenticar en Google Drive
        servicio = obtener_servicio_drive()

        # Subir los archivos
        ids_imagenes = subir_multiples_archivos(servicio, archivos, subcarpetas_internas_id)

        # for carpetita in subcarpetas_internas_id:

        # Actualizar la colección subcarpetainternas en MongoDB
        actualizar_imagenes_en_mongo(db, nRegistro, ids_imagenes)

        return jsonify({
            "mensaje": "Archivos subidos con éxito",
            "ids_imagenes": ids_imagenes
        }), 200

    except Exception as e:
        print(f"Error en el endpoint: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', PORT=8080)