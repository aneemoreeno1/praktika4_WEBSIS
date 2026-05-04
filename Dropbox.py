import requests
import urllib
import webbrowser
import socket
import json
import helper
import tkinter as tk
import tkinter.messagebox as mb
import tkinter.simpledialog as sd

app_key = 'r18w75mottayfkk'
app_secret = '688swm3gkgtmh0k'
server_addr = 'localhost'
server_port = 8090
redirect_uri = "http://" + server_addr + ":" + str(server_port)


class Dropbox:
    _access_token = ""
    _path = "/"
    _files = []
    _root = None
    _msg_listbox = None

    def __init__(self, root):
        self._root = root

    def local_server(self):
        # sartu kodea hemen
        base_uri = "https://www.dropbox.com/oauth2/authorize"
        datuak = {
            'client_id': app_key,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
        }
        datuak_kodifikatuta = urllib.parse.urlencode(datuak)
        step2_uri = base_uri + '?' + datuak_kodifikatuta
        webbrowser.open_new(step2_uri)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', 8090))
        server_socket.listen(1)
        print("Stock listening on port 8090")

        client_connection, client_address = server_socket.accept()

        eskaera = client_connection.recv(1024).decode()
        print("Nabigatzailetik ondrengo eskaera jaso da:")
        print(" " + eskaera)
        # eskaeran "auth_code"-a bilatu
        lehenengo_lerroa = eskaera.split('\n')[0]
        aux_auth_code = lehenengo_lerroa.split(' ')[1]
        auth_code = aux_auth_code[7:].split('&')[0]
        print("auth_code: " + auth_code)

        http_response = """\
        HTTP/1.1 200 OK

        <html>
        <head><title>Proba</title></head>
        <body>
        The authentication flow has completed. Close this window.
        </body>
        </html>
        """
        client_connection.sendall(str.encode(http_response))
        client_connection.close()
        server_socket.close()

        return auth_code

    def do_oauth(self):
        print("\nExchange authorization code for refresh and access tokens")
        auth_code = self.local_server()
        # Exchange authorization code for access token
        # sartu kodea hemen
        uria = "https://api.dropboxapi.com/oauth2/token"
        goiburuak = {'Host': 'api.dropboxapi.com',
                     'Content-Type': 'application/x-www-form-urlencoded'}
        datuak = {'client_id': app_key,
                  'client_secret': app_secret,
                  'code': auth_code,
                  'grant_type': 'authorization_code',
                  'redirect_uri': redirect_uri,
                  }
        datuak_kodifikatuta = urllib.parse.urlencode(datuak)
        goiburuak['Content-Length'] = str(len(datuak_kodifikatuta))
        erantzuna = requests.post(uria, headers=goiburuak, data=datuak_kodifikatuta, allow_redirects=False)
        status = erantzuna.status_code
        print(status)
        edukia = erantzuna.text
        print("\nEdukia:")
        print("\n" + edukia)
        edukia_json = json.loads(edukia)
        access_token = edukia_json['access_token']
        print("\naccess_token: " + access_token)
        self._access_token = access_token
        self._root.destroy()

    def list_folder(self, msg_listbox, cursor="", edukia_json_entries=[]):
        if edukia_json_entries is None:
            edukia_json_entries = []

        print("\nListing all folders")

        if cursor == "":
            edukia_json_entries.clear()
            msg_listbox.delete(0, tk.END)

        goiburuak = {
            "Host": 'api.dropboxapi.com',
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }

        if not cursor:
            print("/list_folder")
            uri = "https://api.dropboxapi.com/2/files/list_folder"
            datuak = {
                "path": self._path if self._path != "/" else "",
            }
        else:
            print("/list_folder/continue")
            uri = "https://api.dropboxapi.com/2/files/list_folder/continue"
            datuak = {
                "cursor": cursor
            }

        # Call Dropbox API
        print("\nCalling Dropbox API")
        erantzuna = requests.post(uri, headers=goiburuak, data=json.dumps(datuak), allow_redirects=False)
        edukia = erantzuna.text
        print("\tEdukia:")
        print(edukia)

        print('Processing JSON data structure...')
        edukia_json = json.loads(edukia)
        edukia_json_entries += edukia_json['entries']
        if edukia_json['has_more']:
            self.list_folder(msg_listbox, edukia_json['cursor'], edukia_json_entries)
        else:
            self._files = helper.update_listbox2(msg_listbox, self._path, edukia_json_entries)

    def transfer_file(self, file_path, file_data):
        print("/upload " + file_path)

        # Validar y limpiar file_path
        if not file_path or not isinstance(file_path, str):
            print("Error: file_path is invalid.")
            return

        cleaned_path = file_path if file_path.startswith("/") else "/" + file_path

        uri = "https://content.dropboxapi.com/2/files/upload"
        headers = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps({
                "path": cleaned_path,
                "mode": "add",
                "autorename": True,
                "mute": False,
                "strict_conflict": False
            })
        }

        response = requests.post(uri, headers=headers, data=file_data)
        print("Erantzuna:")
        print(response.text)

    def delete_file(self, file_path):
        print("/delete_file " + file_path)
        uri = "https://api.dropboxapi.com/2/files/delete_v2"
        goiburuak = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }
        datuak = {
            "path": file_path if file_path.startswith("/") else "/" + file_path
        }

        erantzuna = requests.post(uri, headers=goiburuak, data=json.dumps(datuak))
        print("Erantzuna:")
        print(erantzuna.text)

    def create_folder(self, path):
        print("/create_folder " + path)
        uri = "https://api.dropboxapi.com/2/files/create_folder_v2"
        goiburuak = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }
        datuak = {
            "path": "/" + path.lstrip("/"),
            "autorename": False
        }

        erantzuna = requests.post(uri, headers=goiburuak, data=json.dumps(datuak))
        print("Erantzuna:")
        print(erantzuna.text)

    def download_file(self, file_path, destination_path):
        print("/download_file " + file_path)

        # Asegurarse de que file_path empieza con "/"
        if not file_path.startswith("/"):
            file_path = "/" + file_path

        uri = "https://content.dropboxapi.com/2/files/download"
        goiburuak = {
            "Authorization": "Bearer " + self._access_token,
            "Dropbox-API-Arg": json.dumps({"path": file_path})
        }

        response = requests.post(uri, headers=goiburuak)
        if response.status_code == 200:
            with open(destination_path, "wb") as f:
                f.write(response.content)
            print("Fitxategia deskargatua:", destination_path)
        else:
            print("Errorea deskargan:", response.text)

    def get_file_metadata(self, file_path):
        print("/get_metadata " + file_path)
        uri = "https://api.dropboxapi.com/2/files/get_metadata"
        headers = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }
        data = {"path": file_path if file_path.startswith("/") else "/" + file_path}

        response = requests.post(uri, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            metadata = response.json()
            mb.showinfo("Metadatuak", json.dumps(metadata, indent=2))
        else:
            mb.showerror("Errorea", "Ezin izan da metadaturik lortu.")

    def move_file(self, old_path):
        print("/move_file " + old_path)
        new_path = sd.askstring("Aldatu kokapena", "Sartu bide berria (adib: /karpeta/fitxategia.ext):")
        if not new_path:
            return

        uri = "https://api.dropboxapi.com/2/files/move_v2"
        headers = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }
        data = {"from_path": old_path, "to_path": new_path}
        response = requests.post(uri, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            mb.showinfo("Info", "Fitxategia mugitu da.")
        else:
            mb.showerror("Errorea", response.text)

    def rename_file(self, file_path):
        print("/rename_file " + file_path)

        name_only = file_path.split("/")[-1]
        folder_path = "/".join(file_path.split("/")[:-1])

        new_name = sd.askstring("Aldatu izena", "Sartu izen berria:", initialvalue=name_only)
        if not new_name:
            return

        new_path = folder_path + "/" + new_name if folder_path else "/" + new_name

        uri = "https://api.dropboxapi.com/2/files/move_v2"
        headers = {
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json"
        }
        data = {"from_path": file_path, "to_path": new_path}
        response = requests.post(uri, headers=headers, data=json.dumps(data))

        if response.status_code == 200:
            mb.showinfo("Info", "Fitxategia izenez aldatu da.")
        else:
            mb.showerror("Errorea", response.text)