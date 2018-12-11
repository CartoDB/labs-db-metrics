# -*- coding: UTF-8 -*-

import logging
import warnings
import re
import datetime as dt

import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import matplotlib.pyplot as plt

import mpld3
from mpld3 import fig_to_html

from jinja2 import Environment, BaseLoader
from IPython.core.display import display, HTML

from carto.sql import SQLClient
from carto.auth import APIKeyAuthClient, AuthAPIClient
from carto.visualizations import VisualizationManager
from carto.datasets import DatasetManager
from carto.maps import NamedMapManager, NamedMap

### printer constructor

class Reporter(object):

  def __init__(self, CARTO_USER, CARTO_API_URL, CARTO_ORG, CARTO_API_KEY, USER_QUOTA):
    self.CARTO_USER = CARTO_USER
    self.CARTO_API_URL = CARTO_API_URL
    self.CARTO_ORG = CARTO_ORG
    self.CARTO_API_KEY = CARTO_API_KEY
    self.USER_QUOTA = USER_QUOTA

  def report(self):

    ### logger, variables and CARTO clients

    warnings.filterwarnings('ignore')

    # logger (better than print)
    logging.basicConfig(
        level=logging.INFO,
        format=' %(asctime)s - %(levelname)s - %(message)s',
        datefmt='%I:%M:%S %p')
    logger = logging.getLogger()

    ### CARTO clients
    auth_client = APIKeyAuthClient(self.CARTO_API_URL, self.CARTO_API_KEY, self.CARTO_ORG)
    auth_api_client = AuthAPIClient(self.CARTO_API_URL, self.CARTO_API_KEY, self.CARTO_ORG)
    sql = SQLClient(auth_client)
    vm = VisualizationManager(auth_client)
    dm = DatasetManager(auth_client)

    ### donwload datasets/maps information

    #helper
    def getKey(obj):
        return obj.updated_at

    #retrieve all data from account's maps
    logger.info('Getting all maps data...')
    vizs = vm.all()
    logger.info('Retrieved {} maps'.format(len(vizs)))

    maps = [{
        'name': viz.name, 
        'created': viz.created_at, 
        'url': viz.url
    } for viz in sorted(vizs, key=getKey, reverse=True)]


    #retrieve all data from account's maps
    logger.info('Getting all datasets data...')
    dsets = dm.all()
    logger.info('Retrieved {} datasets'.format(len(dsets)))

    tables = [{
        'name': table.name, 
        'privacy' : table.privacy,
        'created': table.created_at, 
        'synchronization': table.synchronization.updated_at,
        'geometry': table.table.geometry_types
    } for table in dsets]

    #transform dss/maps list of json objects to df
    maps_df = json_normalize(maps)
    total_maps = len(maps)
    tables_df = json_normalize(tables)
    total_dsets = len(dsets)
    tables_df.synchronization = tables_df.synchronization.fillna('None Sync')

    #get sync and privacy information
    logger.info('Getting privacy and sync information...')

    #privacy
    private = len(tables_df.loc[tables_df['privacy'] == 'PRIVATE'])
    link = len(tables_df.loc[tables_df['privacy'] == 'LINK'])
    public = len(tables_df.loc[tables_df['privacy'] == 'PUBLIC'])
    logger.info('{} private tables, {} tables shared with link and {} public tables'.format(private, link, public))

    #get sync and privacy information
    logger.info('Getting privacy and sync information...')

    #privacy
    private = len(tables_df.loc[tables_df['privacy'] == 'PRIVATE'])
    link = len(tables_df.loc[tables_df['privacy'] == 'LINK'])
    public = len(tables_df.loc[tables_df['privacy'] == 'PUBLIC'])
    logger.info('{} private tables, {} tables shared with link and {} public tables'.format(private, link, public))

    #sync
    try:
        tables_df.synchronization = tables_df.synchronization.fillna('None Sync')
        sync = len(dsets) - len(tables_df.loc[tables_df['synchronization'] == 'None Sync'])
        logger.info('{} sync tables'.format(sync))
    except:
        logger.info('Sync tables unable to be retrieved.')
        sync = 0
        logger.info('{} tables will be returned.'.format(sync))

    ### Get geometry information

    #clean geometry column
     
    tables_df['geom_type'] = tables_df.geometry.str[0]

    #get geocoded tables
    tables_df['geocoded'] = False
    for i in range(len(tables_df)):
      if tables_df.geom_type[i] in ('ST_Point', 'ST_MultiPolygon', 'ST_Polygon', 'ST_MultiLineString', 'ST_LineString'):
        tables_df['geocoded'][i] = True
      else:
        tables_df['geocoded'][i] = False

    #non-geocoded
    none_tbls = len(tables_df.loc[tables_df['geocoded'] == False])
    geo = len(tables_df) - none_tbls
    pc_none = round(none_tbls*100.00/len(tables_df),2)
    pc_geo = 100 - pc_none

    #polys
    polys = len(tables_df.loc[tables_df['geom_type'].isin(['ST_MultiPolygon', 'Polygon'])])
    pc_polys = round(polys*100.00/len(tables_df),2)

    #lines
    lines = len(tables_df.loc[tables_df['geom_type'].isin(['ST_LineString', 'MultiLineString'])])
    pc_lines = round(lines*100.00/len(tables_df),2)

    #points
    points = len(tables_df.loc[tables_df['geom_type'].isin(['ST_Point'])])
    pc_points = round(points*100.00/len(tables_df),2)

    #percentage
    logger.info('''
      * Account with... \r\n
      {} non-geocoded datasets ({} %) \r\n
      {} geocoded datasets ({} %) \r\n
      {} point datasets ({} %) \r\n
      {} polygon datasets ({} %) \r\n
      {} lines datasets ({} %)
    '''.format(none_tbls, pc_none, geo, pc_geo, points, pc_points, polys, pc_polys, lines, pc_lines))

    ### get Data Service quota information

    #retrieve all data from account's maps
    logger.info('Getting monthly quota information...')
    quota = pd.DataFrame(sql.send('SELECT * FROM cdb_service_quota_info()')['rows'])
    quota['quota_left'] = quota['monthly_quota']- quota['used_quota']
    lds = quota[0:3] #leave DO out
    logger.info('Retrieved {} Location Data Services'.format(len(lds)))

    #calculate % used quota
    lds['pc_used'] = round(lds.used_quota*100.00/lds.monthly_quota,2)

    #rename column names
    lds = lds.rename(columns={"monthly_quota": "Monthly Quota", "provider": "Provider", "service": "Service", "soft_limit": "Soft Limit", "used_quota": "Used Quota", "quota_left": "Quota Left", "pc_used": "% Used Quota"})

    #set service as new index
    lds = lds.set_index('Service')


    ### get storage data

    #retrieve account size
    logger.info('Getting list of tables and sizes...')

    # check all table name of account
    all_tables = []

    tables = sql.send(
        "select pg_class.relname from pg_class, pg_roles, pg_namespace" +
        " where pg_roles.oid = pg_class.relowner and " +
        "pg_roles.rolname = current_user " +
        "and pg_namespace.oid = pg_class.relnamespace and pg_class.relkind = 'r'")

    for k, v in tables.items():
        if k == 'rows':
            for itr in v:
                all_tables.append(itr['relname'])


    # define array to store all the table sizes
    arr_size = []


    # create array with values of the table sizes
    for i in all_tables:
        try:
            size = sql.send("select pg_total_relation_size('" + i + "')")
            for a, b in size.items():
                if a == 'rows':
                    for itr in b:
                        size_dataset = itr['pg_total_relation_size']
            arr_size.append(size_dataset)
        except:
            continue
            
    # define variables that have the max and min values of the previous array
    max_val = max(arr_size)/1048576.00
    min_val = min(arr_size)/1048576.00

    # define count variable
    sum = 0


    # define list of tuples
    tupleList = []

    # start iterating over array
    for i in all_tables:
        # check column names
        checkCol = []

        sum = sum + 1

        # check all columns name from table
        columns_table = "select column_name, data_type FROM information_schema.columns \
            WHERE table_schema ='" + CARTO_USER + "' \
            AND table_name ='" + i + "';"

        # apply and get results from SQL API request
        columnAndTypes = sql.send(columns_table)
        for key, value in columnAndTypes.items():
            if key == 'rows':
                for itr in value:
                    if 'cartodb_id' == itr['column_name']:
                        checkCol.append(itr['column_name'])
                    elif 'the_geom' == itr['column_name']:
                        checkCol.append(itr['column_name'])
                    elif 'the_geom_webmercator' == itr['column_name']:
                        checkCol.append(itr['column_name'])
        # check indexes
        checkInd = []
        # apply and get results from SQL API request
        indexes = sql.send("select indexname, indexdef from pg_indexes \
          where tablename = '" + i + "' \
          AND schemaname = '" + CARTO_USER + "';")
        for k, v in indexes.items():
            if k == 'rows':
                for itr in v:
                    if 'the_geom_webmercator_idx' in itr['indexname']:
                        checkInd.append(itr['indexname'])
                    elif 'the_geom_idx' in itr['indexname']:
                        checkInd.append(itr['indexname'])
                    elif '_pkey' in itr['indexname']:
                        checkInd.append(itr['indexname'])

        # if indexes and column names exists -> table cartodbified
        if len(checkInd) >= 3 and len(checkCol) >= 3:
            cartodbfied = 'YES'
        else:
            cartodbfied = 'NO'

        # create graphs according on the table size
        try:
            table_size = sql.send("select pg_total_relation_size('" + i + "')")
            for a, b in table_size.items():
                if a == 'rows':
                    for itr in b:
                        table_size = itr['pg_total_relation_size']

            # bytes to MB
            val = table_size/1048576.00
            
            # Normalize values
            norm = ((val-min_val)/(max_val-min_val))*100.00

            tupleList.append({
                'name': i, 
                'size': val, 
                'norm_size': norm,
                'cartodbfied': cartodbfied})

        except:
            print('Error at: ' + str(i))
            
    logger.info('Retrieved {} tables with size information.'.format(len(tupleList)))

    if len(tupleList) > 0:
      #convert tupleList to df
      tupleList_df = json_normalize(tupleList)

      #order by norm size value
      tbls_size = tupleList_df.sort_values(['norm_size'], ascending=False)

      #get sum of sizes and norm sizes
      total_size = round(tbls_size['size'].sum(),2)

      logger.info('Retrieved {} tables with total size of {} MB'.format(len(tupleList_df), total_size))
      
      #split between tables and analysis tables
      cdb_tabls = tbls_size.loc[tbls_size['cartodbfied'] == 'YES']
      analysis_tbls = tbls_size.loc[tbls_size['cartodbfied'] == 'NO']
      logger.info('Retrieved {} cartodbfied tables.'.format(len(analysis_tbls)))
      logger.info('Retrieved {} analysis tables.'.format(len(cdb_tabls)))
    else: 
      total_size = 0
      tbls_size = 0
      cdb_tabls = pd.DataFrame(columns=['name', 'size'])

    if len(analysis_tbls) > 0:

      #get unique analyis id
      analysis_tbls['id'] = analysis_tbls['name'].str.split("_", n = 3, expand = True)[1] 

      #convert equivalences object to a df
      equivalences = [{"type": "aggregate-intersection", "id": "b194a8f896"},{ "type": "bounding-box", "id": "5f80bdff9d"},{ "type": "bounding-circle", "id": "b7636131b5"},{ "type": "buffer", "id": "2f13a3dbd7"},{ "type": "centroid", "id": "ae64186757"},{ "type": "closest", "id": "4bd65e58e4"},{ "type": "concave-hull", "id": "259cf96ece"},{ "type": "contour", "id": "779051ec8e"},{ "type": "convex-hull", "id": "05234e7c2a"},{ "type": "data-observatory-measure", "id": "a08f3b6124"},{ "type": "data-observatory-multiple-measures", "id": "cd60938c7b"},{ "type": "deprecated-sql-function", "id": "e85ed857c2"},{ "type": "filter-by-node-column", "id": "83d60eb9fa"},{ "type": "filter-category", "id": "440d2c1487"},{ "type": "filter-grouped-rank", "id": "f15fa0b618"},{ "type": "filter-range", "id": "942b6fec82"},{ "type": "filter-rank", "id": "43155891da"},{ "type": "georeference-admin-region", "id": "a5bdb274e8"},{ "type": "georeference-city", "id": "d5b2dd1672"},{ "type": "georeference-country", "id": "792d8938e3"},{ "type": "georeference-ip-address", "id": "d5b2274cdf"},{ "type": "georeference-long-lat", "id": "0623244fc4"},{ "type": "georeference-postal-code", "id": "1f7c6f9f43"},{ "type": "georeference-street-address", "id": "1ea6dec9f3"},{ "type": "gravity", "id": "93ab69856c"},{ "type": "intersection", "id": "971639c870"},{ "type": "kmeans", "id": "3c835a874c"},{ "type": "line-sequential", "id": "9fd29bd5c0"},{ "type": "line-source-to-target", "id": "9e88a1147e"},{ "type": "line-to-column", "id": "be2ff62ce9"},{ "type": "line-to-single-point", "id": "eca516b80b"},{ "type": "link-by-line", "id": "49ca809a90"},{ "type": "merge", "id": "c38cb847a0"},{ "type": "moran", "id": "91837cbb3c"},{ "type": "point-in-polygon", "id": "2e94d3858c"},{ "type": "population-in-area", "id": "d52251dc01"},{ "type": "routing-sequential", "id": "a627e132c2"},{ "type": "routing-to-layer-all-to-all", "id": "b70cf71482"},{ "type": "routing-to-single-point", "id": "2923729eb9"},{ "type": "sampling", "id": "7530d60ffc"},{ "type": "source", "id": "fd83c76763"},{ "type": "spatial-markov-trend", "id": "9c3b798f46"},{ "type": "trade-area", "id": "112d4fc091"},{ "type": "weighted-centroid", "id": "1d85314d7a"}]
      equivalences_df = json_normalize(equivalences)

      #join equivalences to analysis table
      analysis_tbls_eq = pd.merge(equivalences_df, analysis_tbls, on='id')
      total_analysis = len(analysis_tbls_eq)
      total_size_analysis = round(analysis_tbls_eq['size'].sum(),2)

      #get analysis summuary
      analysis_types = analysis_tbls_eq['type'].value_counts()
      analysis_df = analysis_types.to_frame()
      analysis_df = analysis_df.rename(columns={'type': 'Analysis Count'})
      
    else:
      total_analysis = 0
      total_size_analysis = 0
      analysis_df = pd.DataFrame(columns=['Analysis Count'])

    ### prepare template and report variables

    # prepare variables

    #date
    now = dt.datetime.now()
    today = now.strftime("%Y-%m-%d %H:%M")

    ## maps metrics
    total_maps = len(maps_df)
    top_5_maps_date = maps_df.sort_values(['created'], ascending=False).head()
    top_5_maps_date = top_5_maps_date.rename(columns={'created': 'Date', 'name': 'Name'})
    top_5_maps_date = top_5_maps_date.set_index('Name')


    ## datasets metrics
    total_dsets = len(tables_df)
    top_5_dsets_date = tables_df[['name', 'created', 'privacy']]
    top_5_dsets_date = top_5_dsets_date.sort_values(['created'], ascending=False).head()
    top_5_dsets_date = top_5_dsets_date.rename(columns={'created': 'Date', 'name': 'Dataset', 'privacy': 'Privacy'})
    top_5_dsets_date = top_5_dsets_date.set_index('Dataset')

    top_5_dsets_size = cdb_tabls.sort_values(['size'], ascending=False).head()
    top_5_dsets_size = top_5_dsets_size[['name', 'size']]
    top_5_dsets_size = top_5_dsets_size.rename(columns={'size': 'Size', 'name': 'Dataset'})
    top_5_dsets_size = top_5_dsets_size.set_index('Dataset')

    if cdb_tabls['size'].empty:
      total_size_tbls = 0
    else:
      total_size_tbls = round(cdb_tabls['size'].sum(),2)

    ## quota
    real_storage = USER_QUOTA*2
    used_storage = round(total_size_tbls,2)
    pc_used = round(used_storage*100.00/real_storage,2)
    left_storage = round(real_storage - used_storage,2)
    pc_left = round(left_storage*100.00/real_storage,2)

    credits = lds[['Monthly Quota', 'Used Quota', '% Used Quota']]
    credits['% Quota Left'] = 100.00 - lds['% Used Quota']
    credits.loc['storage'] = [USER_QUOTA, used_storage, pc_used, pc_left]

    ### create data visualizations

    # vertical bar chart for % quota

    # plot properties
    r = list(range(len(credits)))
    barWidth = 0.85
    names = credits.index.tolist()

    # Create a plot
    fig2, ax2 = plt.subplots()

    # Create green Bars
    ax2.bar(r, credits['% Quota Left'], bottom=credits['% Used Quota'], color='#009392', edgecolor='white', width=barWidth, label='% Quota Left')
    # Create red Bars
    ax2.bar(r, credits['% Used Quota'], color='#cf597e', edgecolor='white', width=barWidth, label='% Used Quota')


    # Custom x axis
    ax2.set_xticks(r)
    ax2.set_xticklabels(names)
    ax2.set_xlabel("Location Data Service")
    ax2.set_ylabel("%")

    # Add a legend
    handles, labels = ax2.get_legend_handles_labels()
    ax2.legend(handles, labels, loc='upper left', bbox_to_anchor=(0,1,1,0))
    
    # Show graphic
    plt.tight_layout()

    # horizontal bar chart for analysis count

    # properties
    analysis_names = analysis_df.index.tolist()
    analysis_portions = analysis_df['Analysis Count']
    cartocolors = ['#7F3C8D','#11A579','#3969AC','#F2B701','#E73F74','#80BA5A','#E68310','#008695','#CF1C90','#f97b72','#4b4b8f','#A5AA99']
    names_positions = [i for i, _ in enumerate(analysis_names)]

    # plot
    fig1, ax1 = plt.subplots()
    ax1.barh(names_positions, analysis_portions, color=cartocolors)
    ax1.set_ylabel("Analysis Type")
    ax1.set_xlabel("Analysis Count")
    ax1.set_yticks(names_positions)
    ax1.set_yticklabels(analysis_names)
    plt.tight_layout()

    ### create a HTML template

    template = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>CARTO Metrics Report</title>
            <link href="https://fonts.googleapis.com/css?family=Montserrat:600" rel="stylesheet">
            <link href="https://fonts.googleapis.com/css?family=Open+Sans" rel="stylesheet">
            <style>
                h1 {
                    color: #2E3C43;
                    line-height: 32px;
                    font-family: 'Montserrat', Arial, Helvetica, sans-serif;
                    font-size: 30px;
                    font-weight: 600;
                }

                h2 {
                    color: #2E3C43;
                    line-height: 32px;
                    font-family: 'Montserrat', Arial, Helvetica, sans-serif;
                    font-size: 24px;
                    font-weight: 600;
                }

                h3 {
                    color: #2E3C43;
                    line-height: 32px;
                    font-family: 'Montserrat', Arial, Helvetica, sans-serif;
                    font-size: 20px;
                    font-weight: 600;
                }

                p {
                    color: #747D82;
                    font-size: 18px;
                    line-height: 16px;
                    font-family: 'Open Sans', Arial, Helvetica, sans-serif;
                    font-weight: 400;
                }

                .header {
                    text-align: center;
                }

                .left {
                    color: #009392;
                }

                .used {
                    color: #cf597e;
                }

                .public {
                    color: #48CA7F;
                }

                .link {
                    color: #F76C43;
                }

                .private {
                    color: #D63C2E;
                }

                ul {
                    margin: 12px 0 0 0;

                }

                li {
                    list-style-type: none;
                    margin-bottom: 8px;
                    color: #747D82;
                    font-size: 16px;
                    line-height: 16px;
                    font-family: 'Open Sans', Arial, Helvetica, sans-serif;
                    font-weight: 400;
                }

                .box {
                    box-align: center;
                    margin: auto;
                    margin-bottom: 18px;
                    padding: 3px 16px 18px;
                    border: 1px solid #DEDEDE;
                    box-shadow: 0px 1px 5px 0px rgba(0, 0, 0, 0.14);
                    -webkit-border-radius: 6px;
                    -moz-border-radius: 6px;
                    border-radius: 6px;
                    -moz-background-clip: padding;
                    -webkit-background-clip: padding-box;
                    background-clip: padding-box;
                    width: 50%;

                    p {
                    margin-bottom: 4px;
                    }

                }

                .fig {
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                    margin-bottom: 6px;
                    width: 50%;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ CARTO_USER }} CARTO Metrics report</h1>
                <h2>Date: {{today}}</h2>
            </div>
            
            <div class="box">
                <h2>Storage Quota</h2>
                <p>Account Storage: <b>{{real_storage}} MB</b></p>
                <p>Used Quota: {{used_storage}} MB, <span class="used">{{pc_used}} %</span></p>
                <p>Quota Left: {{left_storage}} MB, <span class="left">{{pc_left}} %</span></p>
            </div>

            <div class="box">
                <h2>Location Data Services</h2>
                <div class="fig">
                    {{lds.to_html()}}
                </div>
                <div class="fig">
                    {{html_fig2}}
                </div>
            </div>

            <div class="box">
                <h2>Maps and Analysis</h2>
                <p>Number of maps: {{total_maps}}</p>
                <p>Number of analyses: {{total_analysis}}</p>
                <p>Analyses Size: {{total_size_analysis}} MB</p>
                <h3>Analysis Summary</h3>
                <div class="fig">
                    {{analysis_df.to_html()}}
                </div>
                <div class="fig">
                    {{html_fig1}}
                </div>
                <h3>Top5 Recent Maps</h3>
                <div class="fig">
                    {{top_5_maps_date.to_html()}}
                </div>
            </div>

            <div class="box">
                <h2>Datasets</h2>
                <p>Number of tables: {{total_dsets}}</p>
                <p>Sync tables: {{sync}}</p>
                <p>Tables Size: {{total_size_tbls}} MB</p>
                <p>Privacy:</p>
                <ul>
                    <li>🔒 Private: <span class="private">{{private}} tables</span></li>
                    <li>🔗 Shared with link: <span class="link"">{{link}} tables</span></li>
                    <li>🔓 Public: <span class="public">{{public}} tables</span></li>
                </ul>
                <p>📌 Number of geocoded tables: {{geo}}</p>
                <ul>
                    <li>🔴 Points: {{points}} tables</li>
                    <li>〰️ Lines: {{lines}} tables</li>
                    <li>⬛ Polygons: {{polys}} tables</li>
                </ul>
                <p>Number of non-geocoded tables: {{none_tbls}} tables</p>
                <h3>Top5 Recent Datasets</h3>
                    <div class="fig">
                        {{top_5_dsets_date.to_html()}}
                    </div>
                    <h3>Top5 Dataset by Size</h3>
                    <div class="fig">
                        {{top_5_dsets_size.to_html()}}
                    </div>
            </div>
        </body>
    </html>
    """
    rtemplate = Environment(loader=BaseLoader()).from_string(template)

    html_template = rtemplate.render({
            'CARTO_USER':CARTO_USER,
        
            'today': today,
        
            'real_storage':real_storage,
            'used_storage':used_storage,
            'pc_used':pc_used,
            'left_storage':left_storage,
            'pc_left':pc_left,
        
            'total_maps':total_maps,
            'total_analysis':total_analysis,
            'total_size_analysis':total_size_analysis,
            'analysis_df': analysis_df,
            'top_5_maps_date': top_5_maps_date,
        
            'sync': sync,
            'total_dsets':total_dsets,
            'total_size_tbls':total_size_tbls,
            'private':private,
            'link':link,
            'public':public,
            'geo':geo,
            'points':points,
            'lines':lines,
            'polys':polys,
            'none_tbls':none_tbls,
            'top_5_dsets_size': top_5_dsets_size,
            'top_5_dsets_date': top_5_dsets_date,
        
            'lds': lds,
        
            'html_fig1': fig_to_html(fig1),
            'html_fig2': fig_to_html(fig2)
        })
    html_report = HTML(html_template)

    ### get the report

    report = display(html_report)

    ### export report as HTML

    with open('index.html', 'w') as html_file:
      html_file.write(html_template)
    
    return html_file
