# Kontrol af virksomheders aktivitet

Kontrollerer om virksomheder i Odense kommune har haft jobordrer eller tilbud i Momentum inden for de seneste 6 måneder, og tilføjer en virksomhedsbank-markering afhængigt af virksomhedens nuværende status.

## Hvad gør robotten?

1. Henter alle aktive virksomheder i Odense kommune (kommunekode 461) med 2 eller flere ansatte fra Momentum, som ikke allerede har en af markeringerne: kontakt, partnerskab, samarbejde, tjek til virksomhedsbank eller passiv – virksomhedsbank.
2. For hver virksomhed registreres CVR-nummer, P-nummer, virksomhedsnavn, reference-ID, aktiv-status, kommunekode og om virksomheden har markeringen "Passiv – Virksomhedsbank". Virksomheden tilføjes herefter til arbejdskøen.
3. For hvert kø-element hentes borgere i tilbud på virksomheden samt jobordrer med slutdato/opdateringsdato inden for de seneste 6 måneder og 1 dag.
4. Antal aktiviteter (borgere i tilbud + jobordrer) summeres. Har virksomheden mindst 2 aktiviteter, skal den markeres.
5. Hvis virksomheden allerede har markeringen "Passiv – Virksomhedsbank", oprettes markeringen "Tjek til virksomhedsbank". Ellers oprettes markeringen "Tjek til virksomhedsbank – ny portefølje".
6. Afsluttede opgaver registreres via ODK Tracker. Virksomheder uden tilstrækkelig aktivitet registreres som delopgaver.

## Forudsætninger

- Python ≥ 3.13
- [`uv`](https://docs.astral.sh/uv/) til pakkehåndtering
- Adgang til **Automation Server** (arbejdskø)
- Adgang til **Momentum** (produktion)
- Adgang til **Odense SQL Server**

## Installation

```sh
uv sync
```

## Konfiguration

Credentials registreres i Automation Server:
- `Momentum - produktion`
- `Odense SQL Server`

| Miljøvariabel | Beskrivelse |
|---|---|
| `ATS_URL` | URL til Automation Server-instansen (f.eks. `http://localhost:8000`) |
| `ATS_TOKEN` | Bearer token til autentificering mod Automation Server |
| `ATS_WORKQUEUE_OVERRIDE` | Tilsidesæt arbejdskø-ID (bruges til lokal test) |

## Kørsel

```sh
uv run python main.py --queue   # Fyld arbejdskøen med virksomheder fra Momentum
uv run python main.py           # Behandl arbejdskøen og opret markeringer
```

## Afhængigheder

| Pakke | Formål |
|---|---|
| `automation-server-client` | Håndterer arbejdskø, work items og credentials mod Automation Server |
| `momentum-client` | Henter virksomheder, borgere i tilbud og jobordrer samt opretter markeringer i Momentum |
| `odk-tools` | ODK Tracker til registrering af afsluttede og delvise opgaver |
| `pydantic` | Datavalidering af virksomhedsdata (CVR, P-nummer, GUID-format) |
| `python-dateutil` | Datoaritmetik til beregning af 6 måneder tilbage fra dags dato |

## GDPR og sikkerhed

Processen tilgår data om borgere i Momentum for at tælle aktiviteter på virksomheder. Persondata gemmes ikke i arbejdskøen – kø-elementerne indeholder udelukkende virksomhedsdata (CVR, P-nummer, virksomhedsnavn).
