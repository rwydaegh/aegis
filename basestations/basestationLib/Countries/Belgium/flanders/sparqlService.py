try:
    from .configuratie import *
except:
    from configuratie import *

import requests
import json
import os, sys
from threading import Lock

# Import robust HTTP utilities
try:
    from ....utils.http import create_session
except ImportError:
    from basestationLib.utils.http import create_session

try:
    from model import *
except:
    from .model import *


class SparqlService:
    """Service for querying SPARQL endpoints with connection pooling and retry logic."""

    TIMEOUT_LONG = 180
    TIMEOUT_SHORT = 60
    DEBUG = False
    
    # Class-level session for connection pooling (shared across all instances)
    _session = None
    _session_lock = Lock()

    def __init__(self, sparqlEndpoint: str):
        """Initialize SPARQL service with endpoint URL."""
        self.sparqlEndpoint = sparqlEndpoint
        if SparqlService._session is None:
            SparqlService._session = self._create_session()
    
    @staticmethod
    def _create_session() -> requests.Session:
        """Create a session with robust retry strategy and connection pooling."""
        # Use robust HTTP session with connection pooling
        session = create_session(
            retries=3,
            pool_maxsize=20,
            headers={'Accept': 'application/sparql-results+json'}
        )
        return session

    def get_antenna_count(self) -> int:
        """Get total count of antennas with location, technology and provider."""
        query = """
            PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
            PREFIX locn: <http://www.w3.org/ns/locn#>
            PREFIX prov: <http://www.w3.org/ns/prov#>

            SELECT (COUNT(?antenne) as ?aantal)
            WHERE {
                ?antenne a antenne:Zendantenne .
                ?antenne locn:geometry ?geometry .
                ?antenne antenne:antennetechnologie ?tech .
                ?antenne prov:actedOnBehalfOf ?operator .
            }
        """

        try:
            records = self.__run_query(query, self.TIMEOUT_LONG)
            count = int(records['results']['bindings'][0]['aantal']['value'])
            print(f"{count} antennas to retrieve")
            return count
        except Exception as e:
            print(f"Error getting antenna count: {e}")
            return -1

    def _build_limit_offset_clause(self, limit=None, offset=None) -> str:
        """Build LIMIT and OFFSET clause."""
        clause = ""
        if limit is not None:
            clause += f"LIMIT {int(limit)}\n"
        if offset is not None:
            clause += f"OFFSET {int(offset)}\n"
        return clause

    def _build_tech_filter(self, tech=None) -> str:
        """Build technology filter clause."""
        if tech is None:
            return ""
        return f"?antenne antenne:antennetechnologie <https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/{str(tech)}> ."

    def get_antenna_extended(self, limit=None, offset=None, tech=None):
        """Get extended antenna data with optional filtering."""
        tech_filter = self._build_tech_filter(tech)
        limit_offset = self._build_limit_offset_clause(limit, offset)

        query = f"""
        PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
        PREFIX locn: <http://www.w3.org/ns/locn#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX dossier: <https://data.omgeving.vlaanderen.be/ns/dossier#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>
        SELECT ?antenne ?label ?geometry ?azimut ?tech ?operator ?dossiertype ?dossiertype_label ?dossier ?dossier_label ?goedkeuring_tijdstip ?intrekking_tijdstip ?site ?site_label
        WHERE {{
            ?goedkeuring a <https://data.omgeving.vlaanderen.be/ns/dossier#Goedkeuren> .
            ?goedkeuring prov:generated ?conformiteitsattest .
            ?goedkeuring prov:endedAtTime ?goedkeuring_tijdstip .
            ?conformiteitsattest dossier:certifieert ?antenne .
            ?conformiteitsattest dossier:behoortTotProcedurestap ?procedurestap .
            ?procedurestap dossier:behoortTotDossier ?dossier .
            ?dossier dcterms:type ?dossiertype .
            ?dossier rdfs:label ?dossier_label .
            ?dossiertype skos:inScheme <https://data.zendantennes.omgeving.vlaanderen.be/id/conceptscheme/antenne_dossier_type> .
            ?dossiertype skos:prefLabel ?dossiertype_label .
            {tech_filter}
            ?antenne rdfs:label ?label .
            ?antenne locn:geometry ?geometry .
            ?antenne antenne:antennetechnologie ?tech .
            ?antenne prov:actedOnBehalfOf ?operator .
            ?antenne prov:atLocation ?site .
            ?site rdfs:label ?site_label .
            ?antenne waarde:azimut ?t_azimut .
            ?t_azimut rdf:value ?azimut .
            OPTIONAL {{
                ?conformiteitsattest prov:wasInvalidatedBy ?intrekking .
                ?intrekking prov:endedAtTime ?intrekking_tijdstip .
            }}
        }}
        {limit_offset}
        """

        records = self.__run_query(query, self.TIMEOUT_LONG)
        return self.__to_antennas_list(records)


    def get_antenna_locations(self, limit=None, offset=None, tech=None):

        tech_filter = ""
        if tech is not None:
            tech_filter = "?antenne antenne:antennetechnologie <https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/"+str(tech)+"> ."

        limit_filter = ""
        if limit is not None:
            limit_filter = "LIMIT " + str(limit)

        offset_filter = ""
        if offset is not None:
            offset_filter = "OFFSET " + str(offset)

        query = """

                PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
                PREFIX locn: <http://www.w3.org/ns/locn#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX prov: <http://www.w3.org/ns/prov#>
                SELECT ?antenne ?label ?geometry ?tech ?operator
                WHERE
                {
                    ?antenne rdfs:label ?label .
                    ?antenne locn:geometry ?geometry .
                    ?antenne antenne:antennetechnologie ?tech .
                    ?antenne prov:actedOnBehalfOf ?operator .
                    %s
                }
                %s
                %s

                """ %(tech_filter, limit_filter, offset_filter)

        # print(query)

        try:
            records = self.__run_query(query, self.TIMEOUT_LONG)
            return self.__to_antennas_list(records)
        except:
            return []

    def get_antenna_locations_extended(self, limit=None, offset=None, tech=None):

        tech_filter = ""
        if tech is not None:
            tech_filter = "?antenne antenne:antennetechnologie <https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/" + str(
                tech) + "> ."

        limit_filter = ""
        if limit is not None:
            limit_filter = "LIMIT " + str(limit)

        offset_filter = ""
        if offset is not None:
            offset_filter = "OFFSET " + str(offset)

        query = """

                PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
                PREFIX locn: <http://www.w3.org/ns/locn#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                PREFIX prov: <http://www.w3.org/ns/prov#>
                PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>
                SELECT ?antenne ?label ?type ?azimut ?vermogen ?hoogte ?frequentie ?geometry ?site ?site_label ?tech ?operator
                WHERE
                {
                    ?stralen a antenne:Stralen .
                    ?stralen prov:generated ?straling .
                    ?stralen prov:wasAssociatedWith ?antenne .
                    %s
                    {
                        SELECT *
                        WHERE
                        {
                            ?antenne antenne:antennetype ?type .
                            ?antenne antenne:antennetechnologie ?tech .
                            ?antenne rdfs:label ?label .
                            ?antenne locn:geometry ?geometry .
                            ?antenne prov:atLocation ?site .
                            ?site rdfs:label ?site_label .
                            ?antenne prov:actedOnBehalfOf ?operator .
                        }
                    }
                    {
                        SELECT *
                        WHERE
                        {
                            ?antenne waarde:vermogen ?t_vermogen .
                            ?antenne waarde:azimut ?t_azimut .
                            ?antenne waarde:ophangingshoogte ?t_ophangingshoogte .
                            ?straling waarde:frequentie ?t_frequentie .
                            ?t_azimut rdf:value ?azimut .
                            ?t_vermogen rdf:value ?vermogen .
                            ?t_ophangingshoogte rdf:value ?hoogte .
                            ?t_frequentie rdf:value ?frequentie .
                        }
                    }
                }
                %s
                %s

                """ % (tech_filter, limit_filter, offset_filter)

        #print(query)

        try:

            records = self.__run_query(query, self.TIMEOUT_LONG)

            return self.__to_antennas_list(records)
        except:
            return []

    def get_technologies(self):

        query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
            SELECT ?technologie ?label
            WHERE {
              ?technologie a antenne:Antennetechnologie .
              OPTIONAL {
                ?technologie rdfs:label ?label .
              }
            }
        """

        records = self.__run_query(query)
        return self.__to_technology_list(records)


    def __to_technology_list(self, records):

        technologies = []

        if records is not None:
            for record in records['results']['bindings']:
                try:
                    technology = Technology()
                    technology.id = record['technologie']['value']
                    if 'label' in record:
                        technology.label = record['label']['value']
                    elif technology.id in Config.DEFAULT_TECHNOLOGY_LABELS:
                        technology.label = Config.DEFAULT_TECHNOLOGY_LABELS[technology.id]
                    else:
                        technology.label = 'Onbekend'
                    technologies.append(technology)
                except:
                    # some required attribute was missing, just skip this one
                    print(sys.exc_info())
                    print(sys.exc_traceback)
                    pass

        technologies.sort(key=lambda x: x.label)
        return technologies

    def get_dempingsfactoren(self):

        query = """

            PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
            PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?dempingsfactor ?label ?vanfrequentie ?totfrequentie ?factor
            WHERE
            {
                ?dempingsfactor a antenne:Dempingsfactor ;
                rdfs:label ?label .
                ?dempingsfactor waarde:vanfrequentie ?t_vanfrequentie .
                ?dempingsfactor waarde:totfrequentie ?t_totfrequentie .
                ?t_vanfrequentie rdf:value ?vanfrequentie .
                ?t_totfrequentie rdf:value ?totfrequentie .
                ?dempingsfactor rdf:value ?factor
            }

            ORDER BY ASC(?label)

        """

        records = self.__run_query(query)
        return self.__to_dempingsfactor_list(records)

    def get_operators(self):

        query = """

            PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?operator ?label ?identifier
            WHERE
            {
                ?operator a antenne:Operator ;
                dcterms:identifier ?identifier ;
                rdfs:label ?label .
            }

            ORDER BY ASC(?label)

        """

        records = self.__run_query(query)
        return self.__to_operator_list(records)

    def get_dossiertypes(self):

        query = """
        	PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT ?dossiertype ?label
            WHERE
            {
  				?dossiertype a skos:Concept .
  				?dossiertype skos:inScheme <https://data.zendantennes.omgeving.vlaanderen.be/id/conceptscheme/antenne_dossier_type> .
                ?dossiertype skos:prefLabel ?label
            }

            ORDER BY ASC(?label)

        """

        records = self.__run_query(query)
        return self.__to_dossiertypes_list(records)

    def set_debug(self, debug):
        self.DEBUG = debug

    def get_all_for(self, url):

        query = """
            SELECT ?predicate ?object
            WHERE {
                <%s> ?predicate ?object
            }
        """ %(url)

        q = self.__run_query(query)
        # print(q.content)

    def get_antennas2(self):
        query = """

        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        # Aantal antennes van een bepaald type per operator
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>
        SELECT *
        WHERE {
        GRAPH <https://data.zendantennes.omgeving.vlaanderen.be/id/graph/zendantenne-data-publiek>{
            ?antenne a antenne:Zendantenne;
            antenne:antennetype ?antennetype;
            rdfs:label ?label;
            waarde:vermogen ?t_vermogen;
            waarde:azimut ?t_azimut;
            waarde:mechanischetilt ?t_tilt;
            waarde:ophangingshoogte ?t_ophangingshoogte;
            prov:actedOnBehalfOf ?op .
            ?op rdfs:label ?operator .
            ?antennetype rdfs:label ?type_antenne .
            ?t_vermogen rdf:value ?vermogen .
            ?t_azimut rdf:value ?azimut .
            ?t_tilt rdf:value ?mechtilt .
            ?t_ophangingshoogte rdf:value ?hoogtemidden .
          }
        }

        LIMIT 100

        """

        records = self.__run_query(query, self.TIMEOUT_LONG)
        return self.__to_antennas_list(records)

    def __to_dempingsfactor_list(self, records):

        dempingsfactoren = []

        if records is not None:
            for record in records['results']['bindings']:
                try:
                    dempingsfactor = Dempingsfactor()
                    dempingsfactor.id = record['dempingsfactor']['value']
                    dempingsfactor.label = record['label']['value']
                    dempingsfactor.van = record['vanfrequentie']['value']
                    dempingsfactor.tot = record['totfrequentie']['value']
                    dempingsfactor.factor = record['factor']['value']
                    dempingsfactoren.append(dempingsfactor)
                except:
                    # some required attribute was missing, just skip this one
                    print(sys.exc_info())
                    print(sys.exc_traceback)
                    pass

        return dempingsfactoren

    def __to_operator_list(self, records):

        operators = []

        if records is not None:
            for record in records['results']['bindings']:
                try:
                    operator = Operator()
                    operator.id = record['operator']['value']
                    operator.label = record['label']['value']
                    operator.identifier = record['identifier']['value']
                    operators.append(operator)
                except:
                    # some required attribute was missing, just skip this one
                    pass

        return operators

    def __to_dossiertypes_list(self, records):

        dossiertypes = []

        if records is not None:
            for record in records['results']['bindings']:
                try:
                    dossiertype = DossierType()
                    dossiertype.id = record['dossiertype']['value']
                    dossiertype.label = record['label']['value']
                    dossiertypes.append(dossiertype)
                except:
                    # some required attribute was missing, just skip this one
                    pass

        return dossiertypes

    def __to_antennas_list(self, records):

        antennas = []

        for record in records['results']['bindings']:
            antenna = Antenna()
            antenna.id = record['antenne']['value']
            if 'label' in record:
                antenna.label = record['label']['value']
            if 'type' in record:
                antenna.type = record['type']['value']
            if 'geometry' in record:
                antenna.wkt = record['geometry']['value']
            if 'hoogte' in record:
                antenna.height = record['hoogte']['value']
            if 'vermogen' in record:
                antenna.power = record['vermogen']['value']
            if 'frequentie' in record:
                antenna.frequency = record['frequentie']['value']
            if 'tech' in record:
                antenna.technology = record['tech']['value']
            if 'azimut' in record:
                antenna.azimuth = record['azimut']['value']
            if 'maximaleinvloedsstraal' in record:
                antenna.maximaleinvloedsstraal = record['maximaleinvloedsstraal']['value']
            if 'operator' in record:
                antenna.operator = {'id': record['operator']['value'], 'label': ''}
                if 'operator_label' in record:
                    antenna.operator['label'] = record['operator_label']['value']
            if 'goedkeuring_tijdstip' in record:
                antenna.approvaldate = record['goedkeuring_tijdstip']['value']
            if 'intrekking_tijdstip' in record:
                antenna.withdrawaldate = record['intrekking_tijdstip']['value']
            if 'dossier' in record:
                antenna.dossier = {'id': record['dossier']['value'], 'label': ''}
                if 'dossier_label' in record:
                    antenna.dossier['label'] = record['dossier_label']['value']
            if 'dossiertype' in record:
                antenna.dossiertype = {'id': record['dossiertype']['value'], 'label': ''}
                if 'dossiertype_label' in record:
                    antenna.dossiertype['label'] = record['dossiertype_label']['value']
            if 'site' in record:
                antenna.site = {'id': record['site']['value'], 'label': ''}
                if 'site_label' in record:
                    antenna.site['label'] = record['site_label']['value']
            antennas.append(antenna)

        return antennas

    def __run_query(self, query, timeout=TIMEOUT_SHORT):
        """Execute SPARQL query with connection pooling and retry logic."""
        headers = {'Accept': 'application/sparql-results+json'}
        
        proxies = None
        if Config.PROXY_ENABLED:
            proxies = {}
            for proxy_type, proxy_config in Config.PROXY_MAP.items():
                proxies[proxy_type] = f"{proxy_config['scheme']}://{proxy_config['hostname']}:{proxy_config['port']}"
        
        try:
            response = SparqlService._session.post(
                self.sparqlEndpoint,
                data={'query': query},
                headers=headers,
                timeout=timeout,
                proxies=proxies
            )
            
            if response.status_code >= 300:
                print(f"SPARQL service error. Status: {response.status_code}")
                print(response.text)
                return None
            
            js = response.json()
            
            if self.DEBUG:
                debug_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Output.txt")
                with open(debug_file, "w") as f:
                    f.write(json.dumps(js, indent=4))
            
            return js
        
        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in __run_query: {e}")
            return None

    def describe(self, url):

        query = """
        DESCRIBE <%s>
        """ %(url)

        return self.__run_query(query)
