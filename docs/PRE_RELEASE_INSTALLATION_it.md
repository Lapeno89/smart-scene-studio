# Smart Scene Studio v0.1.0-alpha.1 — installazione e collaudo

Questa è una pre-release manuale in prova, non una release pubblicata. Il pacchetto è costruito dal commit indicato in `RELEASE_CANDIDATE.json` e include già il JavaScript compilato. Sul server Home Assistant non servono Python, Node.js, npm, accesso a un CDN o copie in `/config/www`.

## Installazione

1. **Fai un backup completo.** In Home Assistant apri **Impostazioni → Sistema → Backup**, scegli **Backup adesso → Backup manuale**, includi tutte le parti necessarie al ripristino completo e scarica il backup su un altro computer o disco. Segui la [guida ufficiale ai backup](https://www.home-assistant.io/common-tasks/general/backups). Se Smart Scene Studio è già presente, copia anche la vecchia cartella `custom_components/smart_scene_studio`.
2. **Scarica il pacchetto ZIP** `Smart-Scene-Studio-v0.1.0-alpha.1.zip` fornito insieme a questa guida. L'archivio contiene `custom_components/smart_scene_studio/`; estrailo in una cartella temporanea sul computer.
3. Copia la cartella **`custom_components/smart_scene_studio`** estratta in **`/config/custom_components/`**. Il percorso finale deve essere `/config/custom_components/smart_scene_studio/manifest.json`. Se usi File Editor o Samba, prima verifica che non stai sovrascrivendo un'altra copia in uso.
4. **Riavvia Home Assistant.** Un'installazione o sostituzione manuale del codice richiede il riavvio.
5. Apri **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**, cerca **Smart Scene Studio** e completa il flusso di configurazione.
6. Apri **Smart Scene Studio** dalla barra laterale. Se non compare, ricarica la pagina del browser una volta e controlla i log.
7. Apri una scena, seleziona esplicitamente una o più lampade `light.*` (massimo 64), controlla i destinatari e premi **Applica**. Leggi la conferma e conferma l'azione. Aprire la galleria, selezionare una scena o vedere l'anteprima non invia comandi alle lampade.

Non installare questo candidato da HACS/Marketplace: non è stata pubblicata una release GitHub e il branch della PR non è quello predefinito. Il pacchetto è per installazione manuale controllata dal proprietario.

## Checklist del primo collaudo reale

Annota esito e ora per ciascun punto. Inizia con una lampada di prova che puoi osservare in sicurezza.

- [ ] Il backup completo è stato creato e scaricato fuori dal server.
- [ ] L'integrazione si installa e compare in **Dispositivi e servizi** dopo il riavvio.
- [ ] Il pannello si apre dalla barra laterale anche dopo un aggiornamento completo della pagina.
- [ ] La galleria mostra tutti gli **11 preset originali** e le rispettive palette.
- [ ] Aprendo un preset o cambiando anteprima le lampade non ricevono comandi.
- [ ] Seleziono esplicitamente una lampada RGB e vedo il destinatario selezionato prima di applicare.
- [ ] Confermo una scena RGB: la lampada selezionata cambia colore e nessun'altra lampada viene comandata.
- [ ] Seleziono una lampada che supporta la temperatura colore e provo **Candle White (2700 K)** o **Clear White (4000 K)**; registro il Kelvin indicato e il comportamento visivo.
- [ ] Verifico i tempi di transizione con una lampada compatibile; registro se il firmware li rispetta.
- [ ] Provo una lampada non disponibile: la UI la segnala e il risultato indica ciò che è stato saltato o non applicato.
- [ ] Riavvio Home Assistant e verifico che i preset restino visibili e le scene personali salvate siano ancora presenti.
- [ ] Controllo i log di Home Assistant e la console del browser per errori.

Per i log di Home Assistant vai in **Impostazioni → Sistema → Log** e cerca `smart_scene_studio`. Per errori visivi del pannello, apri la console del browser (strumenti sviluppatore) e annota l'errore. Prima di inviare log o screenshot, oscura token, nomi personali, indirizzi e identificativi privati.

## Disinstallazione e ripristino

1. In **Impostazioni → Dispositivi e servizi**, apri Smart Scene Studio e rimuovi la sua voce di integrazione.
2. Arresta Home Assistant prima di cancellare `/config/custom_components/smart_scene_studio/` oppure sostituiscila con la cartella della versione precedente.
3. Riavvia Home Assistant. Le scene sono conservate nell'area `.storage` gestita da Home Assistant e non si trovano nella cartella dell'integrazione: **non cancellare né modificare manualmente quei file**.
4. Se la versione precedente non riesce a leggere i dati dopo un aggiornamento dello schema, ripristina il backup completo creato prima dell'installazione. Questa alpha non promette downgrade automatici dopo future migrazioni.

Il collaudo su HA reale e su lampade fisiche non è stato eseguito dallo sviluppatore: completa questa checklist e comunica gli esiti prima di considerare il candidato accettato.
