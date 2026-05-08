import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import webbrowser
import json
import tkinter.simpledialog as simpledialog
from socket import AF_INET, socket, SOCK_STREAM
import helper

# Sesion con reintentos automaticos para conexiones a content.dropboxapi.com
def _crear_sesion_con_reintentos():
    sesion = requests.Session()
    reintentos = Retry(total=3, backoff_factor=1,
                       status_forcelist=[500, 502, 503, 504])
    adaptador = HTTPAdapter(max_retries=reintentos)
    sesion.mount("https://", adaptador)
    return sesion

_sesion_dropbox = _crear_sesion_con_reintentos()

app_key    = 'np3zn4jlp5gbp73'
app_secret = 'cn16mx5lmtujfx5'
server_addr = "localhost"
server_port  = 8090
redirect_uri = "http://" + server_addr + ":" + str(server_port)

class Dropbox:
    _access_token = ""
    _path  = "/"
    _files = []
    _root  = None
    _msg_listbox = None

    def __init__(self, root):
        self._root = root

    # ------------------------------------------------------------------ #
    #  Servidor local que captura el codigo de autorizacion de Dropbox    #
    # ------------------------------------------------------------------ #
    def local_server(self):
        # Abrir navegador con la URL de autorizacion de Dropbox
        parametros = {
            'client_id':     app_key,
            'redirect_uri':  redirect_uri,
            'response_type': 'code',
            'token_access_type': 'offline'
        }
        url_auth = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode(parametros)
        webbrowser.open(url_auth)
        print(f"\tNavegador abierto: {url_auth}")

        # Escuchar la redireccion del navegador
        servidor = socket(AF_INET, SOCK_STREAM)
        servidor.bind((server_addr, server_port))
        servidor.listen(1)
        print(f"\tServidor local escuchando en el puerto {server_port}...")

        conexion, direccion = servidor.accept()
        peticion = conexion.recv(1024).decode('UTF-8')
        print("\tPeticion recibida del navegador:")
        print(peticion)

        # Extraer el codigo de la primera linea: GET /?code=XXXX HTTP/1.1
        primera_linea  = peticion.split('\n')[0]
        ruta           = primera_linea.split(' ')[1]          # /?code=XXXX&...
        codigo_auth    = ruta[7:].split('&')[0]               # quitar "/?code="
        print(f"\tcodigo_auth: {codigo_auth}")

        respuesta_http = (
            "HTTP/1.1 200 OK\r\n\r\n"
            "<html><head><title>Dropbox Auth</title></head>"
            "<body>Autorizacion completada. Puedes cerrar esta ventana.</body></html>"
        )
        conexion.sendall(respuesta_http.encode('utf-8'))
        conexion.close()
        servidor.close()

        return codigo_auth

    # ------------------------------------------------------------------ #
    #  Intercambio del codigo por el access token                         #
    # ------------------------------------------------------------------ #
    def do_oauth(self):
        print("\n/oauth2/token - Intercambio de codigo por access token")
        codigo_auth = self.local_server()

        uri_token = "https://api.dropboxapi.com/oauth2/token"
        datos_token = {
            'code':         codigo_auth,
            'grant_type':   'authorization_code',
            'client_id':    app_key,
            'client_secret': app_secret,
            'redirect_uri': redirect_uri
        }

        respuesta = requests.post(uri_token, data=datos_token)
        print(f"\tPOST {uri_token} -> {respuesta.status_code}")

        datos_json = respuesta.json()
        self._access_token = datos_json['access_token']
        print(f"\taccess_token obtenido: {self._access_token[:10]}...")

        self._root.destroy()

    # ------------------------------------------------------------------ #
    #  Listar contenido de la carpeta actual                              #
    # ------------------------------------------------------------------ #
    def list_folder(self, msg_listbox):
        print("/list_folder")
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }

        # La API de Dropbox usa "" para la raiz, no "/"
        ruta_api = "" if self._path == "/" else self._path
        cuerpo   = {"path": ruta_api, "recursive": False}

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/list_folder',
            headers=cabeceras,
            json=cuerpo
        )
        datos_json = respuesta.json()
        print(f"\tEntradas recibidas: {len(datos_json.get('entries', []))}")

        # Acumular si hay mas paginas (bucle, no recursion)
        todas_entradas = list(datos_json.get('entries', []))
        while datos_json.get('has_more', False):
            print("\t/list_folder/continue ...")
            respuesta = requests.post(
                'https://api.dropboxapi.com/2/files/list_folder/continue',
                headers=cabeceras,
                json={"cursor": datos_json['cursor']}
            )
            datos_json = respuesta.json()
            todas_entradas.extend(datos_json.get('entries', []))

        # helper.update_listbox2 espera {'entries': [...]}
        resultado = {'entries': todas_entradas}
        self._files = helper.update_listbox2(msg_listbox, self._path, resultado)

    # ------------------------------------------------------------------ #
    #  Subir un fichero a Dropbox                                         #
    # ------------------------------------------------------------------ #
    def transfer_file(self, file_path, file_data):
        print("/upload " + file_path)
        argumentos_api = {
            "path":            file_path,
            "mode":            "add",
            "autorename":      True,
            "mute":            False,
            "strict_conflict": False
        }
        cabeceras = {
            "Authorization":  "Bearer " + self._access_token,
            "Content-Type":   "application/octet-stream",
            "Dropbox-API-Arg": json.dumps(argumentos_api)
        }

        respuesta = requests.post(
            'https://content.dropboxapi.com/2/files/upload',
            headers=cabeceras,
            data=file_data
        )
        print(f"\tSubida completada: {respuesta.status_code}")

    # ------------------------------------------------------------------ #
    #  Borrar un fichero o carpeta en Dropbox                             #
    # ------------------------------------------------------------------ #
    def delete_file(self, file_path):
        print("/delete_v2 " + file_path)
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/delete_v2',
            headers=cabeceras,
            json={"path": file_path}
        )
        print(f"\tBorrado: {respuesta.status_code}")

    # ------------------------------------------------------------------ #
    #  Crear una carpeta en Dropbox                                       #
    # ------------------------------------------------------------------ #
    def create_folder(self, path):
        print("/create_folder_v2 " + path)
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/create_folder_v2',
            headers=cabeceras,
            json={"path": path, "autorename": False}
        )
        print(f"\tCarpeta creada: {respuesta.status_code}")

    # ------------------------------------------------------------------ #
    #  Descargar un fichero de Dropbox al disco local                     #
    # ------------------------------------------------------------------ #
    def download_file(self, file_path, destination_path):
        print("/download " + file_path)
        cabeceras = {
            "Authorization":   "Bearer " + self._access_token,
            "Dropbox-API-Arg": json.dumps({"path": file_path})
        }

        try:
            # Timeout: 10 s para conectar, 30 s para leer
            respuesta = _sesion_dropbox.post(
                'https://content.dropboxapi.com/2/files/download',
                headers=cabeceras,
                timeout=(10, 30)
            )
            if respuesta.status_code == 200:
                with open(destination_path, 'wb') as fichero:
                    fichero.write(respuesta.content)
                print(f"\tFichero guardado en: {destination_path}")
            else:
                print(f"\tError en descarga ({respuesta.status_code}): {respuesta.text}")
        except requests.exceptions.ConnectTimeout:
            print(f"\tTimeout al conectar con Dropbox para '{file_path}'. Reintenta en un momento.")
        except requests.exceptions.RequestException as exc:
            print(f"\tError de red en download_file: {exc}")

    # ------------------------------------------------------------------ #
    #  Obtener metadatos de un fichero                                    #
    # ------------------------------------------------------------------ #
    def get_file_metadata(self, file_path):
        print("/get_metadata " + file_path)
        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/get_metadata',
            headers=cabeceras,
            json={"path": file_path}
        )
        if respuesta.status_code == 200:
            metadatos = respuesta.json()
            print(json.dumps(metadatos, indent=2))
        else:
            print(f"\tError al obtener metadatos: {respuesta.text}")

    # ------------------------------------------------------------------ #
    #  Mover un fichero a otra ruta                                       #
    # ------------------------------------------------------------------ #
    def move_file(self, file_path):
        print("/move_v2 " + file_path)
        ruta_destino = simpledialog.askstring(
            "Mover fichero",
            "Introduce la ruta destino (ej: /carpeta/fichero.pdf):"
        )
        if not ruta_destino:
            return

        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }
        cuerpo = {"from_path": file_path, "to_path": ruta_destino}

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/move_v2',
            headers=cabeceras,
            json=cuerpo
        )
        print(f"\tMovido: {respuesta.status_code}")

    # ------------------------------------------------------------------ #
    #  Renombrar un fichero                                               #
    # ------------------------------------------------------------------ #
    def rename_file(self, file_path):
        print("/move_v2 (rename) " + file_path)
        nombre_actual  = file_path.split('/')[-1]
        carpeta_padre  = '/'.join(file_path.split('/')[:-1]) or '/'

        nuevo_nombre = simpledialog.askstring(
            "Renombrar fichero",
            "Introduce el nuevo nombre:",
            initialvalue=nombre_actual
        )
        if not nuevo_nombre:
            return

        ruta_destino = carpeta_padre.rstrip('/') + '/' + nuevo_nombre

        cabeceras = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type":  "application/json"
        }
        cuerpo = {"from_path": file_path, "to_path": ruta_destino}

        respuesta = requests.post(
            'https://api.dropboxapi.com/2/files/move_v2',
            headers=cabeceras,
            json=cuerpo
        )
        print(f"\tRenombrado: {respuesta.status_code}")
