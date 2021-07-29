# Netzwerkprogrammierung SS-2021
Python Projekt im Modul Netzwerkprogrammierung SS-2021. Das Projekt beinhalten eine eigene 
Interpretation eines Blockchain Servers, mit dazugehörigem Client. Clients lesen Dateien 
(Text, Bild, etc.) ein, zerteilen diese und schicken sie zum Server.

## Blockchain client/server

### Server Anwendung
```
python server.py --ip <ip> --port <port> [--fs]
```
Argumente:

| Name  | Nutzung |
|---	|---	|
| --ip | Angabe der IP Adresse |
| --port | Angabe des Ports| 
| --fs | Option um dem Server mitzuteilen ob die Blockchain im FileSystem gespeichert werden soll| 

### Client Anwendung:
```
python client.py --ip <ip> --port <port>
```
Argumente:

| Name  | Nutzung |
|---	|---	|
| --ip | Angabe der IP Adresse des Servers |
| --port | Angabe des Ports des Servers | 

Der Client wird interaktiv im Terminal verwendet. Es können über den Client Dateien (Text, Bild, etc.)
eingelesen und an den Server gesendet werden. Vor dem senden wird die Datei dabei in Blöcke 
zerlegt, die dann auf dem Server in einer Blockchain gespeichert werden. Der Client hat außerdem die
Möglichkeit zu überprüfen ob eine Datei bereits auf dem Server gespeichert ist. Ebenso ist es Möglich 
die Intirität der gesamten Blockchain zu überpfrügen. Der Client kann außerdem an hand eines Dateihashes
diese Datei vom Server laden und wiederherstellen.

Befehle:

| Name  | Nutzung |
|---	|---	|
| stop | Beendet den Client |
| help | Gibt diese Hilfe aus |
| add \<file> | Sendet die Datei in Blöcken zerteilt an den Server |
| check \<file or hash> | Überprüft ob die Datei schon auf der Blockchain gespeichert ist | 
| check | Überprüft die gesamte Blockchain |
| get \<hash> | Lädt die Datei des zugehörigen hashes vom Server herunter |