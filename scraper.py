import os
import re
from typing import Optional
from urllib.parse import \
    urljoin  # Für die Konvertierung von relativen zu absoluten URLs

import bs4
import pandas as pd
import requests
from bs4 import BeautifulSoup
from json import dump, loads


# Web Scraper Klasse
class WebScraper:
    def __init__(self, keywords:list, max_depth:int=2):
        self.keywords = keywords
        self.visited_urls = set()  # Um bereits besuchte URLs zu tracken
        self.max_depth = max_depth  # Maximale Tiefe der Verlinkungen
        self.extracted_texts = set()  # Set zum Vermeiden von doppelten Texten
        self.results = []  # Liste für die Ergebnisse (für DataFrame)


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
            response = requests.get(url)
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
            if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
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
    

    # Funktion zum Scrapen von URLs bis zur maximalen Tiefe
    def scrape(self, url:str, depth:int=0) -> None:
        """
        Parameters
        ----------
        url : str
            
        depth : int
        """
        if depth > self.max_depth or url in self.visited_urls:
            return  # Breche ab, wenn die maximale Tiefe erreicht ist oder URL schon besucht wurde

        self.visited_urls.add(url)

        # Abrufen der Seite
        page_content = self.fetch_page(url)
        if not page_content:
            return

        # Parsen der HTML-Seite
        soup = BeautifulSoup(page_content, 'html.parser')

        # Extrahiere relevante Links und Texte
        page_results = self.extract_links_and_texts(soup, url)

        if page_results:
            self.results.extend(page_results)

        # Verfolge gefundene Links weiter
        for _, _, link in page_results:
            if link:
                self.scrape(link, depth + 1)


    # Funktion zum Speichern der Ergebnisse als CSV oder JSON
    def save_results_to_file(self, filename:str, folder:str=None, filetype:str= "json") -> None:
        """
        Parameters
        ----------
        filename : str
            
        folder : str

        filetype : str
        """
        # Erstelle DataFrame aus den Ergebnissen
        df = pd.DataFrame(self.results, columns=['URL', 'Text', 'Link'])
        df = self.clean_up_result(df, dup_column= "Text", prefer_column="Link")
        if folder:
            if not os.path.exists(f"./{folder}"):
                os.mkdir(f"./{folder}")
            filename = f"{folder}/{filename}"

        if filetype == "csv":
            filename = f"{filename}.csv"
            df.to_csv(filename, index=False)
            print(f"Ergebnisse wurden in {filename} gespeichert.")

        elif filetype == "json":
            filename = f"{filename}.json"
            try:
                with open(filename, "w", encoding = "utf-8") as file:
                    # file.write(df.to_json(orient="index"))
                    dump(
                        loads(df.to_json(orient="index")),
                        fp= file, 
                        indent = 4, 
                        ensure_ascii = False
                    )
        
                print(f"Ergebnisse wurden in {filename} gespeichert.")
            except IOError:
                print(f"Error: {filename} konnte nicht erstellt werden")


    # Funktion zum kürzen eines DataFrames mit Scrape Results durch löschen von Text Dopplungen 
    def clean_up_result(self, df:pd.DataFrame, dup_column:str, prefer_column:str=None) -> pd.DataFrame:
        """
        Parameters
        ----------
        df : pd.DataFrame

        dup_column : str
            Name of the column from which duplicates are to be deleted

        prefer_column : str
            Name of the column whose content should be retained when deleting duplicates from the dupc_column

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
            df_merged = df.groupby(["URL", "Link"], as_index=False).agg({
                'Text': lambda x: ' '.join(x)  
            })
    
            return df_merged

        # Wende die Funktion auf jede Gruppe von Spalte dup_column an
        df_cleaned = df.groupby(dup_column, group_keys=False).apply(select_row)
        df_cleaned.reset_index(inplace=True, drop=True)
        df_cleaned = merge_text_on_adress(df_cleaned)
        return df_cleaned
            




