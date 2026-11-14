"""Assemble the public raster attachment of a recorded run. No ROS imports.

The recorder sees the immutable prior and, for every map version, the batch
that the mapping provider publishes under one stamp (docs/ICD.md, section 5):
metadata, belief, sigma and the observed mask. A version is kept only when its
metadata and all three layers share that stamp; layers may arrive before or
after their metadata, and the batch is repeated, so they are buffered by stamp.
Nothing is interpolated, resampled or filled in: a version whose batch never
completes is simply absent, and the offline oracle then refuses the package.

The output is the `mge-public-rasters-1.0.0` attachment of
docs/REPLAY_CONTRACT.md. It only ever holds public layers; the evaluator
reference never travels on these topics and is never recorded.
"""
import math

SCHEMA = 'mge-public-rasters-1.0.0'
FILE = 'public_rasters.json'
GEOMETRY = ('dataset_id', 'rows', 'cols', 'origin_x_m', 'origin_y_m',
            'resolution_m', 'crs', 'origin_lat_deg', 'origin_lon_deg', 'vertical_datum')
LAYERS = ('belief', 'sigma', 'observed')
MAX_PENDING_STAMPS = 8      # repeated batches of a few versions, never the whole run


class RasterInputError(ValueError):
    """A layer that cannot be recorded as it is; it is dropped, not repaired."""


def _stamp(header):
    stamp = header['stamp']
    return stamp['sec'], stamp['nanosec']


def height_cells(values, nodata, layer):
    """float32 cells to JSON: NoData (NaN or the declared sentinel) is null."""
    out = []
    for value in values:
        if math.isnan(value) or (nodata is not None and value == nodata):
            out.append(None)
        elif math.isinf(value):
            raise RasterInputError(f'{layer}: infinite cell value')
        elif layer == 'sigma' and value < 0:
            raise RasterInputError('sigma: negative cell value')
        else:
            out.append(value)
    return out


def observed_cells(mask):
    """Indices of the cells a mono8 observed mask marks with 1."""
    if any(v not in (0, 1) for v in mask):
        raise RasterInputError('observed: mask values must be 0 or 1')
    return [i for i, v in enumerate(mask) if v == 1]


class PublicRasterAssembler:

    def __init__(self, run_id):
        self.run_id = run_id
        self.meta = None            # latest metadata, for geometry and NoData
        self.prior = None
        self.stamps = {}            # map version -> stamp of its batch
        self.versions = {}          # str(map version) -> complete layers
        self.pending = {}           # stamp -> {layer: raw values}
        self.done = set()           # stamps of completed versions

    def _geometry(self):
        return {k: self.meta[k] for k in GEOMETRY}

    def _check_shape(self, rows, cols, length, layer):
        if self.meta is not None and (rows, cols) != (self.meta['rows'], self.meta['cols']):
            raise RasterInputError(f'{layer}: {rows} x {cols} differs from the metadata grid')
        if length != rows * cols:
            raise RasterInputError(f'{layer}: {length} cells for a {rows} x {cols} grid')

    def on_meta(self, meta):
        """Metadata of one map version, already JSON-converted by the gateway.

        Returns True when the attachment changed.
        """
        if meta.get('run_id') != self.run_id:
            return False
        if self.meta is not None and self._geometry() != {k: meta[k] for k in GEOMETRY}:
            raise RasterInputError('geometry changed within the run; a new dataset needs a new run')
        version, stamp = meta['map_version'], _stamp(meta['header'])
        known = self.stamps.get(version)
        if known is not None and known != stamp:
            raise RasterInputError(f'map version {version} arrived with a second stamp')
        if any(v != version and s == stamp for v, s in self.stamps.items()):
            raise RasterInputError(f'stamp of map version {version} is reused')
        self.meta = meta
        self.stamps[version] = stamp
        return self._complete()

    def on_prior(self, rows, cols, values):
        """The immutable public prior heights, row-major float32 values.

        Kept raw: its NoData sentinel is known only once metadata arrives.
        """
        self._check_shape(rows, cols, len(values), 'prior')
        values = list(values)
        height_cells(values, None, 'prior')            # reject infinities now
        if self.prior is not None:
            if len(values) != len(self.prior) or any(
                    a != b and not (math.isnan(a) and math.isnan(b))
                    for a, b in zip(values, self.prior)):
                raise RasterInputError('prior: the immutable prior changed within the run')
            return False
        self.prior = values
        return self.ready()

    def on_layer(self, layer, header, rows, cols, values):
        """belief/sigma as float32 values, observed as mono8 values."""
        if layer not in LAYERS:
            raise RasterInputError(f'unknown layer {layer!r}')
        if header.get('frame_id') != 'map':
            raise RasterInputError(f'{layer}: frame {header.get("frame_id")!r} is not map')
        self._check_shape(rows, cols, len(values), layer)
        stamp = _stamp(header)
        if stamp in self.done:
            return False                # a repeat of a complete batch
        self.pending.setdefault(stamp, {})[layer] = (rows, cols, list(values))
        while len(self.pending) > MAX_PENDING_STAMPS:
            del self.pending[min(self.pending)]
        return self._complete()

    def _complete(self):
        changed = False
        for version, stamp in sorted(self.stamps.items()):
            layers = self.pending.get(stamp, {})
            if str(version) in self.versions or set(layers) != set(LAYERS):
                continue
            nodata = self.meta['nodata_value']
            for layer, (rows, cols, values) in layers.items():
                self._check_shape(rows, cols, len(values), layer)
            self.versions[str(version)] = {
                'belief': height_cells(layers['belief'][2], nodata, 'belief'),
                'sigma': height_cells(layers['sigma'][2], nodata, 'sigma'),
                'observed': observed_cells(layers['observed'][2]),
            }
            del self.pending[stamp]
            self.done.add(stamp)
            changed = True
        return changed and self.ready()

    def ready(self):
        return self.meta is not None and self.prior is not None and bool(self.versions)

    def attachment(self):
        """The attachment, or None until the prior and one version are complete."""
        if not self.ready():
            return None
        return {
            'schema_version': SCHEMA,
            'run_id': self.run_id,
            'dataset_id': self.meta['dataset_id'],
            'rows': self.meta['rows'],
            'cols': self.meta['cols'],
            'terrain_geometry': self._geometry(),
            'prior': height_cells(self.prior, self.meta['nodata_value'], 'prior'),
            'versions': {k: self.versions[k] for k in sorted(self.versions, key=int)},
        }
