# Wettportal Import (Browser-Erweiterung)

Überträgt eine bei Tipico platzierte Wette mit einem Klick ins Wettportal — ohne
Passwörter zu speichern und ohne die Tipico-Seite im Hintergrund zu überwachen.

## Installation (Chrome / Edge / Brave)

1. `chrome://extensions` öffnen, **Entwicklermodus** aktivieren.
2. **Entpackte Erweiterung laden** → diesen `extension/`-Ordner auswählen.
3. Auf das Erweiterungssymbol klicken → **Jetzt einrichten** → Portal-URL und
   API-Key eintragen (beides steht im Portal unter **Einstellungen** →
   „Browser-Erweiterung“). Beim Speichern nach der Berechtigung für die
   Portal-URL bestätigen.

## Benutzung

1. Wette bei Tipico wie gewohnt platzieren.
2. Auf das Erweiterungssymbol klicken. Das Popup versucht, Liga, Teams, Markt,
   Tipp, Quote und Einsatz automatisch von der Seite zu lesen.
3. **Alle Felder prüfen und korrigieren** — die Erkennung ist eine Heuristik
   (Texterkennung nach Schlagwörtern wie „Quote“/„Einsatz“ und generischen
   CSS-Selektoren), keine offizielle Tipico-Schnittstelle. Je nach Seite/Ansicht
   kann sie unvollständig oder falsch sein.
4. **An Portal senden** klicken.

## Warum nur "Ein-Klick" statt vollautomatisch?

Tipico bietet keine öffentliche API für Wetthistorie. Eine dauerhafte
Hintergrund-Überwachung oder ein automatisierter Login in dein Tipico-Konto
würde deren Nutzungsbedingungen (Verbot automatisierter Zugriffe) verletzen und
im schlimmsten Fall zu einer Kontosperre führen. Diese Erweiterung liest nur
die Seite, die *du* gerade aktiv im Browser geöffnet hast, wenn *du* auf das
Icon klickst — kein Login, kein Passwort, kein Hintergrundzugriff.

## Bekannte Grenzen / Weiterentwicklung

Die Extraktion in `popup.js` (`extractBetSlip`) wurde ohne Zugriff auf ein
echtes Tipico-Konto geschrieben und ist bewusst generisch gehalten. Wenn
bestimmte Felder regelmäßig falsch oder leer erkannt werden: die tatsächlichen
CSS-Klassen/Texte auf der Tipico-Bestätigungsseite (z. B. per Rechtsklick →
„Untersuchen“) notieren und die Selektoren in `extractBetSlip` entsprechend
anpassen.
