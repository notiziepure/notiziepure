# notiziepure — progetto pronto per la configurazione online

Apri `site/index.html` per l’anteprima locale. Testi, illustrazione, pagine degli articoli e archivio funzionano senza server. La copia iniziale conserva le 49 notizie della prova del 26 settembre 2026: non è una rassegna aggiornata a oggi.

## Che cosa è implementato

- Controllo programmato ogni 30 minuti, con raccolta da RSS/Atom e scoperta dei feed dichiarati dalle testate.
- Lettura di contenuti pubblicamente accessibili, senza superare paywall o divieti di accesso. Le fonti indisponibili sono registrate e saltate.
- Riconoscimento dello stesso evento attraverso il confronto editoriale, ID, titolo e URL già presenti. Un aggiornamento mantiene l’indirizzo originale.
- Sintesi breve e articolo originale più ampio, con almeno due editori e riscontri testuali verificabili. Un secondo passaggio AI verifica il testo prima dell’inserimento. Non è una garanzia assoluta contro gli errori: rimane necessaria la supervisione editoriale.
- Riordino per rilevanza e attualità. Quattro aperture globali senza quote tra sezioni. Le aperture contano nel totale della rispettiva sezione.
- 4–6 articoli per Sport, Rosa e Movimenti; 6–10 per Mondo, Italia, Politica, Cronaca, Tecnologia e Nera. Il massimo si raggiunge solo quando ci sono abbastanza notizie rilevanti. Se mancano riscontri per il minimo, l’edizione precedente resta online e il rapporto segnala il problema.
- Le notizie che escono dalla selezione passano nell’archivio e restano allo stesso indirizzo. Nessuna cancellazione periodica è impostata.
- UNA edizione giornaliera alla mezzanotte italiana: comprende l’ultima selezione del giorno appena concluso, con copie immutabili dei testi e dell’ordine. Non è la raccolta di tutte le notizie transitate durante il giorno: quelle rimosse sono nell’archivio degli articoli.
- Se un’esecuzione salta, il controllo successivo recupera la chiusura prima di aggiornare le notizie. Non inventa edizioni per giorni di inattività. Sono gestiti ora legale e ora solare.
- Una sola illustrazione AI in bianco e nero, indicata come scena simbolica. Non viene rigenerata automaticamente a ogni controllo.

## Stato della consegna

Il motore, i test e il flusso di pubblicazione sono presenti. L’aggiornamento AI è disattivato, il budget impostato a zero e la pubblicazione non è ancora collegata a GitHub. Non è stato acquistato o attivato alcun servizio. Le fonti del catalogo sono configurazioni iniziali: il loro accesso live e la capacità di coprire tutte le sezioni vanno collaudati prima dell’attivazione. Una fonte priva di feed o di testo sufficiente non produce articoli.

L’archivio contiene già una copia chiaramente etichettata dell’edizione di prova. Alla prima attivazione, le notizie nuove si accumulano finché tutte le sezioni raggiungono il minimo; solo allora sostituiscono insieme la prova. Non vengono presentate vecchie notizie demo come notizie del giorno.

## Passaggi di pubblicazione che faremo insieme

1. Creare o collegare il repository GitHub `notiziepure`, con ramo principale `main`, e caricare il CONTENUTO di questa cartella. Deve essere inclusa la cartella nascosta `.github`, che contiene la programmazione. Nessuna chiave deve essere caricata nei file.
2. In GitHub Pages scegliere GitHub Actions. Impostare la variabile di repository `NOTIZIEPURE_PUBLISH` a `true` per pubblicare l’anteprima. In questa fase l’aggiornamento AI resta spento.
3. Eseguire il workflow manualmente con operazione `build` e verificare sito e collegamenti all’indirizzo assegnato. Facoltativo: collegare un dominio proprio e scriverlo in `config/domain.txt`.
4. Scegliere il modello AI e il tetto mensile. Inserire `OPENAI_API_KEY` nei Secrets di GitHub, mai in chat, nel codice o nel sito. Inserire il modello in `OPENAI_MODEL` o nel campo `model` della configurazione.
5. Configurare in `config/settings.json` le tariffe corrette di input/output per milione di token, `monthly_budget_usd`, `ai_enabled: true` e `live_enabled: true`. Le tariffe devono corrispondere al modello effettivo. Il consumo API è un servizio separato dall’hosting.
6. Prima eseguire manualmente `update` con la pubblicazione temporaneamente disabilitata, controllare `data/report.json`, le fonti e alcuni articoli, e risolvere eventuali carenze di copertura. Non abilitare l’avvio automatico prima del collaudo reale.
7. Riabilitare la pubblicazione e impostare `NOTIZIEPURE_ENABLED` a `true`: partono i controlli programmati. Per sospenderli basta riportarla a `false`; il sito già pubblicato resta consultabile.

La configurazione iniziale resta valida per le modifiche successive: un aggiornamento dei file sul ramo principale ricostruisce e pubblica il sito allo stesso indirizzo. Le chiavi e le impostazioni non vanno reinserite ogni volta.

## Costi e affidabilità

Prima di ogni richiesta AI viene accantonata una stima prudente basata sulla dimensione dell’input, sul limite di output e sulle tariffe configurate. Su GitHub la riserva è salvata nel repository PRIMA della richiesta: se il salvataggio fallisce, la chiamata non parte. Una richiesta fallita mantiene la riserva e non viene ritentata automaticamente. Questo meccanismo può fermare il servizio prima di consumare tutto il budget reale; non sostituisce la verifica dei prezzi del fornitore. Il conteggio mensile usa UTC.

Il limite di chiamate per ciclo protegge da esecuzioni troppo lunghe; la rotazione delle sezioni evita di privilegiare sempre le prime. I feed senza variazioni non provocano nuove chiamate AI. La homepage può restare invariata se non ci sono novità sufficientemente documentate. La raccolta usa al massimo tre documenti recenti per fonte a ciclo, per contenere tempi e costi: non pretende di coprire tutte le notizie pubblicate nel mondo.

GitHub può ritardare o saltare esecuzioni programmate; ogni mezz’ora è la cadenza richiesta, non una garanzia al secondo. Il rapporto mostra errori delle fonti, testi scartati, carenze e notizie attive più vecchie della finestra di ricerca. Se il sistema si ferma, l’ultimo sito pubblicato resta accessibile.

## Verifiche eseguite nella consegna

Test locali di aggiornamenti, deduplicazione, limiti per sezione, scelta delle aperture, archiviazione senza cancellazione, chiusura a mezzanotte, cambio d’ora, interruzioni, budget, RSS/Atom e fonti insufficienti. Controllo delle pagine e dei collegamenti relativi. Non sono state eseguite chiamate AI a pagamento né una pubblicazione reale. Il controllo visivo nel browser integrato non è disponibile per questi file locali.

## Struttura

- `site/`: gli unici file da servire al pubblico.
- `data/state.json`: catalogo, ID permanenti e selezione corrente.
- `data/editions/`: copie giornaliere dei contenuti.
- `data/usage.json`: riserve di budget.
- `data/report.json`: esito dell’ultimo ciclo.
- `config/`: fonti e impostazioni.
- `scripts/`: raccolta, redazione, archivio e costruzione del sito (Python 3.12, nessuna dipendenza aggiuntiva).
- `tests/`: prove automatiche con dati fittizi, senza chiamate a pagamento.
- `.github/workflows/notiziepure.yml`: programmazione e pubblicazione.

Per modifiche editoriali manuali possiamo lavorare insieme sul progetto. Il pannello di redazione autonomo non è incluso in questa versione.

## Riferimenti tecnici

- https://developers.openai.com/api/docs/guides/structured-outputs
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
