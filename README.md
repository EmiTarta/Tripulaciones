
# 📷 Proyecto Salvem Les Fotos - Clasificación de Imágenes con IA, Google Drive y MongoDB  

## 🌍 **Introducción**  
Este repositorio forma parte del trabajo hecho por parte de los alumnos del Bootcamp de Data Science en el desafío final del curso. 

Junto con los alumnos de las verticales de UX/UI y FullStack, hemos desarrollado una web App para colaborar con el proyecto **Salvem Les Fotos**, una iniciativa de salvaguarda de fotografías por parte de un grupo de alumnos y profesionales egresados de los títulos de Grado y Máster en Conservación y Restauración de Bienes Culturales, y del Grado en Bellas Artes de la Universitat Politècnica de València. 

Esta iniciativa llevó a la creación en la Facultad de Bellas Artes de la Universitat Politècnica de València, de un laboratorio encargado de recoger, limpiar, desinfectar, montar y digitalizar las fotografías familiares y álbumes de los afectados por la riada en Valencia. 

La WebApp busca mejorar el proceso, optimizar recursos, ahorrar tiempos, evitar errores humanos y colaborar desde nuestro lugar con este proyecto. 


## 🎯 **Desafío**  
El objetivo del proyecto es el **desarrollo de una web app** que utilice **modelos de Inteligencia Artificial** para:  
✅ **Restaurar digitalmente fotografías dañadas** por barro y otros contaminantes.  
✅ **Optimizar el proceso de digitalización y registro digital** de las fotografías recibidas en la UPV.  
✅ **Automatizar la organización y almacenamiento en la nube** de las imágenes restauradas.  

Para lograrlo, hemos desarrollado un sistema basado en **Flask**, que integra tecnologías de **Google Drive para almacenamiento, MongoDB para la gestión de datos y Replicate para modelos de IA**.  

Esta API basada en **Flask** permite la gestión de archivos y datos en **MongoDB** y **Google Cloud Storage**, integrando autenticación con credenciales de servicio y capacidades de IA mediante **Replicate API**. Su propósito es facilitar la manipulación de datos en la nube y proporcionar un backend robusto para aplicaciones frontend.

## 📂 Estructura del Proyecto
```
📂 repositorio
│── 📄 app.py            # Código principal de la API
│── 📄 requirements.txt   # Dependencias del proyecto
│── 📄 Dockerfile         # Configuración para contenedor Docker
│── 📄 .env               # Variables de entorno (no incluido en el repo público)
```

## 📡 Endpoints y Funcionalidad

| Método | Endpoint           		| Descripción |
|--------|--------------------		|-------------|
| GET    | `/`                		| Verifica el estado de la API. |
| POST   | `/crear_estructura_completa` | Crea una estructura de carpetas en Drive|
| POST   | `/subir_archivos		| Subir una foto a carpeta Drive y clasificarlo|
| POST   | `/listar_archivos`       	| Lsta los archivos de una carpeta Drive |


## 🐳 **Dockerización y Despliegue en Google Cloud Run**  

Este proyecto fue **dockerizado** para garantizar la **portabilidad, escalabilidad y facilidad de despliegue** en cualquier entorno, sin depender de configuraciones específicas del sistema operativo.  

Mediante **Docker**, logramos:  
✅ **Ejecutar la API en contenedores aislados**, asegurando que todas las dependencias estén correctamente instaladas.  
✅ **Facilitar el despliegue en producción**, eliminando problemas de compatibilidad entre sistemas.  
✅ **Simplificar el desarrollo**, permitiendo que cualquier desarrollador ejecute la aplicación sin configuraciones complejas.  
✅ **Automatizar la infraestructura**, integrando el servicio en arquitecturas escalables con Kubernetes u orquestadores de contenedores.  

---

### 🚀 Despliegue en Google Cloud Run

La API fue desplegada en **Google Cloud Run** para garantizar un acceso rápido, escalable y eficiente a las funciones del backend. Esta elección facilita la integración con el equipo de **Full Stack**, permitiéndoles consumir los servicios sin preocuparse por la infraestructura subyacente.  

Además, **Google Cloud Run** ofrece ventajas clave como:  
✅ **Escalabilidad automática**, ajustando los recursos según la demanda.  
✅ **Integración con otros servicios de Google Cloud**, como Drive y Firestore.  
✅ **Despliegue sin gestionar servidores**, lo que agiliza el mantenimiento y desarrollo.  
✅ **Seguridad y autenticación nativa**, asegurando un entorno confiable para nuestras operaciones.  

Este enfoque ha permitido que el equipo pueda centrarse en la funcionalidad y optimización de la API, sin preocuparse por la administración de servidores.  

---

## 🎯 Conclusiones
Este proyecto proporciona una API robusta y escalable que permite manejar datos de manera eficiente con MongoDB y Google Cloud Storage. Su integración con Replicate API la hace una solución flexible para diversas aplicaciones.

## 💡 Propuestas de Valor
- **Escalabilidad**: Implementación en Google Cloud para alto rendimiento.
- **Flexibilidad**: Soporte para múltiples tipos de datos.
- **Seguridad**: Uso de autenticación con credenciales de Google Cloud.
- **Automatización**: Integración con Docker para despliegues rápidos.

## 🛠 Tecnologías Utilizadas
- **Python** con Flask como framework backend.
- **MongoDB** como base de datos NoSQL.
- **Google Drive API** para almacenamiento de archivos.
- **Replicate API** para procesamiento de datos con IA.
- **Docker** para contenerización y despliegue.
- **Google Cloud Run** para escalabilidad en la nube.

---
## 📜 **Licencia**  
Este proyecto está bajo la licencia **MIT**. ¡Eres libre de usarlo y modificarlo! 🎉  
