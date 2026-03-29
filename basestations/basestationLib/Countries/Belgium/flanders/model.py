class Antenna:

    def __init__(self):
        self.id = None
        self.label = None
        self.wkt = None
        self.height = None
        self.technology = None
        self.frequency = None
        self.type = None
        self.azimuth = None
        self.maximaleinvloedsstraal = None
        self.etilt = None
        self.power = None
        self.operator = None
        self.approvaldate = None
        self.withdrawaldate = ''
        self.dossiertype = None
        self.dossier = None
        self.site = None

    def __str__(self):
        out = '';
        out += self.id + "\t"
        out += self.type + "\t"
        out += self.maximaleinvloedsstraal + "\t"
        out += self.azimuth + "\t"
        out += self.etilt + "\t"
        out += self.power + "\t"
        out += self.wkt + "\t"
        return out


class Technology:

    def __init__(self):
        self.id = None
        self.label = None

    def __str__(self):
        return self.id + ' (' + str(self.label) + ')'


class Dempingsfactor:

    def __init__(self):
        self.id = None
        self.label = None
        self.van = None
        self.tot = None
        self.factor = None


class Operator:

    def __init__(self):
        self.id = None
        self.identifier = None
        self.label = None


class DossierType:

    def __init__(self):
        self.id = None
        self.label = None