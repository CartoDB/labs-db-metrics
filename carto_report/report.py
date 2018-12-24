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
        org = self.CARTO_ORG
        quota = self.USER_QUOTA

        #maps
        maps_df = self.getMaps(vizs)
        top_5_maps_date = self.getTop5(maps_df, 'created', 'name')

        #datasets
        dsets_df = self.getDatasets(dsets)
        top_5_dsets_date = self.getTop5(dsets_df, 'created', 'name')
        sync =  self.getSync(dsets_df)
        (private, link, public) = self.getPrivacy(dsets_df)
        (points, lines, polys, none_tbls, geo) = self.getGeometry(dsets_df)
        all_tables_df = self.getSizes(dsets_df)
        tables_sizes = all_tables_df.loc[all_tables_df['cartodbfied'] == 'Yes']
        top_5_dsets_size = self.getTop5(all_tables_df, 'size', 'name')

        #lds
        (lds_df) = self.getQuota(user, quota)

        #analysis
        (analysis_df, analysis_types_df) = self.getAnalysisNames(all_tables_df)

        #plots
        fig_analysis = self.plotAnalysis(analysis_types_df)
        fig_lds = self.plotQuota(lds_df)

        #date
        today = self.getDate()

        #report
        report = self.generateReport(user, org, today, lds_df, maps_df, top_5_maps_date, analysis_types_df, analysis_df, dsets_df, tables_sizes, top_5_dsets_date, top_5_dsets_size, sync, private, link, public, geo, none_tbls, points, lines, polys,fig_analysis,fig_lds)

        return report
        
    ### helper - get date
    def getDate(self):
        '''
        Method to get the exact date of the report.
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

        # helper - get key
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

    ### get analysis and tables data

    def getSizes(self, dsets_df):
        '''
        Method to get all tables sizes, know cartodbfied and non cartodbfied tables (analysis).
        '''
        
        self.logger.info('Getting list of tables...')
        
        all_tables = self.sql.send(
                    "select pg_class.relname as name from pg_class, pg_roles, pg_namespace" +
                    " where pg_roles.oid = pg_class.relowner and " +
                    "pg_roles.rolname = current_user " +
                    "and pg_namespace.oid = pg_class.relnamespace and pg_class.relkind = 'r'")['rows']

        all_tables_df = json_normalize(all_tables)
        
        
        self.logger.info('Retrieved {} tables.'.format(len(all_tables_df)))
        
        dsets_df['cartodbfied'] = 'Yes'
        all_tables_df = all_tables_df.merge(dsets_df, on='name', how='left')
        all_tables_df['cartodbfied'] = all_tables_df['cartodbfied'].fillna('No')
        all_tables_df['size'] = 0
        
        self.logger.info('Getting table sizes...')
        
        for index, row in all_tables_df.iterrows():
            try:
                size = self.sql.send("select pg_total_relation_size('" + row['name'] + "') as size")['rows'][0].get('size')
            except:
                self.logger.info('Error at: ' + str(row['name']))
            
            all_tables_df.set_value(index,'size',size)
            
        self.logger.info('Table sizes retrieved with a sum of {} MB'.format(all_tables_df['size'].sum()))
            
        return all_tables_df

    ### get analysis names table

    def getAnalysisNames(self, all_tables_df):
        '''
        Method to transform analysis ids to analysis names.
        '''

        self.logger.info('Getting analysis from tables information...')

        analysis_df = all_tables_df.loc[all_tables_df['cartodbfied'] == 'No']

        if len(analysis_df) > 0:

            #get analysis id
            self.logger.info('Replacing analysis id with proper names...')
            analysis_df['id'] = analysis_df['name'].str.split("_", n = 3, expand = True)[1] 

            #convert equivalences object to a df
            equivalences = [{"type": "aggregate-intersection", "id": "b194a8f896"},{ "type": "bounding-box", "id": "5f80bdff9d"},{ "type": "bounding-circle", "id": "b7636131b5"},{ "type": "buffer", "id": "2f13a3dbd7"},{ "type": "centroid", "id": "ae64186757"},{ "type": "closest", "id": "4bd65e58e4"},{ "type": "concave-hull", "id": "259cf96ece"},{ "type": "contour", "id": "779051ec8e"},{ "type": "convex-hull", "id": "05234e7c2a"},{ "type": "data-observatory-measure", "id": "a08f3b6124"},{ "type": "data-observatory-multiple-measures", "id": "cd60938c7b"},{ "type": "deprecated-sql-function", "id": "e85ed857c2"},{ "type": "filter-by-node-column", "id": "83d60eb9fa"},{ "type": "filter-category", "id": "440d2c1487"},{ "type": "filter-grouped-rank", "id": "f15fa0b618"},{ "type": "filter-range", "id": "942b6fec82"},{ "type": "filter-rank", "id": "43155891da"},{ "type": "georeference-admin-region", "id": "a5bdb274e8"},{ "type": "georeference-city", "id": "d5b2dd1672"},{ "type": "georeference-country", "id": "792d8938e3"},{ "type": "georeference-ip-address", "id": "d5b2274cdf"},{ "type": "georeference-long-lat", "id": "0623244fc4"},{ "type": "georeference-postal-code", "id": "1f7c6f9f43"},{ "type": "georeference-street-address", "id": "1ea6dec9f3"},{ "type": "gravity", "id": "93ab69856c"},{ "type": "intersection", "id": "971639c870"},{ "type": "kmeans", "id": "3c835a874c"},{ "type": "line-sequential", "id": "9fd29bd5c0"},{ "type": "line-source-to-target", "id": "9e88a1147e"},{ "type": "line-to-column", "id": "be2ff62ce9"},{ "type": "line-to-single-point", "id": "eca516b80b"},{ "type": "link-by-line", "id": "49ca809a90"},{ "type": "merge", "id": "c38cb847a0"},{ "type": "moran", "id": "91837cbb3c"},{ "type": "point-in-polygon", "id": "2e94d3858c"},{ "type": "population-in-area", "id": "d52251dc01"},{ "type": "routing-sequential", "id": "a627e132c2"},{ "type": "routing-to-layer-all-to-all", "id": "b70cf71482"},{ "type": "routing-to-single-point", "id": "2923729eb9"},{ "type": "sampling", "id": "7530d60ffc"},{ "type": "source", "id": "fd83c76763"},{ "type": "spatial-markov-trend", "id": "9c3b798f46"},{ "type": "trade-area", "id": "112d4fc091"},{ "type": "weighted-centroid", "id": "1d85314d7a"}]
            equivalences_df = json_normalize(equivalences)

            #join equivalences to analysis table
            analysis_df = pd.merge(analysis_df, equivalences_df, on='id', how='left')

            #get analysis summuary
            analysis_types = analysis_df['type'].value_counts()
            analysis_types_df = analysis_types.to_frame()
            analysis_types_df = analysis_types_df.rename(columns={'type': 'Analysis Count'})

            self.logger.info('{} analysis retrieved, {} different types. '.format(len(analysis_df), analysis_types_df.nunique()))         
        else:
            self.logger.info('No analysis found.')   
                                                
        return (analysis_df, analysis_types_df)

    ### plot LDS figure

    def plotQuota(self, lds_df):
        '''
        Method to plot a lds and storage bar chart.
        '''

        self.logger.info('Plotting LDS figure...')

        # plot properties
        r = list(range(len(lds_df)))
        barWidth = 0.85
        names = lds_df.index.tolist()

        # create a plot
        fig_lds, ax_lds = plt.subplots()

        # create used quota / red bars
        ax_lds.bar(r, lds_df['% Left'], bottom=lds_df['% Used Quota'], color='#009392', edgecolor='white', width=barWidth, label='% Left')
        # create quota left / red bars
        ax_lds.bar(r, lds_df['% Used'], color='#cf597e', edgecolor='white', width=barWidth, label='% Used')

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

    def plotAnalysis(self, analysis_types_df):
        '''
        Method to plot a analysis count bar chart.
        '''

        self.logger.info('Plotting analysis figure...')

        # plot properties
        analysis_names = analysis_types_df.index.tolist()
        analysis_portions = analysis_types_df['Analysis Count']
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

    ### generate report with an HTML template

    def generateReport(self,
        user, org, today, 
        lds_df, 
        maps_df, top_5_maps_date,
        analysis_types_df, analysis_df,
        dsets_df, tables_sizes, top_5_dsets_date, top_5_dsets_size,
        sync, private, link, public,
        geo, none_tbls, points, lines, polys,
        fig_analysis,fig_lds):

        '''
        Method to generate a HTML report.
        '''

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
                    {{ user }} from {{org}} at {{today}}
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
                        {{analysis_types_df.to_html()}}
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

        report = rtemplate.render({

                # user and date info
                'user': user,
                'org': org,
                'today': today,

                # lds and storage info
                'lds': lds_df,
                'real_storage':lds_df['storage']['Monthly Quota'],
                'used_storage':lds_df['storage']['Used'],
                'pc_used':lds_df['storage']['% Used'],
                'left_storage':lds_df['storage']['Left'],
                'pc_left':lds_df['storage']['% Left'],

                # maps info
                'total_maps': len(maps_df),
                'total_analysis': len(analysis_df),
                'total_size_analysis': analysis_df['size'].sum(),
                'analysis_types_df': analysis_types_df,
                'top_5_maps_date': top_5_maps_date,

                # datasets info
                'sync': sync,
                'total_dsets': len(dsets_df),
                'total_size_tbls': tables_sizes['size'].sum(),
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
        
        return report

