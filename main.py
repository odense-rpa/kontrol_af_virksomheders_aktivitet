import asyncio
import logging
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

from automation_server_client import AutomationServer, Workqueue, WorkItemError, Credential
from momentum_client.manager import MomentumClientManager
from process.models import Virksomhed
from pydantic import ValidationError
from odk_tools.tracking import Tracker

load_dotenv()

tracker: Tracker

momentum = None
proces_navn = "kontrol af virksomhedsaktivitet"

async def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    #filter finder alle virksomder som ikke har en aktiv markering som er en af følgende:
    #kontakt - virksomhedsbank, partnerskab - virksomhedsbank, samarbejde - virksomhedsbank og tjek til virksomhedsbank
    #Virksomheden skal også være aktiv
    #Virksomheden skal være i Odense kommune
    #Virksomheden skal have 2 eller flere ansatte
    filter  = [
    {
        "customFilter": "exclude;active",
        "fieldName": "tags/id",
        "values": [
            None,
            None,
            None,
            None,
            "2078ac36-b687-4723-bed7-2445e5c30a6f",
            "aa705e32-6388-4a9a-b4e4-3140fd529834",
            "fa1a14f3-7b57-44d3-b784-fb44cef71866",
            "ed5a3f7e-dd8c-41a5-974a-6d7b4f833d93",
            "30373c64-75ae-466d-8d1c-04073eef360d"
        ]
    },
    {
        "customFilter":"",
        "fieldName":"municipalityId",
        "values":[
            "461"
        ]
    },
    {
        "customFilter":"",
        "fieldName":"isActive",
        "values":[
            "true"
        ]
    },
    {
        "customFilter":"",
        "fieldName":"numberOfEmployees",
        "values":[
            "range", "[{\"from\":2}]"
        ]
    }
    ]

    # Hent virksomheder
    virksomheder_data = momentum.virksomheder.hent_virksomheder(filters=filter)
    virksomheder = virksomheder_data["data"]

    for virksomhed in virksomheder:

        # Tjek om virksomheden har "Passiv - virksomhedsbank" tag
        har_passiv_markering = False
        if "tags" in virksomhed and virksomhed["tags"]:
            har_passiv_markering = any(
                tag.get("title", "").strip() == "Passiv - Virksomhedsbank" 
                for tag in virksomhed["tags"]
            )

        kø_item ={
            "cvr": virksomhed["cvr"],
            "pNummer": virksomhed["pNumber"],
            "virksomhedsnavn": virksomhed["displayName"].strip(),
            "virksomhedsreferenceId": virksomhed["productionUnitId"],
            "aktiv": virksomhed["isActive"],
            "kommunekode": int(virksomhed["municipalityId"]),
            "har_passiv_markering": har_passiv_markering
        }

        try:
            item = Virksomhed(**kø_item)

            workqueue.add_item(item.model_dump(), item.pNummer)
            logger.info(f"Virksomhed tilføjet til kø, pnummer: {item.pNummer}")
        except ValidationError as e:
            logger.error(f"kunne ikke validere virksomhedsformat, pnummer:{item.pNummer}, fejl: {e}")



async def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Starter behandling af items")

    for item in workqueue:
        with item:
            try:

                item_data = Virksomhed(**item.data) 
                logger.info(f"Behandler aktivitet for virksomhed med pnummer: {item_data.pNummer}")

                # Calculate date 6 months and 1 day back from now
                six_months_back = datetime.now() - relativedelta(months=6, days=1)
                # Format to match the required datetime format with fixed time at 22:00
                formatted_date = six_months_back.strftime("%Y-%m-%dT22:00:00.000Z")
                
                Borgere_i_tilbud_filter = [
                    {
                        "fieldName": "end",
                        "values": [
                            formatted_date,
                            None,
                            False
                        ]
                    }
                ]

                jobordre_filter = [
                    {
                        "fieldName": "updatedDate",
                        "values": [
                            formatted_date,
                            None,
                            False
                        ]
                    },
                    {
                        "values": item_data.virksomhedsreferenceId,
                        "fieldName": "providerId"
                    }
                ]

                borgere_i_tilbud = momentum.virksomheder.find_borgere_i_tilbud_på_virksomhed(item_data.virksomhedsreferenceId, Borgere_i_tilbud_filter)
                jobordre = momentum.virksomheder.find_jobordre_på_virksomhed(item_data.virksomhedsreferenceId, jobordre_filter)

                # Hvis der er mere end en aktivitet skal virksomheden have den korrekte markering
                antal_aktiviter = len(borgere_i_tilbud["data"]) + len(jobordre["data"])
                if antal_aktiviter > 1:
                    
                    logger.info("Mere end en aktivitet fundet på virksomhed")
                    
                    if item_data.har_passiv_markering:
                        #Hvis virksomhed har en "passiv - virksomhed" markering skal denne markering
                        momentum.markeringer.opret_markering(
                            markeringsnavn="Tjek til virksomhedsbank",
                            referenceId=item_data.virksomhedsreferenceId,
                            start_dato=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                        )
                        logger.info("Markering 'Tjek til virksomhedsbank' oprettet på virksomhed")
                    else:
                        #ellers skal den have den markering
                        momentum.markeringer.opret_markering(
                            markeringsnavn="Tjek til virksomhedsbank - ny portefølje",
                            referenceId=item_data.virksomhedsreferenceId,
                            start_dato=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                        )
                        logger.info("Markering 'Tjek til virksomhedsbank - ny portefølje' oprettet på virksomhed")
                    #afregn opgave
                    tracker.track_task(proces_navn)
                else:
                    #afregn delopgave
                    tracker.track_partial_task(proces_navn)

            except WorkItemError as e:
                # A WorkItemError represents a soft error that indicates the item should be passed to manual processing or a business logic fault
                logger.error(f"Error processing item: {item_data.pNummer}. Error: {e}")
                item.fail(str(e))


if __name__ == "__main__":
    ats = AutomationServer.from_environment()

    workqueue = ats.workqueue()

    # Initialize external systems for automation here..
    momentum_credential = Credential.get_credential("Momentum - produktion")
    momentum = MomentumClientManager(
        base_url=momentum_credential.data["base_url"],
        client_id=momentum_credential.username,
        client_secret=momentum_credential.password,
        api_key=momentum_credential.data["api_key"],
        resource=momentum_credential.data["resource"],
    )

    tracker_credentials = Credential.get_credential("Odense SQL Server")

    tracker = Tracker(
        username=tracker_credentials.username,
        password=tracker_credentials.password
    )

    # Queue management
    if "--queue" in sys.argv:
        workqueue.clear_workqueue("new")
        asyncio.run(populate_queue(workqueue))
        exit(0)

    # Process workqueue
    asyncio.run(process_workqueue(workqueue))
