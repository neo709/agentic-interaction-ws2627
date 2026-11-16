# Delegationsgrenze

## Entscheidungen

| Aktion | Entscheidung | Begründung |
| --- | --- | --- |
| 1. Termine eines Tages lesen | alone | Der Agent braucht diese Informationen für die Kalenderfrage und verändert dabei keine Daten. |
| 2. Wetter nachschlagen | alone | Die Abfrage liefert Informationen für meine Planung, ohne etwas zu buchen oder zu verändern. |
| 3. Zugverbindungen suchen | alone | Die Suche zeigt mögliche Verbindungen und Preise, verpflichtet mich aber noch zu keinem Kauf. |
| 4. Notizen lesen | alone | Der Agent darf die für meinen Auftrag relevanten Notizen lesen. Die Inhalte bleiben dabei unverändert. |
| 5. Persönlichen Kalenderblock ohne andere Teilnehmende anlegen | alone | Ein zum Auftrag passender Planungsblock, etwa für Reisezeit, betrifft nur meinen Kalender und lässt sich leicht entfernen. |
| 6. Termin mit anderen Teilnehmenden verschieben | approval | Die Änderung beeinflusst auch andere Personen. Den neuen Zeitpunkt möchte ich deshalb vorab bestätigen. |
| 7. Zugticket buchen | approval | Eine Buchung kostet Geld und kann Stornogebühren verursachen. Ich möchte Verbindung und Preis vor dem Kauf bestätigen. |
| 8. Nachricht an Dritte senden | approval | Der Agent kommuniziert in meinem Namen. Empfänger und konkreten Text möchte ich vor dem Senden prüfen. |
| 9. Notiz erstellen | alone | Eine neue Notiz im Rahmen eines geklärten Auftrags ergänzt meine Informationen, ohne vorhandene Inhalte zu überschreiben. |
| 10. Notiz löschen | approval | Beim Löschen können Informationen verloren gehen. Der Agent soll zuerst benennen, welche Notiz er löschen möchte, und meine Zustimmung abwarten. |

`alone` bedeutet selbstständig handeln; `approval` bedeutet vorher fragen und
erst nach einem Ja handeln. Fehlen wichtige Angaben zum Auftrag, soll der Agent
auch bei einer mit `alone` eingeordneten Aktion nachfragen.

## Entscheidungsregel

Der Agent darf auftragsbezogene Informationen selbstständig lesen und leicht rückgängig zu machende persönliche Ergänzungen vornehmen, braucht aber vor Kosten, Auswirkungen auf andere Personen oder Informationsverlust meine Zustimmung.

## Beobachtungen aus dem Rollenspiel

1. Die Reiseplanung erforderte nicht für jeden lesenden Werkzeugaufruf eine
   Zustimmung, aber Rückfragen zu fehlenden Wegzeiten und zum Konflikt zwischen
   Standup und Zugfahrt waren nötig, damit ein brauchbarer Plan entstand;
   das Ziel, rechtzeitig anzukommen, legte außerdem noch nicht fest, ob der Agent
   ein kostenpflichtiges Ticket buchen durfte.
2. Bei „Räume meine Notizen auf“ war zunächst unklar, ob eine Übersicht erstellt
   oder etwas gelöscht werden sollte; erst die Rückfrage klärte, dass die
   Originalnotizen erhalten bleiben sollten, und ermöglichte eine passende
   Ergänzung ohne Informationsverlust.
