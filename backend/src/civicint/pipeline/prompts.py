"""LLM prompts, cost estimation, and text helpers for the pipeline."""

TRIAGE_PROMPT = """\
Analysoit suomalaisia kunnallisia päätösasiakirjoja. Tehtäväsi on tunnistaa päätökset, \
joilla on todellinen vaikutus fyysiseen ympäristöön — riippumatta siitä, mainitaanko \
asiakirjassa "ympäristö"-sanaa vai ei.

Arvioi VAIKUTUSTA, älä aihetta. Kysymys on: "Voiko tämä päätös muuttaa maisemaa, \
luontoa, vesistöjä tai maankäyttöä merkittävästi?"

Kategoriat (yksi tai useampi):
1. maankaytto — Kaavoitusmuutokset jotka avaavat alueita rakentamiselle, \
   merkittävät poikkeamisluvat, maanmyynti kehittäjille, yleiskaavamuutokset
2. rakentaminen — Uudet asuinalueet, teollisuusrakennukset, tiehankkeet, \
   suuret infrastruktuuriprojektit, merkittävät uudisrakennukset
3. luonnonvarat — Kaivokset, maa-ainesten otto, turvetuotanto, metsähakkuut, \
   tuulivoimahankkeet, energiahankkeet
4. vesistot — Ojitus, kuivatus, vesistörakentaminen, rantarakentaminen, \
   pohjavesialueet, jätevesiasiat
5. vaikuttaminen — Kehittäjien aloittamat kaavoituspyynnöt, konsulttisopimukset \
   maankäyttöhankkeisiin, lobbaus, sidosryhmävaikuttaminen päätöksenteossa

Palauta JSON:
{
  "categories": ["rakentaminen"],
  "relevance_score": 0.85,
  "candidate_reason": "Uuden asuinalueen rakentamispäätös 30 hehtaarin metsäalueelle",
  "is_environmental": true
}

Korkea pistemäärä (0.7–1.0):
- Konkreettinen päätös joka muuttaa maankäyttöä tai ympäristöä
- Uusi rakennushanke merkittävässä mittakaavassa
- Kaivos-, tuulivoima-, turve- tai maa-aineslupa
- Vesistöön kohdistuva toimenpide
- Maanmyynti tai kaavoitusaloite kehittäjältä

Matala pistemäärä (alle 0.3):
- Rutiinipoikkeamisluvat (terassi, laajennus, käyttötarkoituksen muutos pienessä mittakaavassa)
- Hallinnolliset asiat (henkilöstö, talous, tiedoksiannot)
- Kokousten pöytäkirjat ilman konkreettisia maankäyttöpäätöksiä
- Yksittäisten kiinteistöjen pienet muutokset
- Kulttuurihistorialliset suojelupäätökset ilman ympäristövaikutusta
"""

CASE_BUILDER_PROMPT = """\
Luot yhteenvetoja kunnallisista päätöksistä jotka vaikuttavat fyysiseen ympäristöön. \
Kohderyhmä: ympäristöjärjestöjen ammattilaiset jotka tarvitsevat toimintakelpoista tietoa.

Jos asiakirjassa EI ole konkreettista päätöstä joka muuttaa maankäyttöä, ympäristöä \
tai luonnonvaroja, palauta: {"skip": true, "skip_reason": "Syy miksi ohitetaan"}

Muussa tapauksessa palauta JSON:

{
  "skip": false,
  "headline": "15 tuulivoimalan lupa hyväksytty Muonion pohjoisalueelle",
  "debrief": [
    "Lupa myönnetty 15 tuulivoimalalle, kokonaiskorkeus 250m",
    "YVA valmistunut — linnustovaikutukset arvioitu vähäisiksi",
    "30 päivän valitusaika alkanut 15.3.2025",
    "Rakentamisen arvioitu alkavan Q2 2025"
  ],
  "status": "valitusaika",
  "action_deadline": "2025-04-15",
  "timeline": [
    {"date": "2025-01-15", "event": "Lupahakemus jätetty"},
    {"date": "2025-03-01", "event": "Nähtävilläoloaika päättynyt"}
  ],
  "evidence": [
    {"page": 3, "snippet": "Ympäristölupa myönnetään ehdoin...",
     "key_point": "Lupa myönnetty ehdollisena"}
  ],
  "entities": {
    "applicant": "Tuulivoima Oy",
    "permit_number": "YL-2025-123",
    "location": "Muonion pohjoinen alue",
    "area_hectares": 150,
    "project_name": "Tuulivoimapuisto Pohjoinen"
  }
}

Status kuvaa TOIMINTAMAHDOLLISUUTTA, ei hallinnollista tilaa:
- "valitusaika" — Päätös tehty, valitusaika käynnissä. Merkitse action_deadline \
  jos valitusajan päättymispäivä on tiedossa tai laskettavissa.
- "nahtavilla" — Nähtävillä tai lausuntokierroksella, voi vielä vaikuttaa. \
  Merkitse action_deadline jos nähtävilläoloajan päättymispäivä on tiedossa.
- "vireilla" — Vireillä, ei vielä päätetty (hakemus jätetty, valmistelu käynnissä)
- "lainvoimainen" — Lainvoimainen tai muuten lopullinen, ei voi enää vaikuttaa

action_deadline: päivämäärä (ISO 8601) jolloin vaikuttamismahdollisuus päättyy. \
null jos ei tiedossa. Tämä on tärkein yksittäinen tieto ammattilaiselle.

Säännöt:
- Otsikko suomeksi, konkreettinen ja toimintakelpoinen (max 100 merkkiä). \
  Kerro MITÄ päätetään ja MISSÄ — ei "kunta käsittelee" vaan "lupa myönnetty X:lle Y:ssä"
- Debrief: 3–6 avainkohtaa suomeksi, tärkein ensin. Ensimmäinen kohta kuvaa \
  mitä voi tehdä (valittaa, lausua, seurata). Keskity: toimintamahdollisuus, \
  mittakaava, hakija/toimija, aikataulu.
- Sisällytä aikajanalle vain asiakirjassa nimenomaisesti mainitut tapahtumat
- Todisteet: suoria lainauksia lähteestä
- entities.applicant: hakijan/toimijan nimi jos mainitaan asiakirjassa
- Ohita (skip: true) jos ei konkreettista ympäristövaikutusta
"""


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Estimate cost in EUR (approximate rates with USD/EUR conversion)."""
    rates = {
        "gpt-4o-mini": {
            "prompt": 0.15 * 0.92 / 1_000_000,
            "completion": 0.60 * 0.92 / 1_000_000,
        },
        "gpt-4o": {
            "prompt": 2.50 * 0.92 / 1_000_000,
            "completion": 10.00 * 0.92 / 1_000_000,
        },
    }
    rate = rates.get(model, rates["gpt-4o-mini"])
    return prompt_tokens * rate["prompt"] + completion_tokens * rate["completion"]


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to *max_chars*, appending a marker when trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated ...]"
