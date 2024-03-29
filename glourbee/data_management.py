import ee
import geemap
from geetools import tools


def maskClouds(image):
    
    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)
    
    qa = image.select('qa_pixel')
    clouds = (qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))).rename('CLOUDS')
    
    return image.updateMask(clouds).addBands(clouds)


def getLandsatCollection(start=ee.Date('1980-01-01'), end=ee.Date('2100-01-01'), cloud_masking=True, cloud_filter=None, roi=None, mosaic_same_day=False):  
    '''
    Documentation
    '''
    
    # Définition des noms de bandes 
    bnd_names = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'qa_pixel']
    
    # Récupération des collections landsat
    l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2').select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5','SR_B6','SR_B7','QA_PIXEL'], bnd_names)
    l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2').select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4','SR_B5','SR_B7','QA_PIXEL'], bnd_names)
    l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2').select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4','SR_B5','SR_B7','QA_PIXEL'], bnd_names)
    l4 = ee.ImageCollection('LANDSAT/LT04/C02/T1_L2').select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4','SR_B5','SR_B7','QA_PIXEL'], bnd_names)
    
    # Merge de toutes les collections
    landsat_collection = ee.ImageCollection(l8.merge(l7).merge(l5).merge(l4)).filterDate(start, end)
        
    # Suppression des images avec trop de nuages
    if cloud_filter:
        landsat_collection = landsat_collection.filter(ee.Filter.lte('CLOUD_COVER', cloud_filter))
        
    # Filtrage de la région d'intérêt
    if roi:
        landsat_collection = landsat_collection.filterBounds(roi)
    
    # Masquage des nuages restants
    if cloud_masking:
        landsat_collection = landsat_collection.map(maskClouds)

    # Mosaiquage par jour de prise de vue pour réduire la taille de la collection
    if mosaic_same_day:
        landsat_collection = tools.imagecollection.mosaicSameDay(landsat_collection)
    
    return landsat_collection


def mask_s2_clouds(image):
      """Masks clouds in a Sentinel-2 image using the QA band.
      Args:     image (ee.Image): A Sentinel-2 image.
      Returns:  ee.Image: A cloud-masked Sentinel-2 image.
      """
      qa = image.select('qa_pixel')
      # Bits 10 and 11 are clouds and cirrus, respectively.
      cloud_bit_mask = (1 << 10)
      cirrus_bit_mask = (1 << 11)
      
      # Both flags should be set to zero, indicating clear conditions.
      mask = (qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))).rename('CLOUDS')

      # Scale the original bands of the image.
      scaled_image = image.divide(10000)

      # Add the cloud mask as an additional band without scaling.
      result_image = scaled_image.addBands(mask)

      # Copy properties from the original image to the result image.
      result_image = result_image.copyProperties(image, image.propertyNames())

      return result_image


def getSentinelCollection(start=ee.Date('2017-03-28'), end=ee.Date('2100-01-01'), cloud_masking=True, cloud_filter=None, roi=None, mosaic_same_day=False):  
    
    # Définition des noms de bandes 
    bnd_names = ['blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'qa_pixel']
    
    # Récupération des collections sentinel
    sentinel_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').select(['B2', 'B3', 'B4', 'B8','B11','B12','QA60'], bnd_names).filterDate(start, end)
                         
    # Filtrage de la région d'intérêt
    if roi:
        sentinel_collection = sentinel_collection.filterBounds(roi)

    # Suppression des images avec trop de nuages
    if cloud_filter:
        sentinel_collection = sentinel_collection.filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', cloud_filter))
        
    # Masquage des nuages restants
    if cloud_masking:
        sentinel_collection = sentinel_collection.map(mask_s2_clouds).select('blue', 'green', 'red', 'nir','swir1','swir2','CLOUDS')

    # Mosaiquage par jour de prise de vue pour réduire la taille de la collection
    if mosaic_same_day:
        sentinel_collection = tools.imagecollection.mosaicSameDay(sentinel_collection)
    
    return sentinel_collection


def imageDownload(collection, landsat_id, roi, scale=90, output='./example_data/landsat_export.tif'):
    image = collection.filter(ee.Filter.eq('LANDSAT_PRODUCT_ID', landsat_id)).first()

    geemap.ee_export_image(
        image, filename=output, scale=scale, region=roi.geometry(), file_per_band=False
    )