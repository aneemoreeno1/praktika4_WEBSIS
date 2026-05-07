import tkinter as tk

import requests
from Dropbox import Dropbox

def test_connection(self):
    headers = {
        "Authorization": "Bearer " + self._access_token
    }

    r = requests.post(
        "https://api.dropboxapi.com/2/users/get_current_account",
        headers=headers
    )

    print("STATUS:", r.status_code)
    print("HEADERS:", r.headers)
    print("BODY:", r.text)


root = tk.Tk()
root.title("Dropbox")

listbox = tk.Listbox(root, width=60, height=20)

root.update()

dbx = Dropbox(root)
root.withdraw()
dbx.do_oauth()

#listbox.pack() #es necesario para el list_folder
#root.deiconify()
#dbx.list_folder(listbox)

#dbx.transfer_file("WS%20Planifikazioa%202025-26.pdf") #Nombre del fichero a subir

#dbx.delete_file("/WS%20Planifikazioa%202025-26.pdf") #Path

#dbx.create_folder("Prueba") #Path

#dbx.delete_file("/Prueba") #Path

#dbx.download_file("/websis/WS_Aurkezpena.pdf", "WS_Aurkezpena.pdf") #Path en Dropbox, path local

#dbx.get_file_metadata("/websis/WS_Aurkezpena.pdf") #Path en Dropbox

#dbx.move_file("/websis/WS_Aurkezpena.pdf") #Path origen, se abre una ventana para introducir el path destino

dbx.rename_file("/Get Started with Dropbox Paper.url")

root.mainloop()

print("TOKEN:", dbx._access_token[:20])