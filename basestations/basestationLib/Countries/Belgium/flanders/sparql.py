import os, sys
import importlib.util
import requests
import json
from threading import Lock

# Import robust HTTP utilities
try:
    from ....utils.http import create_session
except ImportError:
    from basestationLib.utils.http import create_session


# Global session pool for SPARQL queries with connection pooling
_sparql_session = None
_sparql_session_lock = Lock()


def _get_shared_session() -> requests.Session:
    """Get or create a shared session for SPARQL queries (thread-safe)."""
    global _sparql_session
    
    if _sparql_session is None:
        with _sparql_session_lock:
            if _sparql_session is None:
                # Use robust HTTP session with retry logic and connection pooling
                _sparql_session = create_session(
                    retries=3,
                    pool_maxsize=20,
                    headers={
                        'Accept': 'application/sparql-results+json',
                        'Connection': 'keep-alive'
                    }
                )
    
    return _sparql_session


def import_sparql_service_from_plugin(plugin_path=os.path.dirname(__file__)):
    """Dynamically import sparqlService from specified path."""
    sparql_service_file_path = os.path.join(plugin_path, "sparqlService.py")
    
    if not os.path.exists(sparql_service_file_path):
        print(ImportError(f"Cannot find sparqlService.py at: {sparql_service_file_path}"))
        plugin_path = input("Provide path to sparqlService.py file: ...")
    
    try:
        spec = importlib.util.spec_from_file_location("sparqlService", sparql_service_file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec from {sparql_service_file_path}")
        
        sparqlService_module = importlib.util.module_from_spec(spec)
        sys.modules["sparqlService"] = sparqlService_module
        
        original_sys_path = list(sys.path)
        sys.path.insert(0, plugin_path)
        try:
            spec.loader.exec_module(sparqlService_module)
        finally:
            sys.path = original_sys_path
        
        return sparqlService_module.SparqlService
    except Exception as e:
        raise ImportError(f"Failed to import SparqlService: {e}")


def execute_sparql_query(endpoint_url: str, query: str, timeout: int = 60) -> list:
    """
    Execute a SPARQL query with connection pooling and retry logic.
    
    Uses a shared session pool to prevent "Too Many Sessions" errors from the endpoint.
    This is critical when making parallel requests.
    
    Args:
        endpoint_url: SPARQL endpoint URL
        query: SPARQL query string
        timeout: Request timeout in seconds (default 60; reduce to fail fast on slow queries)
    
    Returns:
        List of result bindings or empty list on error
    """
    headers = {
        'Accept': 'application/sparql-results+json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Connection': 'keep-alive'  # Enable HTTP connection keep-alive
    }
    
    try:
        session = _get_shared_session()
        response = session.post(endpoint_url, data={'query': query}, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        if 'application/sparql-results+json' not in content_type and 'application/json' not in content_type:
            return []
        
        js = response.json()
        return js.get("results", {}).get("bindings", [])
    
    except requests.exceptions.HTTPError as e:
        pass
    except requests.exceptions.RequestException as e:
        pass
    except json.JSONDecodeError as e:
        pass
    
    return []


# Query builder functions with improved performance and readability

def get_query_antenna_full_details(antenna_uri: str) -> str:
    """Generate SPARQL query for basic antenna details (type URI and mechanical tilt)."""
    return f"""
        PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
        PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX sdmx: <http://purl.org/linked-data/sdmx/2009/attribute#>
        PREFIX qudt: <http://qudt.org/schema/qudt#>

        SELECT ?type ?mechtilt
        WHERE {{
            BIND(<{antenna_uri}> AS ?antenne)
            ?antenne antenne:antennetype ?type .
            OPTIONAL {{
                ?antenne waarde:mechanischetilt ?t_mechtilt .
                ?t_mechtilt rdf:value ?mechtilt .
            }}
        }}
        LIMIT 1
    """

def get_query_antenna_type_details(antenna_type_uri: str) -> str:
    """Generate SPARQL query for antenna type dimensions and beamwidths."""
    return f"""
        PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>

        SELECT ?winst ?breedte ?hoogte ?verticaleopeningshoek ?horizontaleopeningshoek
        WHERE {{
            BIND(<{antenna_type_uri}> AS ?type)
            OPTIONAL {{
                ?type waarde:winst ?t_winst .
                ?t_winst rdf:value ?winst .
            }}
            OPTIONAL {{
                ?type waarde:hoogte ?t_hoogte .
                ?t_hoogte rdf:value ?hoogte .
            }}
            OPTIONAL {{
                ?type waarde:breedte ?t_breedte .
                ?t_breedte rdf:value ?breedte .
            }}
            OPTIONAL {{
                ?type waarde:verticaleopeningshoek ?t_vbeam .
                ?t_vbeam rdf:value ?verticaleopeningshoek .
            }}
            OPTIONAL {{
                ?type waarde:horizontaleopeningshoek ?t_hbeam .
                ?t_hbeam rdf:value ?horizontaleopeningshoek .
            }}
        }}
        LIMIT 1
    """

def get_query_winstverlies(antenna_type_uri: str) -> str:
    """Generate SPARQL query for antenna gain/loss pattern segments."""
    return f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX antenne: <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#>
        PREFIX waarde: <https://data.omgeving.vlaanderen.be/ns/waarde#>

        SELECT ?vanhoek ?tothoek ?winst ?vlak
        WHERE {{
            ?wv a <https://data.zendantennes.omgeving.vlaanderen.be/ns/zendantenne#Antennewinstverlies> .
            ?wv antenne:isAntennewinstverliesVan <{antenna_type_uri}> .
            ?wv waarde:vanhoek ?t_vanhoek .
            ?wv waarde:tothoek ?t_tothoek .
            ?wv waarde:winst ?t_winst .
            ?wv antenne:vlakwinstverlies ?vlak .

            ?t_vanhoek rdf:value ?vanhoek .
            ?t_tothoek rdf:value ?tothoek .
            ?t_winst rdf:value ?winst .
        }}
        ORDER BY ?vlak ?vanhoek
    """
