import ee
import geemap

import pandas as pd

from .geeprocessing import *
from .classification import *
from .vectorization import *


def dgos_properties_to_csv(dgo_shapefile_path, output_csv, dgo_list = None):
    # Paramètres fixes 
    cloud_filter = 80
    landsat_scale = 30
    px_simplify_tolerance = 1.5
    start_date = ee.Date('1980-01-01')
    end_date = ee.Date('2100-01-01')

    # Upload des DGOs sur GEE
    dgo_shp = geemap.shp_to_ee(dgo_shapefile_path)
    
    # Traiter tous les DGOs si pas de liste de DGOs renseignée
    if not dgo_list:
        n_dgo = dgo_shp.size()
        dgo_list = range(n_dgo)
    
    # Récupérer la collection d'images landsat
    landsat_collection = getLandsatCollection(start_date, end_date, cloud_filter)
    output_collection = None

    # Calculer les MNDWI
    mndwi_collection = landsat_collection.map(calculateMNDWI)

    for dgo_fid in dgo_list:
        
        # Sélectionner le DGO
        selected_dgo = selectDGOs(dgo_shp, [dgo_fid]).first()
        dgo_mndwi_coll = filterDGO(mndwi_collection, selected_dgo)
        
        # Vectoriser les surfaces en eau
        raster_water = dgo_mndwi_coll.map(vectorizeWater(selected_dgo, landsat_scale, px_simplify_tolerance))
        
        # Ajouter les résultats à l'output général
        if not output_collection:
            output_collection = raster_water
        else:
            output_collection = output_collection.merge(raster_water)

    # Récupération des propriété des images en local
    collection_props = output_collection.getInfo()

    # Rangement dans un dictionnaire
    props = [improps['properties'] for improps in collection_props['features']]

    # Conversion en pandas DataFrame
    props_df = pd.DataFrame(props)

    # Conversion d'unités des aires (pixels vers m2)
    props_df['WATER_AREA'] = props_df['WATER_AREA'] * landsat_scale * landsat_scale

    # Export csv
    props_df.to_csv(output_csv)