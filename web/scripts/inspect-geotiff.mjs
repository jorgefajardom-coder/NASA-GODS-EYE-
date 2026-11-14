// Prints the metadata of a GeoTIFF so a crop can be chosen. Usage: node scripts/inspect-geotiff.mjs <file.tif>
import { fromFile } from 'geotiff';

const tiff = await fromFile(process.argv[2]);
const img = await tiff.getImage();
const fd = img.getFileDirectory();
console.log('size', img.getWidth(), 'x', img.getHeight(), 'bands', img.getSamplesPerPixel(), 'bits', fd.BitsPerSample, 'format', fd.SampleFormat);
console.log('tiepoint', img.getTiePoints?.()[0], 'pixelScale', fd.ModelPixelScale);
console.log('bbox', img.getBoundingBox());
console.log('nodata', img.getGDALNoData());
console.log('geokeys', img.getGeoKeys());
console.log('gdal metadata', (fd.GDAL_METADATA || '').toString().slice(0, 300));
