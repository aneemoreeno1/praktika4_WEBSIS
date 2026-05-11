# -*- coding: UTF-8 -*-
from tkinter import messagebox

import bs4
import requests
from urllib.parse import unquote

import soup

from bs4 import BeautifulSoup
import time
import helper

NOMBRE_ASIGNATURA = "Web Sistemak"

class eGela:
    _login = 0
    _cookie = ""
    _curso = ""
    _refs = {}
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
        metodoa = 'GET'
        uri = "https://egela.ehu.eus/login/index.php"

        r1 = requests.request(metodoa, uri, allow_redirects=False)

        print(f"1. Eskaera:\n\t{metodoa} {uri}")
        print(f"1. Erantzuna:\n\t{r1.status_code} {r1.reason}")
        if 'Set-Cookie' in r1.headers: print(f"\tSet-Cookie: {r1.headers['Set-Cookie']}")

        MoodleSaioa = r1.headers['Set-Cookie'].split('MoodleSessionegela=')[1].split(';')[0]
        login_tokena = r1.text.split('logintoken" value="')[1].split('"')[0]

        progress = 25
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)

        print("\n##### 2. PETICION #####")

        metodoa = 'POST'
        goiburuak = {'Cookie': f'MoodleSessionegela={MoodleSaioa}'}
        gorputza = {'username': username, 'password': password, 'logintoken': login_tokena}
        r2 = requests.request(metodoa, uri, headers=goiburuak, data=gorputza, allow_redirects=False)
        # Ez printeatzeko password-a
        gorputza_debug = {
            'username': username,
            'password': '********',
            'logintoken': login_tokena
        }
        print(f"2. Eskaera:\n\t{metodoa} {uri}\n\t{gorputza_debug}")

        print(f"2. Erantzuna:\n\t{r2.status_code} {r2.reason}")
        if 'Location' in r2.headers: print(f"\tLocation: {r2.headers['Location']}")

        if 'Set-Cookie' in r2.headers:
            MoodleSaioa = r2.headers['Set-Cookie'].split('MoodleSessionegela=')[1].split(';')[0]

        progress = 50
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)


        print("\n##### 3. PETICION #####")
        metodoa = 'GET'
        uri = r2.headers['Location']
        goiburuak = {'Cookie': f'MoodleSessionegela={MoodleSaioa}'}
        r3 = requests.request(metodoa, uri, headers=goiburuak, allow_redirects=False)

        print(f"3. Eskaera:\n\t{metodoa} {uri}")
        print(f"3. Erantzuna:\n\t{r3.status_code} {r3.reason}")
        if 'Location' in r3.headers: print(f"\tLocation: {r3.headers['Location']}")

        progress = 75
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)


        print("\n##### 4. PETICION #####")
        uri = r3.headers['Location']
        r4 = requests.request('GET', uri, headers=goiburuak, allow_redirects=False)

        sesion_ok = 'data-userid' in r4.text

        if sesion_ok:
            print("Kautotze zuzena.")
        else:
            print("Errorea: Login-ak huts egin du.")
            exit(1)

        progress = 100
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(1)
        popup.destroy()


        # Comprobar login: Moodle añade data-userid al body si hay sesion activa
        sesion_ok = 'data-userid' in r4.text

        if sesion_ok:
            self._login = 1
            self._cookie = MoodleSaioa

            # Buscar la URL del curso en la pagina de inicio
            soup_inicio = BeautifulSoup(r4.text, 'html.parser')
            enlace_curso = soup_inicio.find(
                'a',
                href=lambda h: h and 'course/view.php' in h,
                string=lambda t: t and NOMBRE_ASIGNATURA in t
            )

            if enlace_curso:
                self._curso = enlace_curso['href']
                print(f"\tCurso encontrado: {self._curso}")
                metodoa = 'GET'
                uri = self._curso + '&sesion=0'

                MoodleSaioa = self._cookie
                goiburuak = {
                    'Cookie': f'MoodleSessionegela={MoodleSaioa}'
                }

                atal_hauts = {}

                erantzuna_atalak = requests.request(
                    metodoa,
                    uri,
                    headers=goiburuak,
                    allow_redirects=False
                )

                if erantzuna_atalak.status_code == 200:

                    soup = BeautifulSoup(erantzuna_atalak.text, 'html.parser')

                    if soup.find('ul',class_='nav nav-tabs mb-3') is None:
                        atal_hauts[NOMBRE_ASIGNATURA] = self._curso

                    else:
                        ul = soup.find('ul',class_='nav nav-tabs mb-3')
                        lis = ul.find_all('li')

                        for li in lis:

                            a = li.find('a')

                            if a.has_attr('href'):
                                atal_hauts[a['title']] = a['href']

                            else:
                                atal_hauts[a['title']] = (
                                    self._curso + '&section=0#tabs-tree-start'
                                )
                print("\nAtalak aurkituta:")
                for izena, esteka in atal_hauts.items():
                    print(f" - {izena}: {esteka}")
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

        print("\n##### 5. PETICION (Página principal de la asignatura en eGela) #####")
        #############################################
        #  HTTP ESKAERA IKASGAIAREN ORRIRA
        #############################################
        headers = {
             'Cookie': f'MoodleSessionegela={self._cookie}'
        }

        response = requests.get(
            self._curso,
            headers=headers,
            allow_redirects=True
        )
        if response.status_code != 200:
            popup.destroy()
            raise Exception("Error accediendo a la página de eGela")

        soup = bs4.BeautifulSoup(response.text, 'html.parser')

        print("\n##### Analisis del HTML... #####")

        #############################################
        # PDF BUSQUEDA
        #############################################
        pdfs = soup.find_all('li', class_='modtype_resource')

        if len(pdfs) == 0:
            popup.destroy()
            return self._refs

        progress_step = float(100.0 / len(pdfs))

        for pdf in pdfs:
            img = pdf.find('img')
            a = pdf.find('a')

            if not img or not a:
                continue

            src_img = img.get('src', '')

            # Solo PDFs
            if 'pdf' in src_img:

                pdf_url = a['href']

                pdf_name = (
                    a.find('span', class_='instancename')
                    .text
                    .split(' Fitxategi')[0]
                    .strip()
                )

                self._refs[pdf_name] = pdf_url

                print(f"\tPDF encontrado: {pdf_name}")

                progress += progress_step
                progress_var.set(progress)
                progress_bar.update()

                time.sleep(0.1)

        popup.destroy()

        return self._refs

    def get_pdf(self, selection):

        print("\t##### descargando  PDF... #####")

        #############################################
        # DESCARGAR PDFS SELECCIONADOS
        #############################################

        pdf_url = self._refs.get(selection)
        if not pdf_url:
            raise Exception("Referencia al PDF no encontrada")

        if self._cookie:
            self._session.cookies.update({'MoodleSessionegela': self._cookie})

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/115.0 Safari/537.36',
            'Referer': self._curso if self._curso else pdf_url
        }

        last_exc = None
        for intento in range(3):
            try:
                response = self._session.get(pdf_url, headers=headers, allow_redirects=True, timeout=30)
            except requests.RequestException as exc:
                last_exc = exc
                print(f"\tIntento {intento+1}: error de red: {exc}")
                time.sleep(1)
                continue

            try:
                print(f"\tIntento {intento+1}: URL final: {response.url}")
                print(f"\tIntento {intento+1}: estado HTTP {response.status_code}")
                if response.history:
                    print(f"\tHistorial ({len(response.history)} redirecciones):")
                    for h in response.history:
                        print(f"\t - {h.status_code} -> {h.url}")
            except Exception:
                pass

            if response.status_code != 200:
                last_exc = Exception(f"HTTP {response.status_code}")
                time.sleep(1)
                continue

            pdf_content = response.content
            if not pdf_content:
                last_exc = Exception("Contenido vacío al descargar PDF")
                time.sleep(1)
                continue

            # Mostrar Content-Type para ayudar a depuración
            try:
                print(f"\tContent-Type: {response.headers.get('Content-Type')}")
            except Exception:
                pass

            pdf_name = selection.replace('/', '_') + ".pdf"
            return pdf_name, pdf_content

        # Si fallaron los intentos
        if last_exc:
            raise Exception(f"Error descargando el PDF: {last_exc}")
        else:
            raise Exception("Error desconocido descargando el PDF")

