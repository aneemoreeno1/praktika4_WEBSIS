# -*- coding: UTF-8 -*-
from tkinter import messagebox
import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup
import time
import helper

NOMBRE_ASIGNATURA = "Web Sistemak"

class eGela:
    _login = 0
    _cookie = ""
    _curso = ""
    _refs = []
    _root = None
    _session = None

    def __init__(self, root):
        self._root = root
        self._session = requests.Session()

    def check_credentials(self, username, password, event=None):
        popup, progress_var, progress_bar = helper.progress("check_credentials", "Logging into eGela...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("##### 1. PETICION #####")
        uri = "https://egela.ehu.eus/login/index.php"

        respuesta1 = self._session.get(uri)
        print(f"\tGET {uri} -> {respuesta1.status_code}")

        pagina_login = BeautifulSoup(respuesta1.text, 'html.parser')
        campo_token = pagina_login.find('input', {'name': 'logintoken'})
        logintoken = campo_token['value']
        print(f"\tlogintoken: {logintoken[:8]}...")

        progress = 25
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)

        print("\n##### 2. PETICION #####")
        campos_formulario = {
            'logintoken': logintoken,
            'username':   username,
            'password':   password,
            'anchor':     ''
        }
        respuesta2 = self._session.post(uri, data=campos_formulario, allow_redirects=False)
        print(f"\tPOST {uri} -> {respuesta2.status_code}")

        url_redireccion = respuesta2.headers.get('Location', '')
        print(f"\tRedireccion -> {url_redireccion}")

        progress = 50
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)

        print("\n##### 3. PETICION #####")
        respuesta3 = self._session.get(url_redireccion, allow_redirects=False)
        print(f"\tGET {url_redireccion} -> {respuesta3.status_code}")

        url_inicio = respuesta3.headers.get('Location', 'https://egela.ehu.eus/my/')
        print(f"\tSiguiente -> {url_inicio}")

        progress = 75
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)

        print("\n##### 4. PETICION #####")
        respuesta4 = self._session.get(url_inicio, allow_redirects=True)
        print(f"\tGET {url_inicio} -> {respuesta4.status_code}")

        progress = 100
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)
        popup.destroy()

        # Comprobar login: Moodle anade data-userid al body si hay sesion activa
        sesion_ok = 'data-userid' in respuesta4.text

        if sesion_ok:
            self._login = 1
            self._cookie = dict(self._session.cookies)

            # Buscar la URL del curso en la pagina de inicio
            soup_inicio = BeautifulSoup(respuesta4.text, 'html.parser')
            enlace_curso = soup_inicio.find(
                'a',
                href=lambda h: h and 'course/view.php' in h,
                string=lambda t: t and NOMBRE_ASIGNATURA in t
            )
            if enlace_curso:
                self._curso = enlace_curso['href']
                print(f"\tCurso encontrado: {self._curso}")
            else:
                print("\tAviso: no se encontro el enlace del curso en la pagina de inicio.")

            self._root.destroy()
        else:
            messagebox.showinfo("Alert Message", "Login incorrect!")

    def get_pdf_refs(self):
        popup, progress_var, progress_bar = helper.progress("get_pdf_refs", "Downloading PDF list...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("\n##### 5. PETICION (Pagina principal de la asignatura en eGela) #####")
        respuesta_curso = self._session.get(self._curso)
        print(f"\tGET {self._curso} -> {respuesta_curso.status_code}")

        print("\n##### Analisis del HTML... #####")
        soup_curso = BeautifulSoup(respuesta_curso.text, 'html.parser')

        # Buscar todos los enlaces a recursos Moodle (PDFs)
        enlaces = soup_curso.find_all(
            'a',
            href=lambda h: h and '/mod/resource/view.php' in h
        )

        # Eliminar duplicados manteniendo el orden de aparicion
        urls_vistas = set()
        recursos_unicos = []
        for enlace in enlaces:
            url = enlace['href']
            if url not in urls_vistas:
                urls_vistas.add(url)
                recursos_unicos.append(enlace)

        self._refs = []
        progress_step = float(100.0 / len(recursos_unicos)) if recursos_unicos else 100

        for enlace in recursos_unicos:
            url_recurso = enlace['href']
            nombre = enlace.get_text(strip=True)
            if nombre:
                self._refs.append({
                    'pdf_name': nombre,
                    'pdf_url':  url_recurso
                })
                print(f"\tRecurso encontrado: {nombre}")

            progress += progress_step
            progress_var.set(progress)
            progress_bar.update()
            time.sleep(0.1)

        popup.destroy()
        return self._refs

    def get_pdf(self, ref):
        print("\t##### descargando PDF... #####")
        url_recurso = ref['pdf_url']

        # Acceder a la pagina del recurso en Moodle
        respuesta_recurso = self._session.get(url_recurso, allow_redirects=True)

        # Moodle expone el enlace real en un div resourceworkaround
        soup_recurso = BeautifulSoup(respuesta_recurso.text, 'html.parser')
        div_workaround = soup_recurso.find('div', class_='resourceworkaround')

        if div_workaround:
            enlace_pdf = div_workaround.find('a')
            url_pdf = enlace_pdf['href']
        else:
            # Moodle puede redirigir directamente al fichero
            url_pdf = respuesta_recurso.url

        respuesta_pdf = self._session.get(url_pdf, allow_redirects=True)
        nombre_pdf = unquote(url_pdf.split('/')[-1])
        print(f"\tPDF descargado: {nombre_pdf} ({len(respuesta_pdf.content)} bytes)")

        return nombre_pdf, respuesta_pdf.content
