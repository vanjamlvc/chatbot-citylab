import os
import re
from urllib.robotparser import RobotFileParser
import json
from typing import Optional
from urllib.parse import \
    urljoin  # Für die Konvertierung von relativen zu absoluten URLs
from urllib.parse import urlparse

import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup


# Web Scraper Klasse
class WebScraper:
    def __init__(self, keywords:list, max_depth:int=2):
        self._base_url = None # erste Adresse die vom Scraper aufgerufen wird (die der Methode scrape übergeben wird)
        self.keywords = keywords # Liste der Stichwörter nach denen im html der aufgerufenen Seiten gesucht wird
        self.visited_urls = set()  # Um bereits besuchte URLs zu tracken
        self.max_depth = max_depth  # Maximale Tiefe der Verlinkungen
        self.extracted_texts = set()  # Set zum Vermeiden von doppelten Texten
        self.results = []  # Liste für die Ergebnisse (für DataFrame)
        self.useragent = "BerlinSummerSchool2024WebScraper/0.1"
        self.robot_parser_cache = {} # dict der gecachten robots.txt 
        self.siteshtml = {} # dict der html body der besuchten Seiten


    # Funktion zum Abrufen und Parsen der Seite
    def fetch_page(self, url:str) -> Optional[str]:
        """
        tries to open the given url and returns the content as string
        
        Parameters
        ----------
        url : str
            Uniform Resource Locator with which an attempt is made to call up content
        """

        try:
            headers = {"User-Agent" : self.useragent}
            response = requests.get(url, headers= headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Fehler beim Abrufen der Seite: {e}")
            return None
        

    # Funktion zum Finden der Keywords im Text
    def search_keywords(self, text:str) -> bool:
        """
        checks whether one of the keywords given to the web scraper occurs in the text 

        Parameters
        ----------
        text : str
            str in which the keywords are searched for
        """

        for keyword in self.keywords:
            if re.search(re.escape(keyword), text, re.IGNORECASE):
                return True
        return False
    

    # Funktion, um alle relevanten Links und Texte von einem Parent zu extrahieren
    def extract_from_parent(self, parent:bs4.element.Tag, current_url:str) -> list:
        """
        Parameters
        ----------
        parent : bs4.element.Tag
            
        current_url : str
        """
        result = []
        # Durchlaufe alle untergeordneten Tags des Parent
        for descendant in parent.descendants:
            if descendant.name == 'a' and descendant.has_attr('href'):
                href = descendant['href']
                # Konvertiere relative Links in absolute Links
                absolute_href = urljoin(current_url, href)
                result.append((current_url, descendant.string.strip() if descendant.string else "", absolute_href))
            elif descendant.string and descendant.string.strip():  # Extrahiere den Text
                text = descendant.string.strip()
                if text not in self.extracted_texts:  # Überprüfe, ob der Text schon extrahiert wurde
                    self.extracted_texts.add(text)
                    result.append((current_url, text, ""))  # Leerer Link, da es sich um normalen Text handelt
        return result
    

    # Funktion, um alle relevanten Links und Texte von einer Seite zu extrahieren
    def extract_links_and_texts(self, soup:BeautifulSoup, base_url:str) -> list:
        """
        Parameters
        ----------
        soup : bs4.BeautifulSoup
            
        base_url : str
        """
        results = []

        # 1. Durchsuche alle <p>-Tags nach Stichwörtern
        for p_tag in soup.find_all('p'):
            if self.search_keywords(p_tag.get_text()):
                # Iteriere über den Parent des <p>-Tags
                parent = p_tag.parent
                if parent:
                    # Extrahiere Texte und Links aus dem Parent-Tag
                    parent_results = self.extract_from_parent(parent, base_url)
                    results.extend(parent_results)

        # 2. Durchsuche alle <a>-Tags nach Stichwörtern im Text
        for a_tag in soup.find_all('a', href=True):
            if self.search_keywords(a_tag.get_text()):
                href = a_tag['href']
                # Konvertiere relative Links in absolute Links
                absolute_href = urljoin(base_url, href)
                text = a_tag.get_text().strip()
                if text and text not in self.extracted_texts:
                    self.extracted_texts.add(text)
                    results.append((base_url, text, absolute_href))

        return results
    

    def is_scraping_allowed(self, url):
        """
        This function determines the host name of the url passed to it and searches for a robots.txt. 
        If a robots.txt is found, it is searched for the universal useragent * and for the useragent of the WebScraper. 
        Returns true if the useragent is allowed to scrape the url passed to the function, otherwise false. 

        Parameters
        ----------
        url : str
            The URL of the page for which you want to check whether it can be scraped
        """
        try:
            o = urlparse(url)
            robots_url = f"{o.scheme}://{o.hostname}/robots.txt"
            
            # Überprüfen, ob die `robots.txt` bereits gecached ist
            if robots_url not in self.robot_parser_cache:
                robot_parser = RobotFileParser()
                robot_parser.set_url(robots_url)
                robot_parser.read()
                self.robot_parser_cache[robots_url] = robot_parser
            else:
                robot_parser = self.robot_parser_cache[robots_url]

            # Überprüfen, ob die URL von dem allgemeinen und spezifischen User-Agent gescrapt werden darf
            can_fetch_general = robot_parser.can_fetch("*", url)
            can_fetch_useragent = robot_parser.can_fetch(self.useragent, url)

            return can_fetch_general and can_fetch_useragent

        except Exception as e:
            print(f"Fehler beim Zugriff auf robots.txt oder beim Parsen der URL: {e}")
            return False  # Rückgabe von False, wenn ein Fehler auftritt


    # Funktion zum Scrapen von URLs bis zur maximalen Tiefe
    def scrape(self, url:str, depth:int=0) -> None:
        """
        Parameters
        ----------
        url : str
            The URL of the page to be scraped
        depth : int
        """
        if depth > self.max_depth or url in self.visited_urls:
            return  # Breche ab, wenn die maximale Tiefe erreicht ist oder URL schon besucht wurde
        
        self.base_url = url

        if url in self.visited_urls:
            return # Breche ab, wenn die Seite schon besucht wurde
        
        self.visited_urls.add(url)
        
        if not self.is_scraping_allowed(url):
            print(f"Error: not allowed to enter {url}")
            return # Breche ab, wenn die robots.txt etwas für den useragent untersagt

        # Abrufen der Seite
        page_content = self.fetch_page(url)
        if not page_content:
            return

        # Parsen der HTML-Seite
        soup = BeautifulSoup(page_content, 'html.parser')

        # füge die gesamte HTML Seite dem dict htmlcontents ein
        self.siteshtml[url] = str(soup.find('body'))

        # Extrahiere relevante Links und Texte
        page_results = self.extract_links_and_texts(soup, url)

        if page_results:
            self.results.extend(page_results)

        # Verfolge gefundene Links weiter
        for _, _, link in page_results:
            if link:
                self.scrape(link, depth + 1)


    # Funktion zum Speichern der Ergebnisse als CSV oder JSON
    def save_results_to_file(self, filename:str, folder:str=None, filetype:str= "json", append_existing_file:bool=False) -> None:
        """
        Parameters
        ----------
        filename : str
            name of the file without .filetype
            
        folder : str, default None
            name of the folder the file should be stored in

        filetype : str, default "json"

        append_existing_file : bool, default False
            just works with filetype = "json"
        """
        # Erstelle DataFrame aus den Ergebnissen
        df = pd.DataFrame(self.results, columns=['URL', 'Text', 'Link'])
        df = self.clean_up_result(df, dup_column= "Text", prefer_column="Link")
        if folder:
            if not os.path.exists(f"./{folder}"):
                os.mkdir(f"./{folder}")
            filename = f"{folder}/{filename}.{filetype}"

        if filetype == "csv":
            # filename = f"{filename}.csv"
            if append_existing_file and os.path.exists(filename):
                pass
            else:
                df.to_csv(filename, index=False)
                print(f"Ergebnisse wurden in {filename} gespeichert.")

        elif filetype == "json":
            # filename = f"{filename}.json"
            if append_existing_file and os.path.exists(filename):
                try:
                    # Überprüfen, ob die Datei existiert und nicht leer ist
                    if os.path.exists(filename) and os.stat(filename).st_size > 0:
                        with open(filename, "r", encoding="utf-8") as file:
                            try:
                                # JSON-Inhalt lesen
                                input_json = json.load(file)
                            except json.JSONDecodeError:
                                print(f"Error: {filename} enthält kein gültiges JSON.")
                                input_json = {}
                    else:
                        input_json = {}

                    # DataFrame-Index setzen
                    df.set_index("URL", drop=True, inplace=True)

                    # Überprüfen, ob das Keyword im JSON existiert
                    if self.keywords[0] in input_json:
                        input_json[self.keywords[0]].update(df.to_dict(orient = "index"))
                    else:
                        input_json[self.keywords[0]] = df.to_dict(orient = "index")

                    # Datei im Schreibmodus öffnen und aktualisiertes JSON speichern
                    with open(filename, "w", encoding="utf-8") as file:
                        json.dump(input_json, file, indent=4, ensure_ascii=False)

                    print(f"Ergebnisse zur Suche nach {self.keywords[0]} mit Basisadresse {self.base_url} wurden in {filename} gespeichert.")

                except IOError:
                    print(f"Error: {filename} konnte nicht ergänzt werden.")

    
            else: # append_existing_file = False or file does not exist yet
                try:
                    with open(filename, "w", encoding = "utf-8") as file:
                        df.set_index("URL", drop=True, inplace = True)
                        parsed_json = json.loads(df.to_json(orient="index"))
                        parsed_json = {self.keywords[0] : parsed_json}
                        json.dump(
                            parsed_json,
                            fp= file, 
                            indent = 4, 
                            ensure_ascii = False
                        )
            
                    print(f"Ergebnisse zur Suche nach {self.keywords[0]} mit Basisadresse {self.base_url} wurden in {filename} gespeichert.")
                except IOError:
                    print(f"Error: {filename} konnte nicht erstellt werden")


    # Funktion zum kürzen eines DataFrames mit Scrape Results durch löschen von Text Dopplungen 
    def clean_up_result(self, df:pd.DataFrame, dup_column:str, prefer_column:str=None) -> pd.DataFrame:
        """
        This function deletes duplicates that occur in the column dup_column in the DataFrame df. 
        If prefer_column is None, the first of all rows in which the dup_column column has duplicate values is retained. 
        If a column is specified with prefer_column, the first row in which the prefer_column column has a value other than None is retained 
        from all rows in which the dup_column column has duplicate values.


        Parameters
        ----------
        df : pd.DataFrame

        dup_column : str
            Name of the column from which duplicates are to be deleted

        prefer_column : str
            Name of the column whose content should be retained when deleting duplicates from the dup_column

        """
        def select_row(group):
            # Behalte die Zeilen mit einem gültigen Wert in Spalte prefer_column, falls vorhanden
            non_na_rows = group[group[prefer_column].notna()]
            
            # Wenn es mindestens eine gültige Zeile gibt, behalte die erste
            if len(non_na_rows) > 0:
                return non_na_rows.iloc[0]
            # Wenn alle Zeilen in Spalte prefer_column NaN sind, behalte einfach die erste Zeile der Gruppe
            else:
                return group.iloc[0]
            
        def merge_text_on_adress(df):
            df_merged = df.groupby(["URL", "Link"], as_index=False, dropna = False).agg({
                'Text': lambda x: ' '.join(x)  
            })
    
            return df_merged

        df_cleaned = df.groupby(dup_column, group_keys=False).apply(select_row)
        df_cleaned.reset_index(inplace=True, drop=True)
        df_cleaned = merge_text_on_adress(df_cleaned)
        df_cleaned = df_cleaned.groupby("URL", as_index=False).agg({
                                                                "Text" : lambda x: " ".join(x),
                                                                "Link" : lambda x: list(filter(None, x))
                                                                })

        return df_cleaned
    
    
    def save_html(self, filename:str, folder:str=None):
        """
        saves the scraped html bodys as json with the url of the website as key and the html body as value of the type string

        Parameters:
        -----------
        filename : str
            name of the file without .filetype
            
        folder : str, default None
            name of the folder the file should be stored in
        """
        filetype = "json"

        if folder:
            if not os.path.exists(f"./{folder}"):
                os.mkdir(f"./{folder}")
            filename = f"{folder}/{filename}.{filetype}"
        
        if filetype == "json":
            
            # Wenn die Datei bereits existiert, laden wir die vorhandenen Daten
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = {}
            else:
                existing_data = {}

            # Update die vorhandenen Daten mit dem neuen Dictionary
            existing_data.update(self.siteshtml)

            # Speichern der aktualisierten Daten in der JSON-Datei
            with open(filename, 'w') as f:
                json.dump(existing_data, f, indent=4)

    
    @property
    def base_url(self):
        return self._base_url
    
    @base_url.setter
    def base_url(self, url):
        if not self._base_url:
            self._base_url = url