import json
import math
import urllib.parse

from area import area as compute_area
from haversine import Unit
from haversine.haversine import get_avg_earth_radius

EARTH_RADIUS = get_avg_earth_radius(Unit.METERS)
EARTH_PERIMETER = 2 * math.pi * EARTH_RADIUS


def latitude_radians_to_meters(radians: float) -> float:
    return EARTH_RADIUS * radians


def latitude_meters_to_radians(meters: float) -> float:
    return meters / EARTH_RADIUS


def longitude_meters_to_radians(meters: float, latitude_rad: float) -> float:
    return meters / (EARTH_RADIUS * math.cos(latitude_rad))


def longitude_radians_to_meters(radians: float, latitude_rad: float) -> float:
    return (EARTH_RADIUS * math.cos(latitude_rad)) * radians


def area_from_integral(latitude_rad: float, longitude_span_rad: float) -> float:
    return EARTH_RADIUS ** 2 * longitude_span_rad * math.sin(latitude_rad)


def latitude_from_area(area: float, longitude_span_rad: float) -> float:
    return math.asin(area / (EARTH_RADIUS ** 2 * longitude_span_rad))


class Cell:
    EXPECTED_EDGE_LENGTH_METERS = 30
    REFERENCE_LATITUDE_RAD = 0.8177264  # 46.85227151642656°

    def __init__(self, lat_index: int, lon_index: int):
        self.lat_index = lat_index
        self.lon_index = lon_index
        latitude_rad = latitude_from_area((self.lat_index + 0.5) * self.expected_area(), self.longitude_rad_increment())
        self.latitude_rad_increment = self.compute_latitude_rad_increment(latitude_rad)

    @classmethod
    def expected_area(cls):
        return cls.EXPECTED_EDGE_LENGTH_METERS ** 2

    @classmethod
    def from_lat_lng(cls, latitude_deg: float, longitude_deg: float):
        latitude_rad = math.radians(latitude_deg)
        longitude_rad = math.radians(longitude_deg)
        lon_index = int(math.floor(longitude_rad / cls.longitude_rad_increment()))
        lat_index = int(
            math.floor(area_from_integral(latitude_rad, cls.longitude_rad_increment()) / cls.expected_area()))
        return cls(lat_index, lon_index)

    @classmethod
    def compute_latitude_rad_increment(cls, latitude_rad):
        # approximation (because sin(lat_i) ~ lat_i and cos(lat_i) ~ 1)
        # cls.expected_area() / (EARTH_RADIUS ** 2 * cls.longitude_rad_increment() * math.cos(latitude_rad))
        return math.asin(cls.expected_area() / (EARTH_RADIUS ** 2 * cls.longitude_rad_increment()) + math.sin(
            latitude_rad)) - latitude_rad

    @classmethod
    def longitude_rad_increment(cls):
        return longitude_meters_to_radians(cls.EXPECTED_EDGE_LENGTH_METERS, cls.REFERENCE_LATITUDE_RAD)

    @classmethod
    def index_to_point(cls, lat_index, lon_index):
        return (
            math.degrees(latitude_from_area(lat_index * cls.expected_area(), cls.longitude_rad_increment())),
            math.degrees(lon_index * cls.longitude_rad_increment())
        )

    @property
    def min_point(self):
        return self.index_to_point(self.lat_index, self.lon_index)

    @property
    def max_point(self):
        return self.index_to_point(self.lat_index + 1, self.lon_index + 1)

    @property
    def geojson_coordinates(self):
        return [
            [self.min_point[1], self.min_point[0]],
            [self.min_point[1], self.max_point[0]],
            [self.max_point[1], self.max_point[0]],
            [self.max_point[1], self.min_point[0]],
            [self.min_point[1], self.min_point[0]],
        ]

    @property
    def geojson_obj(self):
        return json.dumps({'type': 'Polygon', 'coordinates': [self.geojson_coordinates]})

    def get_geojson_url(self):
        data = urllib.parse.quote(json.dumps({'type': 'Polygon', 'coordinates': [self.geojson_coordinates]}))
        return f'http://geojson.io/#data=data:application/json,{data}'

    @property
    def area(self):
        return compute_area(self.geojson_obj)
