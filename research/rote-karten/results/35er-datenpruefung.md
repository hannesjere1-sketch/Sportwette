# Datenprüfung zum erweiterten Durchgang

Erzeugt von `14_datenpruefung_bericht.py`; die Messungen stammen aus
`10_eigentore_pruefung.py` und `11_halbzeit_pruefung.py`.


## 1. Welche Fallzahl gilt

**343.** Nachgezählt direkt in `data/35er-erweitert-faelle.csv`,
Klasse `< 1,30`, erste Ligen.

| Aufteilung | Fälle | Treffer | Trefferquote |
| --- | ---: | ---: | ---: |
| gesamt | 343 | 240 | 70,0 % |
| 2005/06 – 2014/15 | 122 | 86 | 70,5 % |
| 2015/16 – 2023/24 | 221 | 154 | 69,7 % |

| Zerlegung | Fälle | Treffer | Trefferquote |
| --- | ---: | ---: | ---: |
| 5 alte Ligen, 2015 – 2024 | 121 | 73 | 60,3 % |
| 5 alte Ligen, 2005 – 2015 | 69 | 52 | 75,4 % |
| 6 neue Ligen, 2015 – 2024 | 100 | 81 | 81,0 % |
| 6 neue Ligen, 2005 – 2015 | 53 | 34 | 64,2 % |
| **Summe** | **343** | | |

Beide Aufteilungen ergeben 343. Die abweichenden Zahlen 338 und 340
standen nur in meiner Zusammenfassungsnachricht, nicht in
`results/35er-erweitert.md` — dort steht durchgehend 343. Es waren
Übertragungsfehler beim Abtippen der Zerlegung: 118 statt 122 und
220 statt 221 in den Zeithälften, 69 als 68 und 100 als 101 und 53
als 50 in der Zerlegung. Die Tabellen im Bericht waren richtig, die
Nachricht war es nicht. Ich habe sie neu aus der Falldatei gerechnet,
statt sie noch einmal abzuschreiben.

## 2. Liverpool – Newcastle, 11.05.2014

Der Fall ist richtig — aber die Rückfrage trifft genau den
wunden Punkt. Das erste Tor fällt in Minute 20, und geschossen
hat es ein **Liverpooler**: Martin Škrtel, ins eigene Tor.

| Minute | Ereignis | zählt für | Text bei ESPN |
| ---: | --- | --- | --- |
| 20' | Own Goal | Newcastle (Gast) | Own Goal by Martin Skrtel, Liverpool.  Liverpool 0, Newcastle United 1. |
| 63' | Goal | Liverpool (Heim) | Goal!  Liverpool 1, Newcastle United 1. Daniel Agger (Liverpool) left footed sho |
| 65' | Goal | Liverpool (Heim) | Goal!  Liverpool 2, Newcastle United 1. Daniel Sturridge (Liverpool) left footed |

Die Gegenprobe bei football-data.co.uk: Halbzeitstand **0:1**,
Endstand **2:1**. Beide Quellen sagen dasselbe.

Für die Strategie ist das die richtige Zuordnung: Liverpool lag
nach 20 Minuten 0:1 zurück, unabhängig davon, wessen Fuß den Ball
ins Tor gelenkt hat. Der Trigger fragt nach dem Spielstand, nicht
nach dem Schützen.

Ob das ein Muster ist, beantwortet Abschnitt 3: Eigentore sind
die Fallgruppe, in der eine falsche Zuordnung am ehesten
passieren würde — deshalb sind sie vollständig durchgeprüft.

## 3. Eigentore: alle statt achtzig

Die frühere Angabe „78 von 80" kam aus einer Stichprobe. Eine
Stichprobe lässt genau die Frage offen, die gestellt wurde: sind die
zwei Ausnahmen Zufall oder Muster? Deshalb sind jetzt **alle**
zwischengespeicherten Spiele geprüft.

Verfahren: Aus den Team-Verweisen der ESPN-Tor-Ereignisse wird der
Endstand rekonstruiert und mit football-data.co.uk verglichen. Zwei
Quellen, die nichts voneinander wissen.

| Menge | Spiele | Endstand weicht ab | Anteil |
| --- | ---: | ---: | ---: |
| Spiele **mit** Eigentor | 1550 | 50 | 3,23 % |
| Spiele **ohne** Eigentor | 19956 | 1446 | 7,25 % |

**Das Ergebnis ist das Gegenteil einer Warnung.** Spiele mit
Eigentor stimmen häufiger als Spiele ohne. Eigentore sind also
keine Fehlerquelle — ESPN schreibt sie zuverlässig der Mannschaft
gut, für die sie zählen.

Die entscheidende Zusatzprobe: bei wie vielen der Abweichungen
würde ein Umdrehen der Eigentor-Zuordnung den Endstand richtig
machen? Antwort: bei **1 von 50**. Die Abweichungen kommen also
nicht von den Eigentoren, sondern davon, dass in ESPNs Spielverlauf
einzelne Tore fehlen — vor allem in älteren Saisons kleinerer Ligen.

**Und diese Spiele fließen ohnehin nicht ein.** Die Auswertung
verwirft jedes Spiel, dessen rekonstruierter Endstand von
football-data abweicht — das ist die Verwurfskategorie „Endstand
weicht ab". Die hochgerechneten „rund neun falsch zugeordneten
Fälle" gibt es deshalb nicht: die betroffenen Spiele werden
aussortiert, bevor ein Fall daraus wird.

## 4. Die schärfere Probe: der Halbzeitstand

Der Endstand-Abgleich prüft nur die Summe. Zwei Fehler, die sich
aufheben, würde er nicht bemerken — und für den Trigger zählt genau
das, was er nicht prüft: **wer** zuerst trifft und **wann**.

Deshalb die zweite Probe: der Halbzeitstand, aus ESPNs Ereignissen
der ersten Halbzeit rekonstruiert und gegen die Spalten `HTHG`/`HTAG`
von football-data gehalten. Ein 35er-Fall liegt per Definition vor
Minute 35, also immer in der ersten Halbzeit.

| Menge | prüfbare Spiele | Halbzeitstand stimmt | Anteil |
| --- | ---: | ---: | ---: |
| alle zwischengespeicherten Spiele | 20007 | 19921 | 99,57 % |
| nur die 3217 Fälle | 3216 | 3199 | 99,47 % |
| nur Spiele mit Eigentor in Halbzeit 1 | 737 | 735 | 99,73 % |

Von den Fällen weichen **17** ab. Ihr Gewicht:

| Klasse | Fälle | davon betroffen | Trefferquote | ohne die Betroffenen |
| --- | ---: | ---: | ---: | ---: |
| < 1,30 | 343 | 1 | 70,0 % | 69,9 % |
| < 1,50 | 1050 | 7 | 56,9 % | 56,6 % |
| < 1,80 | 2472 | 16 | 46,0 % | 45,8 % |

Selbst wenn **jede** dieser Abweichungen bedeutete, dass der Fall
gar keiner ist, ändert das an keiner Trefferquote mehr als zwei
Zehntel Prozentpunkte.

Auffällig ist, wo sie liegen: **14 von 17** in Belgien, Griechenland
oder der Türkei, und die Jahre reichen von 2006 bis 2010 — also genau
dort, wo ESPNs Spielverläufe ohnehin am dünnsten sind. In den
Saisons ab 2012 gibt es keine einzige Abweichung.

## 5. Was bleibt

| Frage | Antwort |
| --- | --- |
| Welche Fallzahl gilt? | 343. Die abweichenden Zahlen waren Tippfehler in meiner Nachricht. |
| Liverpool – Newcastle | richtig zugeordnet; das Tor war ein Eigentor von Škrtel. |
| Eigentore fehlerhaft? | Nein. 1500 von 1550 Spielen mit Eigentor stimmen, und von den 50 Abweichungen wäre genau eine durch eine umgedrehte Eigentor-Zuordnung erklärbar. |
| Hochgerechnet neun falsche Fälle? | Nein. Spiele mit abweichendem Endstand werden verworfen, bevor ein Fall entsteht. |
| Frühe Tore richtig zugeordnet? | In 99,47 % der Fälle bestätigt der unabhängige Halbzeitstand die Zuordnung. |
