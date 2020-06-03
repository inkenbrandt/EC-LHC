from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.models import Slider, ColumnDataSource, Button, Tabs, Panel, DateSlider, Range1d, Div, TextInput, Select, Panel, DateRangeSlider,Legend, LegendItem
from bokeh.layouts import column, row, layout
from bokeh.tile_providers import ESRI_IMAGERY, get_provider
from bokeh.transform import cumsum
from bokeh.palettes import Spectral10

import sys, pathlib
sys.path.append(str(pathlib.Path(sys.path[0]).parent/'footprint'/'FFP_python_v1_4'))

from calc_footprint_FFP_adjusted01 import FFP
from calc_footprint_FFP_climatology_adjusted01 import FFP_climatology
import numpy as np
import pandas as pd
import datetime as dt
from shapely.geometry.polygon import Polygon
import rasterio
import rasterio.mask


class view_k15:
    def __init__(self):
        self.ep_columns_filtered = ['date','time','wind_dir', 'u_rot','L','v_var','u*','wind_speed']


        self.iab3_x_utm_webMarcator = -5328976.90
        self.iab3_y_utm_webMarcator = -2532052.38

        self.tif_file = r'C:\Users\User\git\EC-LHC\iab3_site\IAB1_SIRGAS_23S.tif'
        self.raster = rasterio.open(self.tif_file)
        self.iab3_x_utm_sirgas = 203917.07880027
        self.iab3_y_utm_sirgas = 7545463.6805863

        self.tabs = Tabs(tabs=[self.tab_01(), self.tab_02(), self.tab_03()])


        curdoc().add_root(self.tabs)

    def tab_01(self):
        self.div_01 = Div(text=r'C:\Users\User\Mestrado\Dados_Processados\EddyPro_Fase01', width=500)

        self.path_ep = TextInput(value='', title='EP Path:')
        self.path_ep.on_change('value', self._textInput)

        self.select_config = Select(title='Configs:', value=None, options=[])
        self.select_config.on_change('value', self._select_config)

        self.button_plot = Button(label='Plot')
        self.button_plot.on_click(self._button_plot)


        tab01 = Panel(child=column(self.div_01, self.path_ep, self.select_config, self.button_plot), title='EP Config')

        return tab01


    def tab_02(self):
        x_range = (-5332000, -5327000)
        y_range = (-2535000, -2530000)
        tile_provider = get_provider(ESRI_IMAGERY)

        self.k15_individual = FFP()

        self.div_02_01 = Div(text='Footprint por intervalo de 30 minutos através da metodologia Kljun et al. (2015)', width=500)

        self.datetime_slider = DateSlider(title='Datetime:',
                                          start=dt.datetime(2018,1,1,0,0),
                                          end=dt.datetime(2018,1,1,0,30),
                                          value=dt.datetime(2018,1,1,0,0),
                                          step=1000*60*30, format='%x %X')
        self.datetime_slider.on_change('value_throttled', lambda attr, old, new: self.update_ffp())

        self.div_02_02 = Div(text='Selecione os dados', width=500)

        self.source_01 = ColumnDataSource(data=dict(xrs=[], yrs=[]))

        self.fig_01 = figure(title='Footprint K15', plot_height=400, plot_width=400, x_range=x_range, y_range=y_range)
        self.fig_01.add_tile(tile_provider)

        iab03 = self.fig_01.circle([self.iab3_x_utm_webMarcator], [self.iab3_y_utm_webMarcator], color='red')

        mlines = self.fig_01.multi_line(xs='xrs', ys='yrs', source=self.source_01, color='red', line_width=1)

        self.source_01_02 = ColumnDataSource(data=dict(angle=[], color=[], significado=[]))

        self.fig_01_02 = figure(plot_height=300, plot_width=500, x_range=(-1.6,1.4), toolbar_location=None)
        wedge_significado = self.fig_01_02.annular_wedge(x=-1, y=0, inner_radius=0.3, outer_radius=0.45,
                                                         start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                                                         line_color='white', fill_color='color', legend_field='significado', source=self.source_01_02)
        self.fig_01_02.axis.axis_label=None
        self.fig_01_02.axis.visible=False
        self.fig_01_02.grid.grid_line_color = None
        self.fig_01_02.outline_line_color = None

        self.div_02_03 = Div(text='''
                          <div class="header">
                          <h1>Basic Stats</h1>
                          <table border="1"><tbody><tr>
                          <td><b>Floresta (#)</b>&nbsp;</td>
                          <td><b>Outros (#)</b></td>
                          <td><b>Aceitação (%)</b></td>
                          </tr><tr>
                          <td>&nbsp;0</td>
                          <td>0</td>
                          <td>0</td>
                          </tr></tbody></table>
                          </div>''', width=500)


        tab02 = Panel(child=column(self.div_02_01,
                                   self.datetime_slider,
                                   self.div_02_02,
                                   row(self.fig_01, column(self.div_02_03,
                                                           self.fig_01_02))), title='Footprint per time')

        return tab02

    def tab_03(self):
        x_range = (-5332000, -5327000)
        y_range = (-2535000, -2530000)
        tile_provider = get_provider(ESRI_IMAGERY)

        self.k15_climatology = FFP_climatology()

        self.div_03 = Div(text='Footprint acumulado através da metodologia Kljun et al. (2015) e direção do vento', width=500)

        self.date_range = DateRangeSlider(title='Date', start=dt.datetime(2018,1,1),
                                          end=dt.datetime(2019,1,1),
                                          value=(dt.datetime(2018,1,1), dt.datetime(2019,1,1)),
                                          step=24*60*60*1000, format="%d/%m/%Y")

        self.time_range = DateRangeSlider(title='Time', start=dt.datetime(2012,1,1,0,0),
                                          end=dt.datetime(2012,1,1,23,30),
                                          value=(dt.datetime(2012,1,1,0,0), dt.datetime(2012,1,1,0,30)),
                                          step=30*60*1000, format='%H:%M')

        self.date_range.on_change('value', lambda attr,old,new:self.update_windDir())
        self.time_range.on_change('value', lambda attr,old,new:self.update_windDir())

        self.button_update_ffp = Button(label='Update Plot', width=500)
        self.button_update_ffp.on_click(self._button_update_ffp)


        self.source_02 = ColumnDataSource(data=dict(xrs=[], yrs=[]))
        self.fig_02 = figure(title='Footprint K15 acumulado', plot_height=400, plot_width=500, x_range=x_range, y_range=y_range)
        self.fig_02.add_tile(tile_provider)
        iab03 = self.fig_02.circle([self.iab3_x_utm_webMarcator], [self.iab3_y_utm_webMarcator], color='red')

        mlines = self.fig_02.multi_line(xs='xrs', ys='yrs', source=self.source_02, color='red', line_width=1)

        legend = Legend(items=[
            LegendItem(label='Torre IAB3', renderers=[iab03], index=0),
            LegendItem(label='Footprint Kljun et al. (90%)', renderers=[mlines], index=1)
        ])
        self.fig_02.add_layout(legend)
        self.fig_02.title.align = 'center'
        self.fig_02.title.text_font_size = '20px'


        self.source_02_02 = ColumnDataSource(data=dict(inner=[0], outer=[1], start=[0],end=[2]))
        self.fig_02_02 = figure(title='Direção do vento', plot_height=400, plot_width=400, toolbar_location=None, x_range=(-1.2, 1.2), y_range=(-1.2, 1.2))

        wedge = self.fig_02_02.annular_wedge(x=0, y=0, inner_radius='inner', outer_radius='outer', start_angle='start', end_angle='end', color='#FF00FF', source=self.source_02_02)
        circle = self.fig_02_02.circle(x=0, y=0, radius=[0.25,0.5,0.75], fill_color=None,line_color='white')
        circle2 = self.fig_02_02.circle(x=0, y=0, radius=[1], fill_color=None, line_color='grey')
        self.fig_02_02.annular_wedge(x=0, y=0, inner_radius='inner', outer_radius='outer', start_angle='start', end_angle='end', line_color='white',fill_color=None, line_width=1,source=self.source_02_02)

        self.date_range.on_change('value', lambda attr,old,new:self.update_windDir())
        self.time_range.on_change('value', lambda attr,old,new:self.update_windDir())

        self.fig_02_02.axis.visible = False
        self.fig_02_02.axis.axis_label = None
        self.fig_02_02.grid.grid_line_color = None
        self.fig_02_02.outline_line_color = None
        self.fig_02_02.title.align = 'center'
        self.fig_02_02.title.text_font_size = '20px'

        self.source_02_03 = ColumnDataSource(data=dict(angle=[], color=[], significado=[]))
        self.fig_02_03 = figure(plot_height=300, plot_width=500, x_range=(-1.6,1.4), toolbar_location=None)
        wedge_significado = self.fig_02_03.annular_wedge(x=-1, y=0, inner_radius=0.3, outer_radius=0.45,
                                                         start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                                                         line_color='white', fill_color='color', legend_field='significado', source=self.source_02_03)
        self.fig_02_03.axis.axis_label=None
        self.fig_02_03.axis.visible=False
        self.fig_02_03.grid.grid_line_color = None
        self.fig_02_03.outline_line_color = None


        self.div_03_02 = Div(text='''
                          <div class="header">
                          <h2>Basic Stats</h2>
                          <table border="1"><tbody><tr>
                          <td><b>Floresta (#)</b>&nbsp;</td>
                          <td><b>Outros (#)</b></td>
                          <td><b>Aceitação (%)</b></td>
                          </tr><tr>
                          <td>&nbsp;0</td>
                          <td>0</td>
                          <td>0</td>
                          </tr></tbody></table>
                          </div>''', width=400,sizing_mode="stretch_width")


        widgets = column(self.date_range,self.time_range,self.button_update_ffp)

        tab03 = Panel(child=column(self.div_03,
                                   self.date_range,
                                   self.time_range,
                                   self.button_update_ffp,
                                   row(self.fig_02, self.fig_02_02, column(self.div_03_02,
                                                                           self.fig_02_03))), title='Footprint per range')
        # layout03 = layout([[self.div_03],
        #                    [widgets],
        #                    [self.fig_02, self.fig_02_02, column(self.div_03_02)]]s)
        # tab03 = Panel(child=layout03, title='Footprint per range')
        return tab03

    def _textInput(self, attr, old, new):
        if self.tabs.active == 0:
            try:
                self.folder_path_ep = pathlib.Path(new)
                readme = self.folder_path_ep.rglob('Readme.txt')
                readme_df = pd.read_csv(list(readme)[0], delimiter=',')
                temp_list = [row.to_list() for i,row in readme_df[['rotation', 'lowfrequency', 'highfrequency','wpl','flagging','name']].iterrows()]
                a = []
                for i in temp_list:
                    a.append('Rotation:{} |LF:{} |HF:{} |WPL:{} |Flag:{}| Name:{}'.format(i[0],i[1],i[2],i[3],i[4],i[5]))
                self.select_config.options = a
            except:
                print('erro text input readme')

    def _select_config(self, attr, old, new):
        print(new)

        full_output_files = self.folder_path_ep.rglob('*{}*_full_output*.csv'.format(new[-3:]))
        dfs_single_config = []
        for file in full_output_files:
            dfs_single_config.append(pd.read_csv(file, skiprows=[0,2], na_values=-9999,
                                                 parse_dates={'TIMESTAMP':['date', 'time']},
                                                 keep_date_col=True,
                                                 usecols=self.ep_columns_filtered))
        self.df_ep = pd.concat(dfs_single_config)
        print('ok')

    def update_ffp(self):
        if self.tabs.active == 1:
            datetime = dt.datetime.utcfromtimestamp(self.datetime_slider.value/1000)

            inputs_to_k15 = self.df_ep.loc[self.df_ep['TIMESTAMP']==datetime, ['u_rot', 'L', 'u*','v_var','wind_dir_compass']]
            print(inputs_to_k15)
            self.div_02_02.text = '''
            <table border="2"><tbody><tr><td>&nbsp;zm</td><td>umean</td><td>h</td><td>ol</td><td>sigmav</td><td>ustar</td><td>wind_dir_compass</td>
    		</tr><tr>
    			<td>&nbsp;{:.3f}</td><td>{:.3f}&nbsp;</td><td>{:.3f}</td><td>{:.3f}</td><td>{:.3f}</td><td>{:.3f}</td><td>&nbsp;{:.3f}</td>
    		</tr></tbody></table>'''.format(9,
                                      inputs_to_k15['u_rot'].values[0],
                                      1000,
                                      inputs_to_k15['L'].values[0],
                                      inputs_to_k15['v_var'].values[0],
                                      inputs_to_k15['u*'].values[0],
                                      inputs_to_k15['wind_dir_compass'].values[0])
            out = self.k15_individual.output(zm=9,
                                             umean=inputs_to_k15['u_rot'].values[0],
                                             h=1000,
                                             ol=inputs_to_k15['L'].values[0],
                                             sigmav=inputs_to_k15['v_var'].values[0],
                                             ustar=inputs_to_k15['u*'].values[0],
                                             wind_dir=inputs_to_k15['wind_dir_compass'].values[0],
                                             rs=[0.3, 0.9], crop=False, fig=False)

            # Sirgas 2000 utm 23S
            poly = [(i+self.iab3_x_utm_sirgas, j+self.iab3_y_utm_sirgas) for i, j in zip(out[8][-1], out[9][-1])]
            poly_shp = Polygon(poly)

            mask_teste = rasterio.mask.mask(self.raster, [poly_shp], crop=True, invert=False)
            unique, counts = np.unique(mask_teste[0], return_counts=True)
            simplified_stats = self.stats_pixel(unique, counts)

            self.div_02_03.text = '''
            <div class="header">
            <h1>Basic Stats</h1><hr><table border="1"><tbody><tr>
            <td>Floresta (#)&nbsp;</td>
            <td>Outros (#)</td>
            <td>Aceitação (%)</td>
    		</tr><tr>
            <td>&nbsp;{}</td>
            <td>{}</td>
            <td>{:.2f}</td>
    		</tr></tbody></table>
            </div>'''.format(simplified_stats[0], simplified_stats[1], 100*simplified_stats[0]/(simplified_stats[0]+simplified_stats[1]))


            # Web Marcator
            x_webMarcator = list(np.array(out[8][-1]) + self.iab3_x_utm_webMarcator)
            y_webMarcator = list(np.array(out[9][-1]) + self.iab3_y_utm_webMarcator)

            self.source_01.data = dict(xrs=[x_webMarcator], yrs=[y_webMarcator])

        if self.tabs.active == 2:
            # try:
            start_date = dt.datetime.utcfromtimestamp(self.date_range.value[0]/1000).date()
            end_date = dt.datetime.utcfromtimestamp(self.date_range.value[1]/1000).date()

            start_time = dt.datetime.utcfromtimestamp(self.time_range.value[0]/1000).time()
            end_time = dt.datetime.utcfromtimestamp(self.time_range.value[1]/1000).time()

            inputs_to_k15 = self.df_ep.loc[
                (self.df_ep['TIMESTAMP'].dt.date >= start_date) &
                (self.df_ep['TIMESTAMP'].dt.date <= end_date) &
                (self.df_ep['TIMESTAMP'].dt.time >= start_time) &
                (self.df_ep['TIMESTAMP'].dt.time <= end_time),
                ['u_rot','L','u*', 'v_var','wind_dir_compass']
            ]

            out = self.k15_climatology.output(zm=9,
                                              umean=inputs_to_k15['u_rot'].to_list(),
                                              h=[1000 for i in range(len(inputs_to_k15['u_rot'].to_list()))],
                                              ol=inputs_to_k15['L'].to_list(),
                                              sigmav=inputs_to_k15['v_var'].to_list(),
                                              ustar=inputs_to_k15['u*'].to_list(),
                                              wind_dir=inputs_to_k15['wind_dir_compass'].to_list(),
                                              rs=[0.3, 0.9], crop=False, fig=False)
            # Sirgas 2000 utm 23S
            poly = [(i+self.iab3_x_utm_sirgas, j+self.iab3_y_utm_sirgas) for i, j in zip(out['xr'][-1], out['yr'][-1])]
            poly_shp = Polygon(poly)

            mask_teste = rasterio.mask.mask(self.raster, [poly_shp], crop=True, invert=False)
            unique, counts = np.unique(mask_teste[0], return_counts=True)
            simplified_stats = self.stats_pixel(unique, counts)

            self.div_03_02.text = '''
            <div class="header">
            <h1>Basic Stats</h1><hr><table border="1"><tbody><tr>
            <td>Floresta (#)&nbsp;</td>
            <td>Outros (#)</td>
            <td>Aceitação (%)</td>
    		</tr><tr>
            <td>&nbsp;{}</td>
            <td>{}</td>
            <td>{:.2f}</td>
    		</tr></tbody></table>
            </div>'''.format(simplified_stats[0], simplified_stats[1], 100*simplified_stats[0]/(simplified_stats[0]+simplified_stats[1]))


            # Web Marcator
            x_webMarcator = list(np.array(out['xr'][-1]) + self.iab3_x_utm_webMarcator)
            y_webMarcator = list(np.array(out['yr'][-1]) + self.iab3_y_utm_webMarcator)

            self.source_02.data = dict(xrs=[x_webMarcator], yrs=[y_webMarcator])
            # except:
            #     print('erro update')

    def update_windDir(self):
        start_date = dt.datetime.utcfromtimestamp(self.date_range.value[0]/1000).date()
        end_date = dt.datetime.utcfromtimestamp(self.date_range.value[1]/1000).date()

        start_time = dt.datetime.utcfromtimestamp(self.time_range.value[0]/1000).time()
        end_time = dt.datetime.utcfromtimestamp(self.time_range.value[1]/1000).time()

        start_angle = np.arange(0,360,10)*np.pi/180 + 90*np.pi/180
        end_angle = np.arange(10,370,10)*np.pi/180 + 90*np.pi/180

        filter = self.df_ep[(self.df_ep['TIMESTAMP'].dt.date >= start_date) &
                            (self.df_ep['TIMESTAMP'].dt.date <= end_date) &
                            (self.df_ep['TIMESTAMP'].dt.time >= start_time) &
                            (self.df_ep['TIMESTAMP'].dt.time <= end_time)]

        self.source_02_02.data = dict(inner=[0 for i in range(36)],
                                   outer=filter.groupby(by='wind_bin').count()['wind_dir_compass'][::-1]/filter.groupby(by='wind_bin').count()['wind_dir_compass'].max(),
                                   start=start_angle,
                                   end=end_angle)
        # print(filter.groupby(by='wind_bin').count()['wind_dir_compass'])

    def _button_plot(self):
        self.datetime_slider.start = self.df_ep['TIMESTAMP'].min()
        self.datetime_slider.end = self.df_ep['TIMESTAMP'].max()
        self.datetime_slider.value = self.df_ep['TIMESTAMP'].min()

        # self.date_range.start = self.df_ep['date'].min()
        # self.date_range.end = self.df_ep['date'].max()
        # self.date_range.value = (self.df_ep['date'].min(), self.df_ep['date'].max())

        self._adjust_wind_direction()

        self.theta = np.linspace(0, 360, 36)
        theta01 = np.linspace(0, 360, 37)
        # print(theta01)
        self.df_ep['wind_bin'] = pd.cut(x=self.df_ep['wind_dir_compass'], bins=theta01)
        # print(self.df_ep['wind_bin'])

        self.date_range.start = self.df_ep['date'].min()
        self.date_range.end = self.df_ep['date'].max()
        self.date_range.value = (self.df_ep['date'].min(), self.df_ep['date'].max())

    def _button_update_ffp(self):
        self.update_ffp()


    def _adjust_wind_direction(self):
        self.df_ep['wind_dir_sonic'] = 360 - self.df_ep['wind_dir']
        azimute = 135.1
        self.df_ep['wind_dir_compass'] = (360 + azimute - self.df_ep['wind_dir_sonic']).apply(lambda x: x-360 if x>=360 else x)


    def stats_pixel(self, unique, counts):
        if self.tabs.active == 1:
            significado_pixel = {3: 'Floresta Natural => Formação Florestal',
                                 4: 'Floesta Natural => Formação Savânica',
                                 9: 'Floresta Plantada',
                                 12: 'Formação Campestre/Outra formação não Florestal',
                                 15: 'Pastagem',
                                 19: 'Agricultura => Cultivo Anual e Perene',
                                 20: 'Agricultura => Cultivo Semi-Perene',
                                 24: 'Infraestrutura Urbana',
                                 25: 'Outra área não Vegetada',
                                 33: "Corpo d'água"}
            significado_pixel_lista = ['Floresta Natural (Formação Florestal)', 'Floesta Natural (Formação Savânica)',
                                       'Floresta Plantada', 'Formação Campestre', 'Pastagem', 'Agricultura (Cultivo Anual e Perene)',
                                       'Agricultura (Cultivo Semi-Perene)', 'Infraestrutura Urbana', 'Outra área não Vegetada', "Corpo d'água"]

            pixel_dict = dict(zip(unique, counts))

            pixel_simplified = []
            for i in significado_pixel:
                try:
                    pixel_simplified.append(pixel_dict[i])
                except:
                    pixel_simplified.append(0)
            pixel_floresta = pixel_simplified[0] + pixel_simplified[1]
            pixel_resto = sum(pixel_simplified[2:])

            df = pd.DataFrame({'significado': significado_pixel_lista, 'value':pixel_simplified})
            df['angle'] = df['value']/df['value'].sum() * 2*np.pi

            self.source_01_02.data = dict(angle=df['angle'],
                                       color=Spectral10,
                                       significado=df['significado'])
            return pixel_floresta, pixel_resto
        if self.tabs.active == 2:
            significado_pixel = {3: 'Floresta Natural => Formação Florestal',
                                 4: 'Floesta Natural => Formação Savânica',
                                 9: 'Floresta Plantada',
                                 12: 'Formação Campestre/Outra formação não Florestal',
                                 15: 'Pastagem',
                                 19: 'Agricultura => Cultivo Anual e Perene',
                                 20: 'Agricultura => Cultivo Semi-Perene',
                                 24: 'Infraestrutura Urbana',
                                 25: 'Outra área não Vegetada',
                                 33: "Corpo d'água"}
            significado_pixel_lista = ['Floresta Natural (Formação Florestal)', 'Floesta Natural (Formação Savânica)',
                                       'Floresta Plantada', 'Formação Campestre', 'Pastagem', 'Agricultura (Cultivo Anual e Perene)',
                                       'Agricultura (Cultivo Semi-Perene)', 'Infraestrutura Urbana', 'Outra área não Vegetada', "Corpo d'água"]

            pixel_dict = dict(zip(unique, counts))

            pixel_simplified = []
            for i in significado_pixel:
                try:
                    pixel_simplified.append(pixel_dict[i])
                except:
                    pixel_simplified.append(0)
            pixel_floresta = pixel_simplified[0] + pixel_simplified[1]
            pixel_resto = sum(pixel_simplified[2:])

            df = pd.DataFrame({'significado': significado_pixel_lista, 'value':pixel_simplified})
            df['angle'] = df['value']/df['value'].sum() * 2*np.pi

            self.source_02_03.data = dict(angle=df['angle'],
                                       color=Spectral10,
                                       significado=df['significado'])
            return pixel_floresta, pixel_resto



view_k15()
