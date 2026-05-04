from tkinter import messagebox as tkMessageBox
import requests
import urllib
from bs4 import BeautifulSoup
import time
import helper
import re

class eGela:
    _login = 0
    _cookiea = ""
    _ikasgaia = ""
    _refs = []
    _root = None

    def __init__(self, root):
        self._root = root

    def get_logintoken(self, html):
        match = re.search(r'name="logintoken" value="(.*?)"', html)
        return match.group(1) if match else None

    def bilatu_ikasgaia(self, html, ikasgai_izena):
        patroia = r'<div class="w-100">(.*?)</div>'
        coincidencias = re.findall(patroia, html, re.DOTALL)
        for coincidencia in coincidencias:
            if ikasgai_izena in coincidencia:
                ona = coincidencia
                textua = ona.split(" class=")[0]
                uria = textua.split("\"")[1]
                print('Ikasgaiaren uria: ' + uria)
                return (uria)


    def check_credentials(self, username, password, event=None):
        popup, progress_var, progress_bar = helper.progress("check_credentials", "Logging into eGela...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("##### 1. ESKAERA (Login inprimakia lortu 'logintoken' ateratzeko #####")
        metodoa0 = 'GET'
        uria0 = "https://egela.ehu.eus/"
        goiburuak0 = {'Host': 'egela.ehu.eus'}
        erantzuna0 = requests.request(metodoa0, uria0, headers=goiburuak0, allow_redirects=False)
        login_url = erantzuna0.headers['Location']

        erantzuna1 = requests.get(login_url, headers=goiburuak0, allow_redirects=False)
        moodle_session = erantzuna1.headers['Set-Cookie'].split(";")[0]
        logintoken = self.get_logintoken(erantzuna1.text)

        progress = 25
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(0.1)

        print("\n##### 2. ESKAERA (Kautotzea -datu bidalketa-) #####")
        metodoa2 = 'POST'
        goiburuak2 = {
            'Host': 'egela.ehu.eus',
            'Cookie': moodle_session,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        datuak = 'logintoken=' + logintoken + '&username=' + username + '&password=' + password
        erantzuna2 = requests.request(metodoa2, login_url, headers=goiburuak2, data=datuak, allow_redirects=False)
        moodle_session = erantzuna2.headers['Set-Cookie'].split(";")[0]
        testsession = "testsession=" + erantzuna2.headers['Location'].split("testsession=")[1]

        progress = 50
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(0.1)

        print("\n##### 3. ESKAERA (berbidalketa) #####")
        uria3 = login_url + '?' + testsession
        goiburuak3 = {'Host': 'egela.ehu.eus', 'Cookie': moodle_session}
        erantzuna3 = requests.get(uria3, headers=goiburuak3, allow_redirects=False)
        uria4 = erantzuna3.headers['Location']

        progress = 75
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(0.1)

        print("\n##### 4. ESKAERA (eGelako orrialde nagusia) #####")
        metodoa4 = 'GET'
        goiburuak4 = {'Host': 'egela.ehu.eus', 'Cookie': moodle_session}
        erantzuna4 = requests.request(metodoa4, uria4, headers=goiburuak4, allow_redirects=False)

        progress = 100
        progress_var.set(progress)
        progress_bar.update()
        time.sleep(0.1)
        popup.destroy()

        print("\n##### LOGIN EGIAZTAPENA #####")

        text_clean = erantzuna4.content.decode('utf-8')
        if f"Kaixo, " in text_clean:
            self._login = 1
            self._cookiea = moodle_session
            self._ikasgaia = self.bilatu_ikasgaia(text_clean, 'Web Sistemak')
            self._root.destroy()
        else:
            tkMessageBox.showinfo("Alert Message", "Login incorrect!")

    def get_pdf_refs(self):
        popup, progress_var, progress_bar = helper.progress("get_pdf_refs", "Downloading PDF list...")
        progress = 0
        progress_var.set(progress)
        progress_bar.update()

        print("\n##### 5. ESKAERA (Ikasgairen eGelako orrialdea) #####")
        metodoa5 = 'GET'
        uria5 = self._ikasgaia
        goiburuak5 = {'Host': 'egela.ehu.eus', 'Cookie': self._cookiea}
        erantzuna5 = requests.request(metodoa5, uria5, headers=goiburuak5, allow_redirects=False)

        print("\n##### HTML-aren azterketa... #####")
        soup = BeautifulSoup(erantzuna5.content, 'html.parser')
        pdf_links = soup.find_all(
            'a',
            class_="aalink stretched-link",
            href=lambda x: x and "/mod/resource/view" in x,
            onclick=lambda x: x and "window.open" in x
        )

        self._refs = []

        for link in pdf_links:
            url = link["href"]
            erantzuna_pdf = requests.request('GET', url, headers={'Host': 'egela.ehu.eus', 'Cookie': self._cookiea},
                                             allow_redirects=True)
            erantzuna_soup = BeautifulSoup(erantzuna_pdf.content, 'html.parser')
            a_tag = erantzuna_soup.find('div', class_='resourceworkaround').find('a')
            pdf_url = a_tag["href"]
            print(pdf_url)
            pdf = requests.get(pdf_url, headers={'Host': 'egela.ehu.eus', 'Cookie': self._cookiea}, allow_redirects=True)
            pdf_izena = pdf_url.split("/")[-1]
            with open(pdf_izena, 'wb') as f:
                f.write(pdf.content)
            print(pdf_izena)

            self._refs.append({'pdf_name': pdf_izena, 'pdf_link': pdf_url})

        progress_step = float(100.0 / len(self._refs)) if self._refs else 100
        for _ in self._refs:
            progress += progress_step
            progress_var.set(progress)
            progress_bar.update()
            time.sleep(0.1)

        print(self._refs)
        popup.destroy()
        return self._refs

    def get_pdf(self, selection):
        print("##### PDF-a deskargatzen... #####")

        pdf_name = selection['pdf_name']
        pdf_link = selection['pdf_link']

        metodoa = 'GET'
        goiburuak = {'Host': 'egela.ehu.eus', 'Cookie': self._cookiea}
        erantzuna = requests.get(pdf_link, headers=goiburuak, allow_redirects=True)

        if erantzuna.status_code == 200:
            pdf_file = erantzuna.content
        else:
            print("Errorea PDF deskargatzean:", erantzuna.status_code)
            return None, None

        return pdf_name, pdf_file
