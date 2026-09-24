"""SHC DE editor backend. Importing this package never imports Qt."""
from .document import MapDocument, MapReader, MapWriter, CommandHistory
from .geometry import MapGeometry
from .services import TerrainService, HeightService, EntityService, MapValidator
from .templates import TemplateLibrary
from .patterns import Pattern, PatternLibrary
from .buildings import BuildingService
from .version import __version__
