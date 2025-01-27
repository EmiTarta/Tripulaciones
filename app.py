from flask import Flask, request, jsonify
from pymongo import MongoClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseUpload
import io
import json
import os
import pytz
from datetime import datetime
from google.oauth2 import service_account
from dotenv import load_dotenv
from flask_cors import CORS
import replicate 
from io import BytesIO

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Crea una instancia de la aplicación Flask
app = Flask(__name__)

# Variable global para almacenar la conexión a la base de datos MongoDB
db = None

# Código para probar React en local. 
CORS(app, origins=['http://localhost:5173'])

# Obtiene las credenciales de la cuenta de servicio de Google Cloud desde la variable de entorno
credenciales_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]

# Variable global para almacenar el servicio de Google Drive autenticado
servicio = None

prompt =  "Analyze the provided image for significant damage. Return ONLY a 0 or a 1. NOT include any other text or explanations. Classification Criteria:*   Black and White Images: Exercise extra caution when evaluating damage.*   Buildings: If the image depicts buildings with extensive structural damage (perimeter or local gaps significantly impacting the structure), return 1.*   Emphasis the Analyze the image to find people: Do NOT get confused, they must be images of people in different places. Damage Assessment (Prioritized by Impact): 1.  Face (if present): Damage affecting the face has the highest priority. Return 1 if:    *   Damage significantly distorts facial features (e.g., missing eye, distorted nose/mouth).    *   Large obscuring gaps or extreme discoloration hinder face identification.2.  Image Composition (Perimeter Gaps): Evaluate loss of information at the image edges. Return 1 if perimeter gaps severely compromise the image composition.  3.Local Gaps: Evaluate loss of information within the image. Return 1 if multiple large local gaps obscure significant details, especially facial features.  4.Smudges: Unwanted marks that appear on the surface of the image, Return 1. Return 0 if the damage is minor and does NOT significantly affect the face (if present) or the overall composition. Examples of Minor Damage (Return 0):*   Scratches (especially on edges)*   Small Scattered stains NOT affecting the FACE*   Slight discoloration*   Minor wrinkles*   Missing corner NOT affecting the FACE. Examples: Eye erased by a gap: 1.Large stain covering PART of the FACE: 1. Slight discoloration and small wrinkle: 0.More Discoloration and more wrinkles(barely distinguishable image): 1.  IMPORTANT REMEMBER: Return ONLY a 0 or a 1. NOT include any other text or explanations."


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

            # Inicializar subcarpetas internas solo para M, O, S
            if tipo_subcarpeta in ["M", "O", "S"]:
                subcarpeta = {
                    "nRegistro": n_registro_subcarpeta,
                    "id_subcarpeta": subcarpeta_id,
                    "tipo": tipo_subcarpeta,
                    "subcarpetas_internas": []
                }

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
                    subcarpeta["subcarpetas_internas"].append({
                        "nRegistro": n_registro_album,
                        "subcarpetas_internas_id": album_id,
                        "tipo": "A",
                        "imagenes": []
                    })

                # Subcarpetas de marcos
                for i in range(1, cantidad_marcos + 1):
                    n_registro_marco = f"{n_registro_subcarpeta}-MC{i:02d}"
                    marco_id = crear_carpeta(servicio, n_registro_marco, subcarpeta_id)
                    subcarpeta["subcarpetas_internas"].append({
                        "nRegistro": n_registro_marco,
                        "subcarpetas_internas_id": marco_id,
                        "tipo": "MC",
                        "imagenes": []
                    })

                # Subcarpetas de negativos
                for i in range(1, cantidad_negativos + 1):
                    n_registro_negativo = f"{n_registro_subcarpeta}-NG{i:02d}"
                    negativo_id = crear_carpeta(servicio, n_registro_negativo, subcarpeta_id)
                    subcarpeta["subcarpetas_internas"].append({
                        "nRegistro": n_registro_negativo,
                        "subcarpetas_internas_id": negativo_id,
                        "tipo": "NG",
                        "imagenes": []
                    })
            else:
                # Inicializar como lista vacía para imágenes
                subcarpeta = {
                    "nRegistro": n_registro_subcarpeta,
                    "id_subcarpeta": subcarpeta_id,
                    "tipo": tipo_subcarpeta,
                    "imagenes": []  # Lista vacía para F y R
                }
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

        # Procesar subcarpetas
        for subcarpeta in estructura_creada["subcarpetas"]:
            # Caso para M, O, S: Subcarpetas internas
            if subcarpeta["tipo"] in ["M", "O", "S"]:
                subcarpeta_doc = {
                    "nRegistro": subcarpeta["nRegistro"],
                    "id_subcarpeta": subcarpeta["id_subcarpeta"],
                    "tipo": subcarpeta["tipo"],
                    "subCarpetasInternas": [],  # Inicializar subcarpetas internas
                    "created_at": datetime.now(spain_timezone)
                }
                # Insertar cada subcarpeta interna
                for subcarpeta_interna in subcarpeta["subcarpetas_internas"]:
                    subcarpeta_interna_doc = {
                        "nRegistro": subcarpeta_interna["nRegistro"],
                        "subcarpetas_internas_id": subcarpeta_interna["subcarpetas_internas_id"],
                        "tipo": subcarpeta_interna["tipo"],
                        "imagenes": subcarpeta_interna["imagenes"],
                        "created_at": datetime.now(spain_timezone)
                    }
                    # Insertar subcarpetas internas en MongoDB
                    db.subcarpetainternas.insert_one(subcarpeta_interna_doc)
                    subcarpeta_doc["subCarpetasInternas"].append(subcarpeta_interna_doc["subcarpetas_internas_id"])
             # Caso para F y R: Lista de imágenes, sin subcarpetas internas
            elif subcarpeta["tipo"] in ["F", "R"]:
                subcarpeta_doc = {
                    "nRegistro": subcarpeta["nRegistro"],
                    "id_subcarpeta": subcarpeta["id_subcarpeta"],
                    "tipo": subcarpeta["tipo"],
                    "imagenes": subcarpeta.get("imagenes", []),  # Inicializar lista de imágenes
                    "created_at": datetime.now(spain_timezone)
                }
            subcarpeta_id = db.subcarpetas.insert_one(subcarpeta_doc).inserted_id
            print(f"Subcarpeta insertada con ID: {subcarpeta_id}")

            # Actualizar el lote con la subcarpeta
            db.lotes.update_one(
                {"_id": lote_id},
                {"$push": {"subCarpetas": subcarpeta_id}}
            )
        print("Estructura almacenada en MongoDB con éxito.")
        return True
    except Exception as e:
        print(f"Error al crear la estructura en MongoDB: {e}")
        return False


def obtener_id_subcarpeta(db, nRegistro):
    """
    Obtiene el ID del documento correcto dependiendo de la colección (subcarpetas o subcarpetainternas).

    Args:
        db: Objeto de conexión a la base de datos MongoDB.
        nRegistro: Identificador único de la estructura.

    Returns:
        str: Valor del campo solicitado ('id_subcarpeta' o 'subcarpetas_internas_id'), o None si no se encuentra.
    """
    # Validar entradas
    if not nRegistro:
        print("Error: Faltan parámetros necesarios (nRegistro)")
        return None
    
    # Determinar la colección según el formato de nRegistro
    if "-" in nRegistro[8:]:  # Si hay algo después del octavo carácter, es una subcarpeta interna
        coleccion = "subcarpetainternas"
        campo = "subcarpetas_internas_id"  # Campo a buscar en subcarpetainternas
    else:  # Si no, es una subcarpeta normal
        coleccion = "subcarpetas"
        campo = "id_subcarpeta"  # Campo a buscar en subcarpetas

    try:
        # Realizar la consulta en la colección 'subcarpetainternas'
        resultado = db[coleccion].find_one(
            {
                "nRegistro": nRegistro,
            },
            {
                campo: 1,  # Solo devuelve el campo subcarpetas_internas_id
                "_id": 0  # Excluye el campo _id que MongoDB devuelve por defecto
            }
        )

        # Procesar el resultado
        if resultado and campo in resultado:
            print(f"{campo} encontrado en colección '{coleccion}': {resultado[campo]}")
            return resultado[campo]
        else:
            print(f"No se encontró el campo '{campo}' para nRegistro: {nRegistro} en la colección '{coleccion}'")
            return None
        
    except Exception as e:
        print(f"Error al buscar en la base de datos: {e}")
        return None
    

def subir_archivo(servicio, archivo, subcarpeta_id, nRegistro):
    """
    Sube un archivo específico a una carpeta de Google Drive.

    Args:
        servicio: Objeto de servicio de Google Drive autenticado.
        archivo: Archivo recibido en la solicitud.
        subcarpeta_id: ID de la subcarpeta de destino.
        nRegistro: Identificador único de la estructura.

    Returns:
        dict: Datos del archivo subido (ID y nombre).
    """
    contador = 1
    try:
        # Extraer información del archivo recibido
        nombre_archivo = archivo.filename
        contenido_archivo = archivo.read()
        mime_type = archivo.content_type  # Tipo MIME del archivo (por ejemplo, 'image/jpeg')

        # Generar nombre único para el archivo
        nombre_archivo = f"{nRegistro}-F-{contador:03}"

        # Preparar el archivo para subirlo a Google Drive
        media = MediaIoBaseUpload(io.BytesIO(contenido_archivo), mimetype=mime_type)
        metadatos_archivo = {
            'name': nombre_archivo,
            'parents': [subcarpeta_id]
        }

        # Subir el archivo a Google Drive
        archivo_subido = servicio.files().create(body=metadatos_archivo, media_body=media, fields='id').execute()
        archivo_id = archivo_subido.get('id')
        print(f"Archivo subido: {nombre_archivo} (ID: {archivo_id})")

        return {
            'id': archivo_id,
            'nombre': nombre_archivo
        }

    except Exception as e:
        print(f"Error al subir el archivo '{archivo.filename}': {e}")
        return None


# Función para subir múltiples archivos
def subir_multiples_archivos(servicio, archivos, subcarpetas_internas_id, nRegistro):
    """
    Sube múltiples archivos a una carpeta específica en Google Drive.

    Args:
        servicio: Objeto de servicio de Google Drive autenticado.
        archivos: Lista de archivos a subir.
        subcarpetas_internas_id: ID de la carpeta de destino.
        nRegistro: Nombre base proporcionado por el usuario.

    Returns:
        list: Lista de IDs de los archivos subidos.
    """
    resultados = []
    # contador = 1

    for archivo in archivos:
        try:
            # Extraer información del archivo recibido
            nombre_archivo = archivo.filename
            contenido_archivo = archivo.read()
            mime_type = archivo.content_type  # Tipo MIME del archivo (por ejemplo, 'image/jpeg')

            # Preparar el archivo para subirlo a Google Drive
            media = MediaIoBaseUpload(io.BytesIO(contenido_archivo), mimetype=mime_type)
            # nombre_archivo =  f"{nRegistro}-{contador:03}"
            metadatos_archivo = {
                'name': nombre_archivo,
                'parents': [subcarpetas_internas_id]
            }

            # Subir el archivo a Google Drive
            archivo_subido = servicio.files().create(body=metadatos_archivo, media_body=media, fields='id').execute()
            archivo_id = archivo_subido.get('id')
            # Guardar el resultado de la subida
            resultados.append({
                'id': archivo_id,
                'nombre': nombre_archivo
            })
            contador += 1

        except Exception as e:
            print(f"Error al subir el archivo '{archivo.filename}': {e}")
    
    print("Subida de multiples archivos exitosa")
    return resultados


# Funcion de clasificador
def classification_llava(img_bytes):
    """
    Clasifica una imagen a partir de un objeto en memoria (BytesIO o bytes).

    :param img_bytes: Contenido de la imagen en formato bytes o BytesIO.
    :return: Resultado de la clasificación.
    """
    # Si el input es bytes, conviértelo en BytesIO
    if isinstance(img_bytes, bytes):
        img_stream = BytesIO(img_bytes)
    elif hasattr(img_bytes, "read"):
        img_stream = img_bytes
    else:
        raise ValueError("El argumento img_bytes debe ser bytes o un objeto similar a BytesIO.")

    # Crear el diccionario de entrada
    input_data = {
        "image": img_stream,
        "prompt": prompt
    }

    events = []
    # Realizar la clasificación con replicate
    try:
        for event in replicate.stream(
            "yorickvp/llava-v1.6-mistral-7b:19be067b589d0c46689ffa7cc3ff321447a441986a7694c01225973c2eafc874",
            input=input_data
        ):
            events.append(event.data)

        output =  " ".join(events)
        output = output.replace("{}","")
        output = output.replace(" ","")

        # Reemplazar 0 por "IA" y 1 por "PS"
        if output == "0":
            return "IA"
        elif output == "1":
            return "PS"
        else:
            raise ValueError(f"Valor inesperado en la salida: {output}")
    
    except Exception as e:
        print(f"Error al procesar la imagen: {e}")
        return {"error": str(e)}


# Funcion de Clasificacion
def clasificacion(archivos):
    classifications = []

    for archivo in archivos:
        try:
            # Extraer información del archivo recibido
            nombre_archivo = archivo.filename
            contenido_archivo = archivo.read()

            # Validar si el archivo tiene contenido
            if not contenido_archivo:
                print(f"El archivo '{nombre_archivo}' está vacío. Saltando clasificación.")
                classifications.append("Archivo vacío")
                continue

            # Usar una copia del archivo para clasificar
            archivo_memoria = BytesIO(contenido_archivo)

            # Clasificar la imagen utilizando el objeto en memoria
            try:
                classification_result = classification_llava(archivo_memoria)
                if classification_result:
                    classifications.append(classification_result)

                else:
                    classifications.append("Clasificación no realizada")

            except Exception as e:
                print(f"Error durante la clasificación de {nombre_archivo}: {e}")
                classifications.append("Error durante clasificación")
            
            # Volver a colocar el puntero al inicio para que esté listo para la subida
            archivo.stream.seek(0)
            
        except Exception as e:
            print(f"Error al procesar el archivo '{archivo.filename}': {e}")
            classifications.append("Error general")

    return classifications


# Actualizar la colección subcarpetainternas en MongoDB
def actualizar_imagenes_en_mongo(db, nRegistro, ids_imagenes, classifications=None):
    """
    Actualiza la colección "subcarpetainternas"  o las carpetas F/R en MongoDB con los IDs de las imágenes subidas.

    Args:
        db: Objeto de conexión a la base de datos MongoDB.
        nRegistro: Identificador único de la estructura.
        ids_imagenes: Lista de IDs de las imágenes subidas.
    """
    try:
         # Crear una lista de objetos con id_imagen y created_at
        imagenes_con_timestamp = []  # Lista vacía para almacenar los resultados
        if nRegistro.split("-")[2] == "S":
            for indice, id_imagen in enumerate(ids_imagenes):
                imagen_con_datos = {
                    "id_imagen": id_imagen,
                    "created_at": datetime.now(spain_timezone),
                    "classification": classifications[indice]
                }
                imagenes_con_timestamp.append(imagen_con_datos)
        else:
            for id_imagen in ids_imagenes:
                imagen_con_datos = {
                    "id_imagen": id_imagen,
                    "created_at": datetime.now(spain_timezone)
                }
                imagenes_con_timestamp.append(imagen_con_datos)

        resultado = db['subcarpetainternas'].update_one(
            {"nRegistro": nRegistro}, # Filtrar por el nombre único de la carpeta
            {"$push": {"imagenes": {"$each": imagenes_con_timestamp}}} # Agregar imágenes a la lista
        )

        if nRegistro.split("-")[2] == "F":
            resultado = db['subcarpetas'].update_one(
            {"nRegistro": nRegistro}, # Filtrar por el nombre único de la carpeta
            {"$push": {"imagenes": {"$each": imagenes_con_timestamp}}} # Agregar imágenes a la lista
        )

        # Verificar el resultado
        if resultado.matched_count == 0:
            print(f"[ERROR] No se encontró la carpeta para nRegistro: {nRegistro}")
        elif resultado.modified_count > 0:
            print(f"[SUCCESS] Imágenes actualizadas en MongoDB para nRegistro: {nRegistro}")
        else:
            print(f"[INFO] No se modificó el documento para nRegistro: {nRegistro}")

    except Exception as e:
        print(f"Error al actualizar imágenes en MongoDB: {e}")



def renombrar_archivo_drive(servicio, file_id, new_name):
    """
    Renombra un archivo en Google Drive utilizando su ID.

    Args:
        servicio: Objeto autenticado del servicio de Google Drive.
        file_id: ID del archivo que se desea renombrar.
        new_name: Nuevo nombre que se le asignará al archivo.

    Returns:
        dict: Información del archivo renombrado (id y nombre actualizado), o None si falla.
    """
    try:
        # Metadatos para actualizar el nombre del archivo
        file_metadata = {
            "name": new_name
        }

        # Llamada a la API de Google Drive para actualizar el nombre
        archivo_renombrado = servicio.files().update(
            fileId=file_id,
            body=file_metadata,
            fields="id, name"
        ).execute()

        print(f"Archivo renombrado: {archivo_renombrado['name']} (ID: {archivo_renombrado['id']})")
        return {
            "id": archivo_renombrado["id"],
            "nombre": archivo_renombrado["name"]
        }

    except Exception as e:
        print(f"Error al renombrar el archivo con ID {file_id}: {e}")
        return None


def configurar_permisos(servicio, archivo_id):
    """
    Configura los permisos para permitir que cualquier persona con el enlace tenga acceso de lectura.

    :param servicio: Objeto autenticado de la API de Google Drive.
    :param archivo_id: ID del archivo o carpeta en Google Drive.
    """
    try:
        permiso = {
            'type': 'anyone',  # Cualquiera con el enlace
            'role': 'reader'   # Permisos de lectura
        }
        servicio.permissions().create(fileId=archivo_id, body=permiso).execute()
        print(f"Permisos configurados para el archivo/carpeta: {archivo_id}")
    except Exception as e:
        print(f"Error al configurar permisos: {e}")
        raise


init_db()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"mensaje": "API activa y funcionando"}), 200



@app.route('/crear_estructura_completa', methods=['POST'])
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

        archivo = request.files.get('archivo')  # Archivo adjunto (foto)

        if not nombre_principal or cantidad_albumes <= 0:
            return jsonify({"error": "Faltan parámetros requeridos o valores no válidos"}), 400

        servicio = obtener_servicio_drive()

        estructura_creada = crear_estructura_completa(servicio, nombre_principal, cantidad_albumes, cantidad_marcos, cantidad_negativos)
        print("Estructura creada para MongoDB:", estructura_creada)

        # Obtener la subcarpeta con el nombre `nRegistro + "-F"`
        nRegistro = nombre_principal
        subcarpeta_f_id = None
        for subcarpeta in estructura_creada["subcarpetas"]:
            if subcarpeta["nRegistro"] == f"{nRegistro}-F":
                subcarpeta_f_id = subcarpeta["id_subcarpeta"]
                break

        if not subcarpeta_f_id:
            return jsonify({"error": "No se encontró la subcarpeta '-F' en la estructura creada"}), 404

        # Subir el archivo a la subcarpeta '-F'
        if archivo:
            resultado_subida = subir_archivo(servicio, archivo, subcarpeta_f_id, nRegistro)
            print("Archivo subido a la subcarpeta '-F':", resultado_subida)
        else:
            return jsonify({"error": "No se proporcionó un archivo para subir"}), 400

        if crear_estructura_en_mongodb(db, estructura_creada):
            print("Estructura creada en MongoDB. Ahora actualizando imágenes...")
            
            # Actualizar imágenes en MongoDB
            if resultado_subida:
                actualizar_imagenes_en_mongo(db, f"{nRegistro}-F", [resultado_subida["id"]])
                print(f"Actualizando MongoDB para nRegistro: {nRegistro}-F con ID {resultado_subida['id']}")
            
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
        
        # Iterar sobre los archivos y extraer el nombre original
        contador = 1
        for archivo in archivos:
            # Cambio de nombre
            nuevo_nombre = f"{nRegistro}-{contador:03}"
            print(f"Nuevo nombre del archivo: {nuevo_nombre}")
            contador += 1


        # Inicializar classifications para evitar errores
        classifications = []
            # Clasificación de imágenes
        if nRegistro.split("-")[2] == "S":
            classifications = clasificacion(archivos)  

        # Obtener el ID de dicha carpeta
        subcarpetas_internas_id = obtener_id_subcarpeta(db, nRegistro)
        if not subcarpetas_internas_id:
            return jsonify({"error": f"No se encontró subcarpetas_internas_id para nRegistro: {nRegistro}"}), 404
        
        # Autenticar en Google Drive
        servicio = obtener_servicio_drive()

        # Subir los archivos
        archivos_subidos = subir_multiples_archivos(servicio, archivos, subcarpetas_internas_id, nRegistro)

        # Extraer IDs y nombres de los archivos subidos para la respuesta
        # Manejar los IDs y nombres
        ids_y_nombres = []
        if nRegistro.split("-")[2] == "S":
            for indice, archivo in enumerate(archivos_subidos):
                if isinstance(archivo, dict) and "id" in archivo and "nombre" in archivo:
                    ids_y_nombres.append({
                        "id": archivo["id"],
                        "nombre": nuevo_nombre + "-" + classifications[indice]
                    })
                else:
                    print(f"Archivo con formato inesperado: {archivo}")
        else:
            for archivo in archivos_subidos:
                    ids_y_nombres.append({
                        "id": archivo["id"],
                        "nombre": nuevo_nombre
                    })
        
        # Actualizar la colección subcarpetainternas en MongoDB
        actualizar_imagenes_en_mongo(db, nRegistro, ids_y_nombres)

        # Iterar sobre los archivos para renombrarlos
        for archivo in ids_y_nombres:
            if "id" in archivo and "nombre" in archivo:
                try:
                    renombrado = renombrar_archivo_drive(servicio, archivo["id"], archivo["nombre"])
                    if renombrado:
                        print(f"Archivo renombrado con éxito: {renombrado}")
                    else:
                        print(f"No se pudo renombrar el archivo con ID {archivo['id']}")
                except Exception as e:
                    print(f"Error al renombrar el archivo con ID {archivo['id']}: {e}")
            else:
                print(f"Archivo con datos incompletos: {archivo}")

        return jsonify({
            "mensaje": "Archivos subidos con éxito",
            "archivos_subidos": ids_y_nombres

        }), 200
        
    except Exception as e:
        print(f"Error en el endpoint: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500



@app.route('/listar_archivos', methods=['GET'])
def listar_archivos():
    """
    Lista los archivos de una carpeta específica en Google Drive.
    """
    try:
        # Obtener el ID de la carpeta desde los parámetros de la solicitud
        nRegistro = request.args.get('nRegistro')
        if not nRegistro:
            return jsonify({"error": "Se requiere el ID de la carpeta (nRegistro)"}), 400
        
        # Obtener el ID Drive de dicha carpeta nRegistro
        subcarpetas_internas_id = obtener_id_subcarpeta(db, nRegistro)
        if not subcarpetas_internas_id:
            return jsonify({"error": f"No se encontró subcarpetas_internas_id para nRegistro: {nRegistro}"}), 404

        # Obtener el servicio autenticado de Google Drive
        servicio = obtener_servicio_drive()

        # Listar los archivos dentro de la carpeta
        resultados = servicio.files().list(
            q=f"'{subcarpetas_internas_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, webViewLink, webContentLink)"
        ).execute()

        archivados = resultados.get('files', [])

        # Estructurar la respuesta en un formato amigable para React
        respuesta = []
        for archivo in archivados:
            # Configurar permisos de lectura para "anyone with the link"
            configurar_permisos(servicio, archivo.get('id'))
            respuesta.append({
                "id": archivo.get('id'),
                "nombre": archivo.get('name'),
                "tipo": archivo.get('mimeType'),
                "link_visualizacion": archivo.get('webViewLink'),  # Para vista previa
                "link_descarga": archivo.get('webContentLink')  # Para descargar
            })

        return jsonify({
            "mensaje": "Archivos listados con éxito",
            "archivos": respuesta, 
            "success" : True
        }), 200

    except Exception as e:
        print(f"Error al listar archivos: {e}")
        return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)