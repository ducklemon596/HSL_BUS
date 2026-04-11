"""Bus data models"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class BusPosition:
    """Bus position and heading information"""

    unique_veh_id: str
    lat: float
    long: float
    hdg: int  # heading in degrees
    spd: float  # speed in m/s
    timestamp: str
    route: Optional[str] = None


@dataclass
class BusData:
    """Complete bus data structure from HSL API"""

    # Identification
    desi: str  # Route number (e.g., "37")
    dir: str  # Direction (1 or 2)
    oper: int  # Operator ID (e.g., 22)
    veh: int  # Vehicle number (e.g., 1219)
    unique_veh_id: str  # Unique ID (e.g., "22_1219")

    # Location data
    lat: float  # Latitude
    long: float  # Longitude
    hdg: int  # Heading in degrees (0-360)
    spd: float  # Speed in m/s
    acc: Optional[float] = None  # Acceleration

    # Timestamps
    tst: str  # ISO timestamp (e.g., "2026-02-10T15:32:11.598Z")
    tsi: int  # Unix timestamp (seconds)

    # Route data
    oday: str  # Operating day
    jrn: int  # Journey/trip number
    line: int  # Line code
    start: str  # Departure time
    stop: Optional[str] = None  # Current stop
    route: Optional[str] = None  # Route code

    # Odometer and door
    odo: Optional[float] = None  # Odometer reading
    drst: Optional[int] = None  # Door status (0/1)

    # Other info
    dl: int  # Delay in seconds
    loc: str  # Location method (e.g., "GPS")
    occu: int  # Occupancy (0 = empty, 1+ = occupied)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "desi": self.desi,
            "dir": self.dir,
            "oper": self.oper,
            "veh": self.veh,
            "unique_veh_id": self.unique_veh_id,
            "lat": self.lat,
            "long": self.long,
            "hdg": self.hdg,
            "spd": self.spd,
            "acc": self.acc,
            "tst": self.tst,
            "tsi": self.tsi,
            "oday": self.oday,
            "jrn": self.jrn,
            "line": self.line,
            "start": self.start,
            "stop": self.stop,
            "route": self.route,
            "odo": self.odo,
            "drst": self.drst,
            "dl": self.dl,
            "loc": self.loc,
            "occu": self.occu,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BusData":
        """Create from dictionary"""
        return cls(
            desi=data.get("desi", ""),
            dir=data.get("dir", ""),
            oper=data.get("oper", 0),
            veh=data.get("veh", 0),
            unique_veh_id=data.get("unique_veh_id", ""),
            lat=data.get("lat", 0),
            long=data.get("long", 0),
            hdg=data.get("hdg", 0),
            spd=data.get("spd", 0),
            acc=data.get("acc"),
            tst=data.get("tst", ""),
            tsi=data.get("tsi", 0),
            oday=data.get("oday", ""),
            jrn=data.get("jrn", 0),
            line=data.get("line", 0),
            start=data.get("start", ""),
            stop=data.get("stop"),
            route=data.get("route"),
            odo=data.get("odo"),
            drst=data.get("drst"),
            dl=data.get("dl", 0),
            loc=data.get("loc", "GPS"),
            occu=data.get("occu", 0),
        )
