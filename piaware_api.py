import requests
from geopy import distance
from geographiclib.geodesic import Geodesic

DUMP_1090_IP = "localhost:8080"


def get_request(url):
    res = requests.get(url)
    try:
        return res.json() if res else None
    except Exception as e:
        print(e)
        return None


class Aircraft:
    def __init__(self, data):
        self.JSON = data
        self.id = data.get("hex")
        self.flight = data.get("flight")
        self.barometricAltitude = data.get('alt_baro')
        self.gemoetricAltitude = data.get('alt_geom')
        self.groundSpeed = data.get('gs')
        self.indicatedAirSpeed = data.get('ias')
        self.trueAirSpeed = data.get('tas')
        self.machSpeed = data.get('mach')
        self.track = data.get('track')
        self.track_rate = data.get('track_rate')
        self.roll = data.get('roll')
        self.magneticHeading = data.get('mag_heading')
        self.trueHeading = data.get('true_heading')
        self.barometricAltitudeRate = data.get('baro_rate')
        self.gemoetricAltitudeRate = data.get('geom_rate')
        self.squawk = data.get("squawk")
        self.emergency = data.get('emergency')
        self.emitterCategory = data.get('category')
        self.altimeterSetting = data.get('nav_qnh')
        self.altitudeModeMCP = data.get('nav_altitude_mcp')
        self.altitudeModeFMS = data.get('nav_altitude_fms')
        self.headingMode = data.get('nav_heading')
        self.navigationModes = data.get('nav_modes')
        self.latitude = data.get('lat')
        self.longitude = data.get('lon')
        self.NavIntegrityCategory = data.get('nid')
        self.containmentRadius = data.get('rc')
        self.positionLastUpdated = data.get('seen_pos')
        self.lastSeen = data.get('seen')
        self.adsbVersion = data.get('version')
        self.NICBarometric = data.get('nic_baro')
        self.NavAccuracyPosition = data.get('nac_p')
        self.NavAccuracyVelocity = data.get('nac_v')
        self.SourceIntegrityLevel = data.get('sil')
        self.SourceIntegrityLevelType = data.get('sil_type')
        self.GeomVerticalAccuracy = data.get('gva')
        self.SysDesignAccuracy = data.get('sda')
        self.MLAT = data.get('mlat')
        self.TISB = data.get('tisb')
        self.ModeSMessageCount = data.get('messages')
        self.recentSignalPower = data.get('rssi')

    def distance_from(self, lat: float, lon: float, in_miles=False):
        if self.latitude and self.longitude:
            dist = distance.distance((lat, lon), (self.latitude, self.longitude)).km
            if in_miles:
                dist = dist * 0.621371
            return dist
        return None

    def degrees_from_north(self, lat: float, lon: float):
        if self.latitude and self.longitude:
            angle = Geodesic.WGS84.Inverse(lat, lon, self.latitude, self.longitude)
            return angle['azi1'] if angle['azi1'] > 0 else angle['azi1'] + 360
        return None


class Dump1090:
    def __init__(self, ip_and_port=DUMP_1090_IP):
        self.ip = ip_and_port
        self.baseUrl = 'http://{}/data'.format(ip_and_port)
        self.receiver = None
        self.receiverJSON = None
        self.get_receiver(force_reload=True)
        self.aircraft = []
        self.aircraftJSON = None
        self._stored_aircraft_ids = []
        self.get_all_aircraft(current_only=False)
        self.stats = None
        self.history = None

    def get_all_aircraft(self, current_only=False):
        """
        :param current_only: Delete old/disappeared aircraft from self.aircraft.
        If True, all Aircraft objects re-created. If False, Aircraft objects may have outdated info
        :return: [Aircraft, Aircraft, Aircraft, ...]
        """
        data = get_request('{}/aircraft.json'.format(self.baseUrl))
        if data:
            self.aircraftJSON = data
            if current_only:
                self.aircraft = []
                self._stored_aircraft_ids = []
                for craft in data['aircraft']:
                    self.aircraft.append(Aircraft(craft))
            else:
                for craft in data['aircraft']:
                    # since list has old aircraft, let's not duplicate entries
                    if craft['hex'] and not self._craft_exists(id=craft['hex']):
                        self.aircraft.append(Aircraft(craft))
                        self._stored_aircraft_ids.append(craft['hex'])
            return self.aircraft
        return None

    def _craft_exists(self, id: str = None, current_craft: Aircraft = None):
        if id:
            if id in self._stored_aircraft_ids:
                return True
        if current_craft:
            if current_craft.id in self._stored_aircraft_ids:
                return True
        return False

    def get_receiver(self, force_reload=False):
        if force_reload or not self.receiver:
            data = get_request('{}/receiver.json'.format(self.baseUrl))
            if data:
                self.receiverJSON = data
                self.receiver = Receiver(data)
                return self.receiver
            return None
        return self.receiver

    def get_stats(self, force_reload=False):
        if force_reload or not self.stats:
            data = get_request('{}/stats.json'.format(self.baseUrl))
            if data:
                self.stats = Stats(data)
                return self.stats
            return None
        return self.stats

    def get_history(self, force_reload=False):
        # This function is slow since it's loading 120 different JSON files each time.
        # Use with caution when force reloading
        if force_reload or not self.history:
            print("Loading history. This may take a while, please wait...")
            if not self.receiver:
                self.get_receiver(force_reload=True)
            if self.receiver.historyCount:
                self.history = History(history_count=self.receiver.historyCount, ip_and_port=self.ip)
                return self.history
            return None
        return self.history

    def get_specific_aircraft(self, hex_id: str = None, flight_callsign: str = None, force_reload_aircrafts=False):
        if not hex_id and not flight_callsign:
            raise Exception("'hex_id' or 'flight_callsign' required.")
            return None
        if force_reload_aircrafts or not self.aircraft:
            self.get_all_aircraft()
        for craft in self.aircraft:
            if hex_id:  # match by hex_id, fallback to flight_callsign
                if hex_id == craft.id:
                    return craft
            if flight_callsign:
                if flight_callsign == craft.flight:
                    return craft
        return None


class Receiver:
    def __init__(self, data):
        self.JSON = data
        self.version = data.get('version')
        self.refreshTime = data.get('refresh')
        self.historyCount = data.get('history')
        self.latitude = data.get('lat')
        self.longitude = data.get('lon')


class History:
    def __init__(self, history_count: int = None, ip_and_port=DUMP_1090_IP):
        self.count = history_count
        self.ip = ip_and_port
        self.historyBaseUrl = 'http://{}/data'.format(ip_and_port)
        self.historyFiles = []
        self.aircraft = []
        self.messageCount = 0
        self._stored_aircraft_ids = []
        if self.count and self.historyBaseUrl:
            self._process_history()

    def _process_history(self):
        self.history_files = []
        self.messageCount = 0
        for i in range(0, self.count + 1):
            history_file = HistoryFile('{}/history_{}.json'.format(self.historyBaseUrl, i))
            if history_file.now:
                self.history_files.append(history_file)
                self.messageCount += history_file.messageCount
        self.history_files.sort(key=lambda x: x.now, reverse=True)
        for history_file in self.history_files:
            for craft in history_file.JSON['aircraft']:
                # avoid duplicate entries of aircraft
                if craft['hex'] and not self._craft_exists(id=craft['hex']):
                    self.aircraft.append(Aircraft(craft))
                    self._stored_aircraft_ids.append(craft['hex'])

    def _craft_exists(self, id: str = None, current_craft: Aircraft = None):
        if id:
            if id in self._stored_aircraft_ids:
                return True
        if current_craft:
            if current_craft.id in self._stored_aircraft_ids:
                return True
        return False


class HistoryFile:
    def __init__(self, fileUrl):
        self.fileUrl = fileUrl
        self.JSON = None
        self.now = None
        self.messageCount = 0
        self._load_history_file()

    def _load_history_file(self):
        data = get_request(self.fileUrl)
        if data:
            self.JSON = data
            self.now = data['now']
            self.messageCount = data['messages']


class Stats:
    def __init__(self, data):
        self.JSON = data
        self.total = None
        if data['total']:
            self.total = StatsPeriod(data['total'])
        self.last1min = None
        if data['last1min']:
            self.last1min = StatsPeriod(data['last1min'])
        self.last5min = None
        if data['last5min']:
            self.last5min = StatsPeriod(data['last5min'])
        self.last15min = None
        if data['last15min']:
            self.last15min = StatsPeriod(data['last15min'])
        self.latest = None
        if data['latest']:
            self.latest = StatsPeriod(data['latest'])


class StatsPeriod:
    def __init__(self, data):
        self.JSON = data
        self.start = data.get('start')
        self.end = data.get('end')
        self.local = None
        if data['local']:
            self.local = Local(data['local'])
        self.remote = None
        if data['remote']:
            self.remote = Remote(data['remote'])
        self.cpu = None
        if data['cpu']:
            self.cpu = CPU(data['cpu'])
        self.cpr = None
        if data['cpr']:
            self.cpr = CPR(data['cpr'])
        self.tracks = None
        if data['tracks']:
            self.tracks = Tracks(data['tracks'])
        self.messages = data.get('messages')


class Local:
    def __init__(self, data):
        self.JSON = data
        self.blocksProcessed = data.get('blocks_processed')
        self.blocksDropped = data.get('blocks_dropped')
        self.modeACDecoded = data.get('modeac')
        self.modeSReceived = data.get('modes')
        self.modeSInvalid = data.get('bad')
        self.modeSUnknown = data.get('unknown_icao')
        self.modeSAccepted = data.get('accepted')
        self.averageSignalPower = data.get('signal')
        self.peakSignalPower = data.get('peak_signal')
        self.strongSignalPowerMessageCount = data.get('strong_signals')


class Remote:
    def __init__(self, data):
        self.JSON = data
        self.modeACDecoded = data.get('modeac')
        self.modeSReceived = data.get('modes')
        self.modeSInvalid = data.get('bad')
        self.modeSUnknown = data.get('unknown_icao')
        self.modeSAccepted = data.get('accepted')
        self.HTTPRequestCount = data.get('http_requests')


class CPU:
    def __init__(self, data):
        self.demodulationTime = data.get('demod')
        self.readerTime = data.get('reader')
        self.backgroundTime = data.get('background')


class CPR:
    def __init__(self, data):
        self.JSON = data
        self.surfaceMessages = data.get('surface')
        self.airborneMessages = data.get('airborne')
        self.globalPositionsGood = data.get('global_ok')
        if data.get('global_bad'):
            self.globalBadExceededRange = data['global_bad'].get('global_range')
            self.globalBadExceededSpeed = data['global_bad'].get('global_speed')
        self.globalSkipped = data.get('global_skipped')
        self.localPositionsGood = data.get('local_ok')
        if self.localPositionsGood:
            self.localAircraftRelative = self.localPositionsGood.get('local_aircraft_relative')
            self.localReceiverRelative = self.localPositionsGood.get('local_receiver_relative')
        self.localSkipped = data.get('local_skipped')
        if self.localSkipped:
            self.localSkippedExceededRange = self.localSkipped.get('local_range')
            self.localSkippedExceededSpeed = self.localSkipped.get('local_speed')
        self.filteredMessages = data.get('filtered')


class Tracks:
    def __init__(self, data):
        self.JSON = data
        self.all = data.get('all')
        self.single_message = data.get('single_message')
