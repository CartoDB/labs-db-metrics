# -*- coding: UTF-8 -*-

import logging
import re
import datetime as dt

import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import matplotlib.pyplot as plt

import mpld3
from mpld3 import fig_to_html

from jinja2 import Environment, BaseLoader

from carto.sql import SQLClient
from carto.auth import APIKeyAuthClient, AuthAPIClient
from carto.visualizations import VisualizationManager
from carto.datasets import DatasetManager
from carto.maps import NamedMapManager, NamedMap

### printer constructor

class Reporter(object):

    def __init__(self, CARTO_USER, CARTO_API_URL, CARTO_ORG, CARTO_API_KEY, USER_QUOTA):
        self.CARTO_USER = CARTO_USER
        self.CARTO_ORG = CARTO_ORG
        self.USER_QUOTA = USER_QUOTA

        ### CARTO clients
        auth_client = APIKeyAuthClient(CARTO_API_URL, CARTO_API_KEY, CARTO_ORG)
        self.sql = SQLClient(auth_client)
        self.vm = VisualizationManager(auth_client)
        self.dm = DatasetManager(auth_client)

        ### logger, variables and CARTO clients
        self.logger = logging.getLogger('carto_report')
        self.logger.addHandler(logging.NullHandler())

    def report(self):
        '''
        Main method to get the full report
        '''
        vizs = self.vm.all()
        dsets = self.dm.all()
        user = self.CARTO_USER
        quota = self.USER_QUOTA

        #maps
        maps_df = self.getMaps(vizs)
        total_maps = len(vizs) 
        top_5_maps_date = self.getTop5(maps_df, 'created', 'name')

        #datasets
        dsets_df = self.getDatasets(dsets)
        total_dsets = len(dsets)
        top_5_dsets_date = self.getTop5(dsets_df, 'created', 'name')
        sync =  self.getSync(dsets_df)
        (private, link, public) = self.getPrivacy(dsets_df)
        (points, lines, polys, none_tbls, geo) = self.getGeometry(dsets_df)

        #lds
        (lds_df) = self.getQuota(user, quota)


    ### helper - get date
    def getDate(self):
        '''
        Method to get the exact date of the report
        '''
        now = dt.datetime.now()
        today = now.strftime("%Y-%m-%d %H:%M")
        return today

    ### get maps data

    def getMaps(self, vizs):
        '''
        Method to get a df with the list of maps with names, urls and date of creation.
        '''

        self.logger.info('Getting all maps data...')

        #helper
        def getKey(obj):
            return obj.updated_at

        maps = [{
            'name': viz.name, 
            'created': viz.created_at, 
            'url': viz.url
        } for viz in sorted(vizs, key=getKey, reverse=True)]

        maps_df = json_normalize(maps)
        
        self.logger.info('Retrieved {} maps'.format(len(maps_df)))

        return maps_df

    ### get dsets data

    def getDatasets(self, dsets):
        '''
        Method to get a df with the list of dsets with names, privacy, sync, geometry and date of creation.
        '''

        self.logger.info('Getting all datasets data...')

        tables = [{
            'name': table.name, 
            'privacy' : table.privacy,
            'created': table.created_at, 
            'synchronization': table.synchronization.updated_at,
            'geometry': table.table.geometry_types
        } for table in dsets]
        
        tables_df = json_normalize(tables)

        self.logger.info('Retrieved {} datasets'.format(len(tables_df)))

        return tables_df

    def getSync(self, tables_df):
        '''
        Method to get the number of sync tables.
        '''

        self.logger.info('Getting privacy and sync information...')

        try:
            tables_df.synchronization = tables_df.synchronization.fillna('None Sync')
            sync = len(dsets) - len(tables_df.loc[tables_df['synchronization'] == 'None Sync'])
            self.logger.info('{} sync tables'.format(sync))
        except:
            self.logger.info('Sync tables unable to be retrieved.')
            sync = 0
            self.logger.info('{} tables will be returned.'.format(sync))
        
        return sync

    ### get datasets privacy settings

    def getPrivacy(self, tables_df):
        '''
        Method to get the number of tables based on their privacy settings (private, link and public).
        '''

        self.logger.info('Getting privacy information...')

        private = len(tables_df.loc[tables_df['privacy'] == 'PRIVATE'])
        link = len(tables_df.loc[tables_df['privacy'] == 'LINK'])
        public = len(tables_df.loc[tables_df['privacy'] == 'PUBLIC'])
        
        self.logger.info('{} private tables, {} tables shared with link and {} public tables'.format(private, link, public))

        return (private, link, public)

    ### get datasets geometry

    def getGeometry(self, tables_df):
        '''
        Method to get the number of tables with and without geometry. It also returns the geometry type (lines, points and polygons).
        '''

        self.logger.info('Getting geometry information...')
        
        tables_df['geom_type'] = tables_df.geometry.str[0]

        tables_df['geocoded'] = False
        for i in range(len(tables_df)):
            if tables_df.geom_type[i] in ('ST_Point', 'ST_MultiPolygon', 'ST_Polygon', 'ST_MultiLineString', 'ST_LineString'):
                tables_df['geocoded'][i] = True
            else:
                tables_df['geocoded'][i] = False

        none_tbls = len(tables_df.loc[tables_df['geocoded'] == False])
        geo = len(tables_df.loc[tables_df['geocoded'] == True])
        polys = len(tables_df.loc[tables_df['geom_type'].isin(['ST_MultiPolygon', 'Polygon'])])
        lines = len(tables_df.loc[tables_df['geom_type'].isin(['ST_LineString', 'MultiLineString'])])
        points = len(tables_df.loc[tables_df['geom_type'].isin(['ST_Point'])])

        self.logger.info('{} non-geocoded datasets retrieved'.format(none_tbls)) 
        self.logger.info('{} geocoded datasets'.format(geo))
        self.logger.info('{} point datasets'.format(points))
        self.logger.info('{} polygon datasets'.format(polys))
        self.logger.info('{} lines datasets'.format(lines))

        return (points, lines, polys, none_tbls, geo)

    ### helper - get percentage 

    def getPercentage(self, part, df):
        percentage = round(part*100/len(df),2)
        return percentage

    ### helper - get top list

    def getTop5(self, df, col_order, col_index):
        top5 = df.sort_values([col_order], ascending=False).head()
        top5 = top5.set_index(col_index)
        return top5

    ### get quota information

    def getQuota(self, user, quota):
        '''
        Method to get storage quota and LDS (geocoding, routing, isolines) information as df.
        '''

        self.logger.info('Getting storage quota and geocoding, routing and isolines quota information...')

        dsets_size = pd.DataFrame(self.sql.send(
            "SELECT SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))/1000000 as total FROM pg_tables WHERE schemaname = '" + user + "'")['rows'])['total'][0]
        self.logger.info('Retrieved {} MB as storage quota'.format(dsets_size))

        lds = pd.DataFrame(self.sql.send('SELECT * FROM cdb_service_quota_info()')['rows'])
        self.logger.info('Retrieved {} Location Data Services'.format(len(lds)))

        lds = lds[0:3] #leave DO out
        lds['pc_used'] = round(lds.used_quota*100/lds.monthly_quota,2)
        lds = lds.rename(columns={"monthly_quota": "Monthly Quota", "provider": "Provider", "service": "Service", "used_quota": "Used", "pc_used": "% Used"})
        
        real_storage = quota*2
        used_storage = round(dsets_size,2)
        pc_used = round(used_storage*100/real_storage,2)
        storage = [real_storage, 'carto', 'storage', 'false', used_storage, pc_used]
        lds.loc[len(lds)] = storage
        
        lds = lds.set_index('Service')
        lds['Left'] = round(lds['Monthly Quota'] - lds['Used'],1)
        lds['% Left'] = 100.00 - lds['% Used']
        lds_df = lds[['Monthly Quota', 'Provider', 'Used', '% Used', 'Left', '% Left']]

        return lds_df

    ### get storage data

    def getSizes(self):

        self.logger.info('Getting list of tables and sizes...')

        # check all table name of account
        all_tables = []

        tables = self.sql.send(
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

        self.logger.info('Getting table sizes...')
        # create array with values of the table sizes
        for i in all_tables:
            try:
                size = self.sql.send("select pg_total_relation_size('" + i + "')")
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

        self.logger.info('Getting cartodbfied and analysis tables...')
        # start iterating over array
        for i in all_tables:
            # check column names
            checkCol = []

            sum = sum + 1

            # check all columns name from table
            columns_table = "select column_name, data_type FROM information_schema.columns \
                WHERE table_schema ='" + self.CARTO_USER + "' \
                AND table_name ='" + i + "';"

            # apply and get results from SQL API request
            columnAndTypes = self.sql.send(columns_table)

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
            indexes = self.sql.send(
                "select indexname, indexdef from pg_indexes \
                where tablename = '" + i + "' \
                AND schemaname = '" + self.CARTO_USER + "';")

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
                table_size = self.sql.send("select pg_total_relation_size('" + i + "')")
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
                self.logger.info('Error at: ' + str(i))
                
        self.logger.info('Retrieved {} tables with size information.'.format(len(tupleList)))

        return tupleList

    ### get tables sizes

    def getTableSizes(self,tupleList):

        self.logger.info('Processing cartodbfied and analysis tables...')

        if len(tupleList) > 0:
            #convert tupleList to df
            tupleList_df = json_normalize(tupleList)

            #order by norm size value
            tbls_size = tupleList_df.sort_values(['norm_size'], ascending=False)

            #get sum of sizes and norm sizes
            total_size = round(tbls_size['size'].sum(),2)

            self.logger.info('Retrieved {} tables with total size of {} MB'.format(len(tupleList_df), total_size))

            #split between tables and analysis tables
            cdb_tabls = tbls_size.loc[tbls_size['cartodbfied'] == 'YES']
            analysis_tbls = tbls_size.loc[tbls_size['cartodbfied'] == 'NO']
            self.logger.info('Retrieved {} cartodbfied tables.'.format(len(analysis_tbls)))
            self.logger.info('Retrieved {} analysis tables.'.format(len(cdb_tabls)))
        else: 
            total_size = 0
            tbls_size = 0
            cdb_tabls = pd.DataFrame(columns=['name', 'size'])
            analysis_tbls = pd.DataFrame(columns=['name', 'size'])

        top_5_dsets_size = cdb_tabls.sort_values(['size'], ascending=False).head()
        top_5_dsets_size = top_5_dsets_size[['name', 'size']]
        top_5_dsets_size = top_5_dsets_size.rename(columns={'size': 'Size', 'name': 'Dataset'})
        top_5_dsets_size = top_5_dsets_size.set_index('Dataset')

        if cdb_tabls['size'].empty:
            total_size_tbls = 0
        else:
            total_size_tbls = round(cdb_tabls['size'].sum(),2)
        
        return total_size, tbls_size, cdb_tabls, analysis_tbls, top_5_dsets_size, total_size_tbls

    ### get analysis names table

    def getAnalysisNames(self, analysis_tbls):

        self.logger.info('Replacing analysis id with proper names...')

        if len(analysis_tbls) > 0:
            self.logger.info('Replacing analysis table ids with the right analysis name.')  
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

        self.logger.info('{} analysis names replaced '.format(total_analysis))

        return analysis_df, total_analysis, total_size_analysis

    ### plot LDS figure

    def plotQuota(self, credits):

        self.logger.info('Plotting LDS figure...')

            # plot properties
        r = list(range(len(credits)))
        barWidth = 0.85
        names = credits.index.tolist()

        # create a plot
        fig_lds, ax_lds = plt.subplots()

        # create used quota / red bars
        ax_lds.bar(r, credits['% Quota Left'], bottom=credits['% Used Quota'], color='#009392', edgecolor='white', width=barWidth, label='% Quota Left')
        # create quota left / red bars
        ax_lds.bar(r, credits['% Used Quota'], color='#cf597e', edgecolor='white', width=barWidth, label='% Used Quota')

        # customize ticks and labels
        ax_lds.set_xticks(r)
        ax_lds.set_xticklabels(names)
        ax_lds.set_xlabel("Location Data Service")
        ax_lds.set_ylabel("%")

        # Add a legend
        handles, labels = ax_lds.get_legend_handles_labels()
        ax_lds.legend(handles, labels, loc='upper left', bbox_to_anchor=(0,1,1,0))
        
        # tight plot
        plt.tight_layout()

        return fig_lds

    ### plot analysis figure

    def plotAnalysis(self, analysis_df):

        self.logger.info('Plotting analysis figure...')

        # plot properties
        analysis_names = analysis_df.index.tolist()
        analysis_portions = analysis_df['Analysis Count']
        cartocolors = ['#7F3C8D','#11A579','#3969AC','#F2B701','#E73F74','#80BA5A','#E68310','#008695','#CF1C90','#f97b72','#4b4b8f','#A5AA99']
        names_positions = [i for i, _ in enumerate(analysis_names)]

        # create plot
        fig_analysis, ax_analysis = plt.subplots()

        # plot bars
        ax_analysis.barh(names_positions, analysis_portions, color=cartocolors)

        # customize ticks and labels
        ax_analysis.set_ylabel("Analysis Type")
        ax_analysis.set_xlabel("Analysis Count")
        ax_analysis.set_yticks(names_positions)
        ax_analysis.set_yticklabels(analysis_names)

        # tight plot
        plt.tight_layout()

        return fig_analysis

    ### create a HTML template

    def generateTemplate(self,
        user, today, 
        lds, real_storage, used_storage, pc_used, left_storage, pc_left, 
        total_maps, top_5_maps_date,
        total_analysis, total_size_analysis, analysis_df,
        sync, total_dsets, total_size_tbls, top_5_dsets_date, top_5_dsets_size,
        private, link, public,
        geo, none_tbls, points, lines, polys,
        fig_analysis,
        fig_lds):

        self.logger.info('Generating HTML template...')

        template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="ie=edge">
            <title>CARTO Database Metrics Report Template</title>
            <link rel="stylesheet" href="https://libs.cartocdn.com/airship-style/v1.0.3/airship.css">
            <script src="https://libs.cartocdn.com/airship-components/v1.0.3/airship.js"></script>
            <style>
            .as-sidebar{
                width: 33.33%;
            }
            .as-box{
                border-bottom: 1px solid #F5F5F5;
            }
            </style>
            </head>                   
            <body class="as-app-body as-app">
            <header class="as-toolbar">
                <div class="as-toolbar__item as-title">
                    CARTO Metrics Report 
                </div>
                <div class="as-toolbar__item as-display--block as-p--12 as-subheader as-bg--complementary">
                    {{ user }} at {{today}}
                </div>
            </header>
            <div class="as-content">
                <aside class="as-sidebar as-sidebar--left">
                <div class="as-container">
                    <h1 class="as-box as-title as-font--medium">
                    Maps and Analysis
                    </h1>
                    <div class="as-box">
                        <h2 class="as-title">
                            Maps
                        </h2>
                        <p class="as-body as-font--medium">Number of maps: {{total_maps}}</p>
                        <div class="as-box" id="maps-table">
                            {{top_5_maps_date.to_html()}}
                        </div>
                    </div>

                    <div class="as-box">
                    <h2 class="as-title">
                        Analysis
                    </h2>
                    <ul class="as-list">
                        <li class="as-list__item">Number of analyses: {{total_analysis}}</li>
                        <li class="as-list__item">Analyses Size: {{total_size_analysis}} MB</li>
                    </ul>
                    <div class="as-box" id="analysis-table">
                        {{analysis_df.to_html()}}
                    </div>
                    <div class="as-box" id="analysis-fig">
                        {{html_fig_analysis}}
                    </div>
                    </div>
                </div>
                </aside>
                <main class="as-main">
                    <h1 class="as-box as-title as-font--medium">
                        Storage Quota & LDS
                    </h1>
                    <div class="as-box">
                        <h2 class="as-title">
                            Storage Quota
                        </h2>
                        <ul class="as-list">
                            <li class="as-list__item as-font--medium">Account Storage: {{real_storage}} MB</li>
                            <li class="as-list__item as-color--support-01">Used Quota: {{used_storage}} MB, {{pc_used}} %</li>
                            <li class="as-list__item as-color--complementary">Quota Left: {{left_storage}} MB, {{pc_left}} %</li>
                        </ul>
                    </div>
                    <div class="as-box">
                        <h2 class="as-title">
                            Location Data Services
                        </h2>
                        <div class="as-box" id="lds-table">
                            {{lds.to_html()}}
                        </div>
                        <div class="as-box" id="lds-fig">
                            {{html_fig_lds}}
                        </div>
                    </div>
                </main>
                <aside class="as-sidebar as-sidebar--right">
                <div class="as-container">
                    <div class="as-box as-title as-font--medium">
                    Datasets
                    </div>
                    <div class="as-box">
                        <h2 class="as-title">
                            Datasets Summary
                        </h2>
                        <ul class="as-list">
                            <li class="as-list__item as-font--medium">Number of tables: {{total_dsets}}</li>
                            <li class="as-list__item">Sync tables: {{sync}}</li>
                            <li class="as-list__item">Tables Size: {{total_size_tbls}} MB</li>
                        </ul>
                    </div>
                    <div class="as-box">
                    <h2 class="as-title">
                        Privacy
                    </h2>
                    <ul class="as-list">
                        <li class="as-list__item as-color--support-01">🔒 Private: {{private}} tables</li>
                        <li class="as-list__item as-color--support-02">🔗 Shared with link: {{link}} tables</li>
                        <li class="as-list__item as-color--support-03">🔓 Public: {{public}} tables</li>
                    </ul>
                    </div>
                    <div class="as-box">
                    <h2 class="as-title">
                        Geometry
                    </h2>
                    <p class="as-body">
                        Number of geocoded tables: {{geo}}
                    </p>
                    <ul class="as-list">
                        <li class="as-list__item">📌 Points: {{points}} tables</li>
                        <li class="as-list__item">〰️ Lines: {{lines}} tables</span></li>
                        <li class="as-list__item">⬛ Polygons: {{polys}} tables</li>
                    </ul>
                    <p class="as-body">
                        Number of non-geocoded tables: {{none_tbls}}
                    </p>
                    </div>
                    <div class="as-box" id="tables-size">
                        {{top_5_dsets_size.to_html()}}
                    </div>
                    <div class="as-box" id="tables-date">
                        {{top_5_dsets_date.to_html()}}
                    </div>
                </div>
                </aside>
            </div>
            <script>
                // add airship class to tables 
                const tableElements = document.querySelectorAll('table');
                tableElements.forEach(element => element.classList.add("as-table"));
            </script>
            </body>
            </html>
        """
        rtemplate = Environment(loader=BaseLoader()).from_string(template)

        self.logger.info('Rendering HTML report...')

        return rtemplate.render({

                # user and date info
                'user': user,
                'today': today,

                # lds and storage info
                'lds': lds,
                'real_storage':real_storage,
                'used_storage':used_storage,
                'pc_used':pc_used,
                'left_storage':left_storage,
                'pc_left':pc_left,

                # maps info
                'total_maps':total_maps,
                'total_analysis':total_analysis,
                'total_size_analysis':total_size_analysis,
                'analysis_df': analysis_df,
                'top_5_maps_date': top_5_maps_date,

                # datasets info
                'sync': sync,
                'total_dsets':total_dsets,
                'total_size_tbls':total_size_tbls,
                'top_5_dsets_size': top_5_dsets_size,
                'top_5_dsets_date': top_5_dsets_date,

                # privacy info
                'private':private,
                'link':link,
                'public':public,

                # geometry info
                'geo':geo,
                'points':points,
                'lines':lines,
                'polys':polys,
                'none_tbls':none_tbls,

                # figures
                'html_fig_analysis': fig_to_html(fig_analysis),
                'html_fig_lds': fig_to_html(fig_lds)
            })

