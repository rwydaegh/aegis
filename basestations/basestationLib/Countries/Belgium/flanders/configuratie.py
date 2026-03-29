import os


class Config:
    JAVA_HOME = os.environ.get('JAVA_HOME', '')
    JAVA_STRALING_JAR = 'zendantennes-qgis.jar'
    JAVA_LOGGING_PROPERTIES = 'logging.properties'

    PROXY_ENABLED = False
    PROXY_MAP = {
        'http': {
            'scheme': 'http',
            'hostname': 'server',
            'port': '8080'
        },
        'https': {
            'scheme': 'https',
            'hostname': 'server',
            'port': '8443'
        }
    }

    SPARQL_ENDPOINT = "https://data.zendantennes.omgeving.vlaanderen.be/sparql"
    SPARQL_ANTENNAS_PER_QUERY = 10000
    SPARQL_SOURCE_CRS = "EPSG:4326"
    SPARQL_DEST_CRS = "EPSG:31370"

    TECHNOLOGY_5G_URI = 'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/6'

    RADIUS_DEFAULT = 1000
    RADIUS_TECHNOLOGY = {
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/1': 2000,
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/2': 2000,
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/3': 2000,
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/4': 2000,
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/5': 2000,
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/6': 2000
    }

    RENDER_SCALE = 1.0

    NORM_LEGENDE = (
        #('0.0 - 0.1', 0.01, 0.1, '#ffffff'),
        ('0.1 - 0.2', 0.1, 0.2, '#e6e6ff'),
        ('0.2 - 0.3', 0.2, 0.3, '#ccccff'),
        ('0.3 - 0.4', 0.3, 0.4, '#b3b3ff'),
        ('0.4 - 0.5', 0.4, 0.5, '#9999ff'),
        ('0.5 - 0.6', 0.5, 0.6, '#8080ff'),
        ('0.6 - 0.7', 0.6, 0.7, '#6666ff'),
        ('0.7 - 0.8', 0.7, 0.8, '#4d4dff'),
        ('0.8 - 0.9', 0.8, 0.9, '#3333ff'),
        ('0.9 - 1.0', 0.9, 1.0, '#1a1aff'),
        ('> 1.0', 1.0, 99, '#0000ff')
    )

    DEFAULT_TECHNOLOGY_LABELS = {
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/1': '4G',
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/2': '3G',
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/3': '2G',
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/4': 'Andere',
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/5': 'Microwave',
        'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetechnologie/6': '5G'
    }

    EXTRA_5G_ANTENNA = {
        'types': [
            {
                'id': 'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetype/265236475/0',
                'label': 'ASI4518R42v06_n35Tilt(Min2-Max12)',
                'default_power': 52.5,
                'default_frequency': 3750,
                'min_frequency': 3500,
                'max_frequency': 3800
            },
            {
                'id': 'https://data.zendantennes.omgeving.vlaanderen.be/id/antennetype/264061586/0',
                'label': 'JB_5980470PG_R1_Tilt(Min2-Max10)',
                'default_power': 52.5,
                'default_frequency': 763,
                'min_frequency': 694,
                'max_frequency': 790
            }
        ]
    }
