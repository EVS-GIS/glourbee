""" Page for choosing the metrics in the interface
"""
import streamlit as st
import os

from packaging import version
from sqlalchemy.sql import text

from glourbee import ui

ui.addHeader('Manage metrics')
if not st.session_state['authenticated']: 
    st.switch_page('pages/01_🕶️_Authentication.py')
if 'extraction_zones' not in st.session_state or not st.session_state['extraction_zones']['tableId']: 
    st.switch_page('pages/02_🌍_Manage_extraction_zones.py')

from glourbee import (
    workflow,
    __version__ as glourbee_version,
)

if 'metrics' not in st.session_state:
    st.session_state['metrics'] = None

st.title('Select a metrics dataset')

assets = st.session_state['db'].query('select * from glourbmetrics where zones_asset = :zone_id', 
                                        ttl=0, 
                                        params={'zone_id': int(st.session_state['extraction_zones']['tableId'])})

if len(assets) >= 1:
    st.write('Check the already calculated metric datasets for your selected extraction zones. Check your task manager to update the tasks state.')
    
    def check_outdated(row):
        return version.parse(row['glourbee_version']) < version.parse(str(glourbee_version))

    assets['outdated'] = assets.apply(check_outdated, axis=1)

    if not st.session_state['metrics']:
        selection = ui.select_metrics(assets)

        if len(selection) == 1:
            st.session_state['metrics'] = selection['run_id'].iloc[0]
            st.rerun()

    else:
        st.success(f'Selected metrics dataset: {st.session_state["metrics"]}')
        local_csv = os.path.join(st.session_state['tempdir'].name, 'metrics.csv')

        if st.button('Unselect metrics dataset'):
            st.session_state['metrics'] = None
            if os.path.exists(local_csv):
                os.remove(local_csv)
            st.rerun()

        if st.button('Prepare dataset', help='Download the dataset from GEE to the GloUrbEE-UI server so you can visualize the metrics in the visualizer.'):
            with st.spinner('Preparing results...'):
                workflow.getResults(run_id = st.session_state['metrics'],
                                    ee_project_name= 'ee-glourb',
                                    output_csv = local_csv)
        
        if os.path.exists(local_csv):
            with open(local_csv) as f:
                st.download_button('Download metrics CSV', f, 'text/csv', help="Download the metrics dataset to your local computer")

else:
    st.warning('No metrics already calculated for this extraction zones asset')

st.title('Start a new metrics dataset computation')

def checkExistingMetrics():
    st.info('Test')

with st.form('calulate_metrics'):
    col1, col2 = st.columns(2)

    start = col1.date_input('Start date')
    start = start.strftime('%Y-%m-%d')

    stop = col2.date_input('End date')
    stop = stop.strftime('%Y-%m-%d')

    cloud_filter= st.slider('Cloud filter', min_value= 0, max_value= 100, value = 80)
    
    col1, col2 = st.columns(2)
    cloud_masking = col1.toggle('Cloud masking', value = True)
    mosaic_same_day = col1.toggle('Mosaic same day', value = True)

    satellite_type = col2.radio('Satellite imagery dataset to use', 
                                options=['Landsat', 'Sentinel-2'], 
                                captions = ['Data available since 1982-08-22', 'Data available since 2017-03-28'])

    fid_field = st.selectbox('Unique Identifier field', 
                             options=st.session_state['extraction_zones']['features'].limit(0).getInfo()['columns'].keys())

    submit_metrics = st.form_submit_button("Start computation tasks")

    if submit_metrics:
        with st.spinner('Starting computation tasks...'):
            # Récupérer la taille des ZONEs
            zones_size = st.session_state['db'].query('SELECT zones_size FROM glourbassets WHERE id = :i',
                                                    ttl=0, 
                                                    params={'i': int(st.session_state['extraction_zones']['tableId'])})
            
            # Faire des paquets de 100km de ZONEs
            # split_size = 100000 / int(zones_size['zones_size'])
            split_size = 1

            # Lancer le workflow
            run_id = workflow.startWorkflow(ee_project_name='ee-glourb',
                                            zones_asset=st.session_state['extraction_zones']['assetId'],
                                            satellite_type=satellite_type,
                                            start=start,
                                            end=stop,
                                            cloud_filter=cloud_filter,
                                            cloud_masking=cloud_masking,
                                            mosaic_same_day=mosaic_same_day,
                                            split_size=split_size,
                                            fid_field=fid_field)
            
            # Mettre à jour la base de données
            with st.session_state['db'].session as session:
                session.execute(text('INSERT INTO glourbmetrics (zones_asset, run_by, glourbee_version, run_id, state, start_date, end_date, cloud_filter, cloud_masking, mosaic_same_day, satellite_type) \
                                     VALUES (:zone, :by, :vers, :run, :s, :start, :end, :filt, :mask, :mosaic, :sat);'),
                                {
                                    'zone': int(st.session_state['extraction_zones']['tableId']),
                                    'by': st.session_state['user'],
                                    'vers': glourbee_version,
                                    'run': run_id,
                                    's': 'SUBMITTED',
                                    'start': start,
                                    'end': stop,
                                    'filt': cloud_filter,
                                    'mask': cloud_masking,
                                    'mosaic':mosaic_same_day,
                                    'sat': satellite_type
                               })
                session.commit()

        st.success('Tasks submitted to GEE. Check your task manager to track progress')



st.write('Metrics calculated by this tool')
st.markdown('''
| metric name | description |   
|---|---|
| AC_AREA | Active Channel area (pixels) |
| CLOUD_SCORE | Percent of the extraction zone covered by clouds (%) |
| COVERAGE_SCORE | Percent of the extraction zone covered by the Landsat image (%) |
| SCALE | Size of a pixel on the selected imagery dataset (meters) |
| MEAN_AC_MNDWI | Mean MNDWI in the active channel surface |
| MEAN_AC_NDVI | Mean NDVI in the active channel surface |
| MEAN_MNDWI | Mean MNDWI of the full extraction zone |
| MEAN_NDVI| Mean NDVI of the full extraction zone |
| MEAN_VEGETATION_MNDWI | Mean MNDWI in the vegetation surface |
| MEAN_VEGETATION_NDVI | Mean NDVI in the vegetation surface |
| MEAN_WATER_MNDWI | Mean MNDWI in the water surface |
| VEGETATION_AREA | Vegetation area (pixels) |
| VEGETATION_POLYGONS | Number of vegetation patches inside the extraction zone |
| VEGETATION_POLYGONS_p* | Percentiles of the vegetation patches size (in pixels) inside the extraction zone |
| VEGETATION_PERIMETER | Vegetation surface perimeter (projection unit) |
| WATER_AREA | Water area (pixels) |
| WATER_POLYGONS | Number of water patches inside the extraction zone |
| WATER_POLYGONS_p* | Percentiles of the water patches size (in pixels) inside the extraction zone |
| WATER_PERIMETER | Water surface perimeter (projection unit) |
''')

st.title('Start a new indicators dataset computation')

if st.button('Start computation task (no parameters)'):
    local_csv = os.path.join(st.session_state['tempdir'].name, 'indicators.csv')

    with st.spinner('Computing indicators...'):
        workflow.indicatorsWorkflow(zones_asset=st.session_state['extraction_zones']['features'], 
                                    output_csv=local_csv)
    
    with open(local_csv) as f:
        st.download_button('Download indicators CSV', f, 'text/csv')
    

st.write('Compute the following indicators, and download results csv.')
st.markdown('''
            | indicator name | description |   
            |---|---|
            | occurrence_p* | The frequency with which water was present (JRC Global Surface Water Mapping) |
            | change_abs_p* | Absolute change in occurrence between two epochs: 1984-1999 vs 2000-2021 (JRC Global Surface Water Mapping) |
            | change_norm_p* | Normalized change in occurrence. (epoch1-epoch2)/(epoch1+epoch2) * 100 (JRC Global Surface Water Mapping) |
            | seasonality_p* | Number of months water is present (JRC Global Surface Water Mapping) |
            | recurrence_p* | The frequency with which water returns from year to year (JRC Global Surface Water Mapping) |
            | max_extent | Surface where water has ever been detected (JRC Global Surface Water Mapping) |
            ''')