"""Assemble the public raster attachment of a recorded run. No ROS imports.

The recorder sees the immutable prior and, for every map version, the batch
that the mapping provider publishes under one stamp (docs/ICD.md, section 5):
metadata, belief, sigma and the observed mask. A version is kept only when its
metadata and all three layers share that stamp; layers may arrive before or
after their metadata, and the batch is repeated, so they are buffered by stamp.
Nothing is interpolated, resampled or filled in: a version whose batch never
completes is simply absent, and the offline oracle then refuses the package.

Optionally, the human traversability mask of the same batch adds `impassable`:
the indices of the cells the mapping provider marks forbidden (100) for a human
(observed obstacles, or slopes beyond the human limit). It is an optional
addition to the attachment: a version without it says nothing about obstacles.

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


def impassable_cells(values):
    """Indices of the cells an OccupancyGrid marks forbidden (100); -1 and 0 are not."""
    if any(v not in (-1, 0, 100) for v in values):
        raise RasterInputError('impassable: occupancy values must be -1, 0 or 100')
    return [i for i, v in enumerate(values) if v == 100]


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
        self.prior_shape = None     # (rows, cols) the prior arrived with
        self.stamps = {}            # map version -> stamp of its batch
        self.versions = {}          # str(map version) -> complete layers
        self.pending = {}           # stamp -> {layer: raw values}
        self.done = set()           # stamps of completed versions
        self.impassable = {}        # stamp -> (rows, cols, cells, geometry), optional

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
        # A prior that arrived first was checked only for its cell count.
        mismatch = self.prior is not None and self.prior_shape != (meta['rows'], meta['cols'])
        if mismatch:
            shape = self.prior_shape
            self.prior = self.prior_shape = None
        changed = self._complete()
        if mismatch:
            raise RasterInputError(f'prior: {shape[0]} x {shape[1]} differs from the metadata grid '
                                   f'{meta["rows"]} x {meta["cols"]}; prior dropped')
        return changed

    def on_prior(self, rows, cols, values):
        """The immutable public prior heights, row-major float32 values.

        Kept raw: its NoData sentinel is known only once metadata arrives.
        """
        self._check_shape(rows, cols, len(values), 'prior')
        values = list(values)
        height_cells(values, None, 'prior')            # reject infinities now
        if self.prior is not None:
            if (rows, cols) != self.prior_shape or any(
                    a != b and not (math.isnan(a) and math.isnan(b))
                    for a, b in zip(values, self.prior)):
                raise RasterInputError('prior: the immutable prior changed within the run')
            return False
        self.prior = values
        self.prior_shape = (rows, cols)
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

    def _check_mask_geometry(self, geometry):
        if geometry is None:
            return
        if (len(geometry) != 3 or any(not math.isfinite(v) for v in geometry)
                or geometry[2] <= 0):
            raise RasterInputError('impassable: invalid occupancy grid geometry')
        if self.meta is not None:
            expected = (self.meta['origin_x_m'], self.meta['origin_y_m'],
                        self.meta['resolution_m'])
            if any(not math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)
                   for a, b in zip(geometry, expected)):
                raise RasterInputError('impassable: occupancy geometry differs from metadata')

    def on_impassable(self, header, rows, cols, values, *, geometry=None):
        """Human traversability of one batch (OccupancyGrid values, row-major).

        Optional: attached to its version whether it arrives before or after the
        required layers complete. Returns True when the attachment changed.
        """
        if header.get('frame_id') != 'map':
            raise RasterInputError(f'impassable: frame {header.get("frame_id")!r} is not map')
        self._check_shape(rows, cols, len(values), 'impassable')
        self._check_mask_geometry(geometry)
        stamp = _stamp(header)
        cells = impassable_cells(values)
        for version, known in self.stamps.items():
            layers = self.versions.get(str(version))
            if known == stamp and layers is not None:
                if 'impassable' in layers:
                    if layers['impassable'] != cells:
                        raise RasterInputError('impassable: immutable map version changed')
                    return False
                layers['impassable'] = cells
                return self.ready()
        incoming = (rows, cols, cells, tuple(geometry) if geometry is not None else None)
        if stamp in self.impassable and self.impassable[stamp] != incoming:
            raise RasterInputError('impassable: immutable pending batch changed')
        self.impassable[stamp] = incoming
        while len(self.impassable) > MAX_PENDING_STAMPS:
            del self.impassable[min(self.impassable)]
        return False

    def _complete(self):
        changed = False
        for version, stamp in sorted(self.stamps.items()):
            layers = self.pending.get(stamp, {})
            if str(version) in self.versions or set(layers) != set(LAYERS):
                continue
            nodata = self.meta['nodata_value']
            for layer, (rows, cols, values) in layers.items():
                self._check_shape(rows, cols, len(values), layer)
            mask = self.impassable.get(stamp)
            if mask is not None:
                mask_rows, mask_cols, cells, geometry = mask
                self._check_shape(mask_rows, mask_cols, len(layers['belief'][2]), 'impassable')
                self._check_mask_geometry(geometry)
            self.versions[str(version)] = {
                'belief': height_cells(layers['belief'][2], nodata, 'belief'),
                'sigma': height_cells(layers['sigma'][2], nodata, 'sigma'),
                'observed': observed_cells(layers['observed'][2]),
            }
            if stamp in self.impassable:
                self.versions[str(version)]['impassable'] = self.impassable.pop(stamp)[2]
            del self.pending[stamp]
            self.done.add(stamp)
            changed = True
        return changed and self.ready()

    def ready(self):
        return (self.meta is not None and self.prior is not None and bool(self.versions)
                and self.prior_shape == (self.meta['rows'], self.meta['cols']))

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
