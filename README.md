# Berlin Buddy 

Projekt zur Chatbot für internationale Studierende im Rahmen der Summerschool 2024 des City Labs Berlin.

## Projekt
Im Rahmen dieses Projekts wurde ein Chatbot entwickelt, der mit öffentlichen Datenquellen wie den Webseiten der Berliner Hochschulen und berlin.de arbeitet. Diese Daten stammen aus einer Sammlung von rund 80 [Links](links.csv), die speziell recherchiert und ausgewählt wurden, um relevante Informationen für internationale Studierende bereitzustellen.

Für die Entwicklung des Chatbots wurde [Flowise.ai](https://flowiseai.com), ein Low-Code-Tool zur Erstellung von LLM-basierten Chatbots, eingesetzt. Zur effizienten Nutzung der Webseiteninformationen kam das RAG-Verfahren (Retrieval-Augmented Generation) zum Einsatz. Dabei wurde großer Wert darauf gelegt, ausschließlich selbst gehostete Open-Source-Software zu verwenden, um den Einsatz in datenschutzsensiblen Behörden zu ermöglichen.

Die erstellte Präsentation, sowie der OnePager und das auf der Transferale präsentierte Plakat sind im [doc](doc) Verzeichnis zu finden.

## Architektur
![Flow](doc/flow.png)
Die Daten werden über den Cheerio Webscraper abgerufen, dabei können auch Links tieferer Ebenen verwendet werden. Aus diesen Daten und den daraus durch LocalAi generierten Embeddings werden Einträge in einer Postgres-Vektordatenbank erstellt. 
Es gibt einen Record Manager, welcher verhindert das es zu doppelten Einträgen kommmt.    
Die Conversational Retrieval Chain nutzt Llama 3.1 über LocalAi mit einem RedisCache als Chat Modell.   
Die Postgresdatenbank ist der Vector Store. Zusätzslich gibt es noch Redis-Backed-Chat Memory um unterschiedliche Konversationen führen zu können und eine einfache Input Moderation, welche wieder über Llama 3.1 läuft.


## Installation

### Voraussetzung
Es wird nur docker-compose benötigt um das Projekt lokal laufen lassen zu können. Bei der Verwendung lokaler Chatbots bietet sich allerdings an eine GPU zu verwenden.

#### Hinweise
Mitunter gibt es unter Windows Probleme mit dem Embeddingsmodel in Local.Ai. Es wird deshalb empfohlen MacOS oder Linux zu verwenden.


### Konfiguration 
Für den "api" Service muss ggf. aufgrund der Architektur das passende Image ausgewählt werden (siehe https://localai.io/basics/container/).
Außerdem sollten die Zugangsdaten in [docker-compose.yml](docker-compose.yml) angepasst werden!

### Einrichtung
1. **Flow in Flowise erstellen**  
   Öffne Flowise unter [http://localhost:8080](http://localhost:8080) und erstelle einen neuen Flow. Importiere anschließend unsere [flow.json](data/flow.json) in den erstellten Flow.

2. **Modelle in LocalAi herunterladen**  
   Öffne LocalAi unter [http://localhost:3000](http://localhost:3000) und lade die benötigten Modelle herunter, beispielsweise *Llama 3.1* als LLM und *MiniLM-L6* für Embeddings. Danach richte eine API-Authentifizierung ein.

3. **Daten einspielen**  
   Daten können mithilfe des integrierten Webscrapers im Flow hinzugefügt werden. Füge einfach den gewünschten Link in den Webscraper ein und klicke auf **Upsert DB**, um die Datenbank zu aktualisieren. Ggf. müssen noch die Authentifizierungen für den Datenbankzugang in Flowise angelegt werden. Nutze dafür die Zugangsdaten aus [docker-compose.yml](docker-compose.yml).

4. **Chatbot verwenden**  
   Nach der Einrichtung des Flows und der Modelle sollte der Chatbot einsatzbereit sein. Öffne dazu einfach die Datei [chat-popup.html](chat/chat-popup.html) im Browser.

