import pandas as pd
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import datetime as dt
import tensorflow as tf

from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator

from sklearn.metrics import mean_absolute_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn import preprocessing


class gapfilling_iab3:
    def __init__(self, ep_path, lf_path, iab2_path, iab1_path, footprint_file):
        # File's Path
        self.iab3EP_path = pathlib.Path(ep_path)
        self.iab3LF_path = pathlib.Path(lf_path)
        self.iab2_path = pathlib.Path(iab2_path)
        self.iab1_path = pathlib.Path(iab1_path)

        self.footprint_file = pathlib.Path(footprint_file)

        self._read_files()

        # self._gagc()

    def _read_files(self):
        # Reading csv files
        self.iab3EP_files = self.iab3EP_path.rglob('eddypro*p08*full*.csv')
        self.iab3LF_files = self.iab3LF_path.rglob('TOA5*.flux*.dat')
        self.iab2_files = self.iab2_path.rglob('*.dat')
        self.iab1_files = self.iab1_path.rglob('*Table1*.dat')

        # self.footprint_file = self.footprint_path.rglob('classification_pixel_2018-10-05-00-30to2020-11-04-00-00_pf_80*')

        footprint_columns = ['TIMESTAMP','code03', 'code04', 'code09','code12','code15','code19','code20','code24','code25','code33']
        ep_columns =  ['date','time',  'H', 'qc_H', 'LE', 'qc_LE','sonic_temperature', 'air_temperature', 'air_pressure', 'air_density',
               'ET', 'e', 'es', 'RH', 'VPD','Tdew', 'u_unrot', 'v_unrot', 'w_unrot', 'u_rot', 'v_rot', 'w_rot', 'wind_speed',
               'max_wind_speed', 'wind_dir', 'u*', '(z-d)/L',  'un_H', 'H_scf', 'un_LE', 'LE_scf','u_var', 'v_var', 'w_var', 'ts_var','H_strg','LE_strg']
        lf_columns = ['TIMESTAMP', 'CO2_sig_strgth_mean','H2O_sig_strgth_mean','Rn_Avg','Rs_incoming_Avg', 'Rs_outgoing_Avg',
                      'Rl_incoming_Avg', 'Rl_outgoing_Avg', 'Rl_incoming_meas_Avg','Rl_outgoing_meas_Avg', 'shf_Avg(1)', 'shf_Avg(2)',
                      'precip_Tot']
        iab3EP_dfs = []
        print('Reading IAB3_EP files...')
        for file in self.iab3EP_files:
            iab3EP_dfs.append(pd.read_csv(file,skiprows=[0,2], na_values=-9999, parse_dates={'TIMESTAMP':['date','time']}, keep_date_col=True, usecols=ep_columns))
        self.iab3EP_df = pd.concat(iab3EP_dfs)
        print(f"# IAB3_EP: {len(iab3EP_dfs)}\tInicio: {self.iab3EP_df['TIMESTAMP'].min()}\tFim: {self.iab3EP_df['TIMESTAMP'].max()}")

        iab3LF_dfs = []
        print('Reading IAB3_LF files...')
        for file in self.iab3LF_files:
            iab3LF_dfs.append(pd.read_csv(file, skiprows=[0,2,3], na_values=['NAN'], parse_dates=['TIMESTAMP'], usecols=lf_columns))
        self.iab3LF_df = pd.concat(iab3LF_dfs)
        print(f"# IAB3_LF: {len(iab3LF_dfs)}\tInicio:{self.iab3LF_df['TIMESTAMP'].min()}\tFim: {self.iab3LF_df['TIMESTAMP'].max()}")

        iab2_dfs = []
        print('Reading IAB2 files...')
        for file in self.iab2_files:
            iab2_dfs.append(pd.read_csv(file, skiprows=[0,2,3], na_values=['NAN'], parse_dates=['TIMESTAMP']))
        self.iab2_df = pd.concat(iab2_dfs)
        print(f"# IAB2: {len(iab2_dfs)}\tInicio: {self.iab2_df['TIMESTAMP'].min()}\tFim: {self.iab2_df['TIMESTAMP'].max()}")

        iab1_dfs = []
        print('Reading IAB1 files...')
        for file in self.iab1_files:
            iab1_dfs.append(pd.read_csv(file, skiprows=[0,2,3], na_values=['NAN'], parse_dates=['TIMESTAMP']))
        self.iab1_df = pd.concat(iab1_dfs)
        print(f"# IAB1: {len(iab1_dfs)}\tInicio: {self.iab1_df['TIMESTAMP'].min()}\tFim: {self.iab1_df['TIMESTAMP'].max()}")

        iab_dfs = [self.iab3EP_df, self.iab3LF_df, self.iab2_df, self.iab1_df]

        print('Reading Footprint file...')
        self.footprint_df = pd.read_csv(self.footprint_file, parse_dates=['TIMESTAMP'], na_values=-9999, usecols=footprint_columns)
        print(f"Inicio: {self.footprint_df['TIMESTAMP'].min()}\tFim: {self.footprint_df['TIMESTAMP'].max()}")

        # Removing duplicated files based on 'TIMESTAMP'
        for df in iab_dfs:
            print('Duplicatas: ',df.duplicated().sum())
            df.drop_duplicates(subset='TIMESTAMP', keep='first', inplace=True)
            df.reset_index(inplace=True)
            print('Verificacao de Duplicatas: ', df.duplicated().sum())

        # Merging files from EddyPro data and LowFreq data
        self.iab3_df = pd.merge(left=self.iab3EP_df, right=self.iab3LF_df, on='TIMESTAMP', how='inner')

        # Resampling IAB2
        self.iab2_df_resample = self.iab2_df.set_index('TIMESTAMP').resample('30min').mean()
        self.iab2_df_resample.reset_index(inplace=True)
        # print(self.iab2_df_resample)

    def _applying_filters(self):
        # Flag using Mauder and Foken (2004)
        self.iab3_df.loc[self.iab3_df[['qc_H','qc_LE']].isin([0]).sum(axis=1)==2, 'flag_qaqc'] = 1
        self.iab3_df.loc[self.iab3_df[['qc_H','qc_LE']].isin([0]).sum(axis=1)!=2, 'flag_qaqc'] = 0

        # Flag rain
        self.iab3_df.loc[self.iab3_df['precip_Tot']>0, 'flag_rain'] = 0
        self.iab3_df.loc[self.iab3_df['precip_Tot']==0, 'flag_rain'] = 1

        # Flag signal strength
        min_signalStr = 0.8
        self.iab3_df.loc[self.iab3_df['H2O_sig_strgth_mean']>=min_signalStr, 'flag_signalStr'] = 1
        self.iab3_df.loc[self.iab3_df['H2O_sig_strgth_mean']<min_signalStr, 'flag_signalStr'] = 0

    def dropping_bad_data(self):
        # Apply filters
        self._applying_filters()

        # Creating a copy and changing to 'nan' filtered values
        iab3_df_copy = self.iab3_df.copy()
        iab3_df_copy.loc[
            (iab3_df_copy['flag_qaqc']==0)|
            (iab3_df_copy['flag_rain']==0)|
            (iab3_df_copy['flag_signalStr']==0)|
            (iab3_df_copy['LE']<0), 'ET'] = np.nan

        return iab3_df_copy

    def _adjacent_days(self, df,n_days=5):
        # Selecting datetime adjectent
        delta_days = [i for i in range(-n_days, n_days+1, 1)]
        df[f'timestamp_adj_{n_days}'] = df['TIMESTAMP'].apply(lambda x: [x + dt.timedelta(days=i) for i in delta_days])

    def _gagc(self):
        self.iab3_df['psychrometric_kPa'] = 0.665*10**(-3)*self.iab3_df['air_pressure']/1000
        self.iab3_df['delta'] = 4098*(0.6108*np.e**(17.27*(self.iab3_df['air_temperature']-273.15)/((self.iab3_df['air_temperature']-273.15)+237.3)))/((self.iab3_df['air_temperature']-273.15)+237.3)**2
        self.iab3_df['VPD_kPa'] = (self.iab3_df['es']-self.iab3_df['e'])/1000
        self.iab3_df['LE_MJmh'] = self.iab3_df['LE']*3600/1000000
        self.iab3_df['Rn_Avg_MJmh'] = self.iab3_df['Rn_Avg']*3600/1000000
        self.iab3_df['shf_Avg_MJmh'] = self.iab3_df[['shf_Avg(1)','shf_Avg(2)']].mean(axis=1)*3600/1000000

        self.iab3_df['ga'] = (self.iab3_df['wind_speed']/self.iab3_df['u*']**2)**(-1)
        self.iab3_df['gc'] = (self.iab3_df['LE_MJmh']*self.iab3_df['psychrometric_kPa']*self.iab3_df['ga'])/(self.iab3_df['delta']*(self.iab3_df['Rn_Avg_MJmh']-self.iab3_df['shf_Avg_MJmh'])+self.iab3_df['air_density']*3600*1.013*10**(-3)*self.iab3_df['VPD_kPa']*self.iab3_df['ga']-self.iab3_df['LE_MJmh']*self.iab3_df['delta']-self.iab3_df['LE_MJmh']*self.iab3_df['psychrometric_kPa'])

        # print(self.iab3_df['gc'].describe())
        self.iab3_df_gagc = self.iab3_df.set_index('TIMESTAMP').resample('1m').mean()[['ga','gc']]
        self.iab3_df_gagc.reset_index(inplace=True)
        # print(self.iab3_df_gagc)

    def _adjusting_input_pm(self):
        # self.iab2_df_resample['delta'] = 4098*(0.6108*np.e**(17.27*self.iab2_df_resample['AirTC_Avg']/(self.iab2_df_resample['AirTC_Avg']+237.3)))/(self.iab2_df_resample['AirTC_Avg']+237.3)**2

        # self.iab2_df_resample['es'] = 0.6108*np.e**(17.27*self.iab2_df_resample['AirTC_Avg']/(self.iab2_df_resample['AirTC_Avg']+237.3))

        self.iab12_df = pd.merge(left=self.iab1_df[['TIMESTAMP','RH']],
                                 right=self.iab2_df_resample[['TIMESTAMP', 'AirTC_Avg','CNR_Wm2_Avg','G_Wm2_Avg']],
                                 on='TIMESTAMP', how='inner')

        self.iab12_df['delta'] = 4098*(0.6108*np.e**(17.27*self.iab12_df['AirTC_Avg']/(self.iab12_df['AirTC_Avg']+237.3)))/(self.iab12_df['AirTC_Avg']+237.3)**2
        self.iab12_df['es'] = 0.6108*np.e**(17.27*self.iab12_df['AirTC_Avg']/(self.iab12_df['AirTC_Avg']+237.3))
        self.iab12_df['ea'] = self.iab12_df['RH']/100*self.iab12_df['es']
        self.iab12_df['VPD'] = self.iab12_df['es']-self.iab12_df['ea']

        altitude = 790
        self.iab12_df['P'] = 101.3*((293-0.0065*altitude)/293)**5.26
        self.iab12_df['psychrometric_cte'] = 0.665*10**(-3)*self.iab12_df['P']

        self.iab12_df['air_density'] = 1.088

        self.iab12_df['Rn_Avg_MJmh'] = self.iab12_df['CNR_Wm2_Avg']*3600/1000000
        self.iab12_df['G_Avg_MJmh'] = self.iab12_df['G_Wm2_Avg']*3600/1000000

    def lstm_model_forecast(self, model, series, window_size):
        ds = tf.data.Dataset.from_tensor_slices(series)
        ds = ds.window(window_size, shift=1, drop_remainder=True)
        ds = ds.flat_map(lambda w: w.batch(window_size))
        ds = ds.batch(32).prefetch(1)
        forecast = model.predict(ds)
        return forecast

    def dnn_model(self, train_X, val_X, train_y, val_y, learning_rate, epochs, batch_size):
        tf.keras.backend.clear_session()
        tf.random.set_seed(51)

        models = []

        for e in epochs:
            for l in learning_rate:
                optimizer = tf.keras.optimizers.SGD(lr=l)
                for b in batch_size:
                    model = tf.keras.Sequential([
                        tf.keras.layers.Dense(1000, input_shape=[np.shape(train_X)[1]], activation='relu'),
                        # tf.keras.layers.Dropout(0.2),
                        tf.keras.layers.Dense(800, activation='relu'),
                        tf.keras.layers.Dense(600, activation='relu'),
                        tf.keras.layers.Dense(150, activation='relu'),
                        tf.keras.layers.Dense(1, activation='linear')
                        ])

                    model.compile(optimizer=optimizer,
                                  loss=tf.keras.losses.Huber(),
                                  metrics=['mae'])
                    history = model.fit(x=train_X, y=train_y,
                                        epochs=e, batch_size=b, verbose=0,
                                        validation_data=(val_X, val_y))
                    last_mae_t = history.history['mae'][-1]
                    last_mae_v = history.history['val_mae'][-1]

                    models.append(model)

                    # plt.title(f'Batch_size: {b} | LR: {l:.2f} | MAE_t: {last_mae_t:.4f} | MAE_v: {last_mae_v:.4f}')
                    # plt.plot(history.history['mae'], label='Training')
                    # plt.plot(history.history['val_mae'], label='Validation')
                    #
                    # plt.legend(loc='best')
                    # plt.xlabel('# Epochs')
                    # plt.ylabel('MAE')
                    # plt.savefig(r'G:\Meu Drive\USP-SHS\Resultados_processados\Gapfilling\ANN\imgs\dnn\{}-epochs_{}-lr_{}-bs.png'.format(e,l,b))
                    # plt.show()
                    tf.keras.backend.clear_session()
                    tf.random.set_seed(51)
        return models

    def lstm_univariate_model(self, length, generator_train, generator_val, epochs=10):
        tf.keras.backend.clear_session()
        tf.random.set_seed(51)

        model = tf.keras.Sequential([
            tf.keras.layers.Masking(mask_value=0, input_shape=(length, 1)),
            tf.keras.layers.LSTM(32, activation='relu', return_sequences=True, dropout=0.4),
            tf.keras.layers.LSTM(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])

        model.compile(loss=tf.keras.losses.Huber(), optimizer='adam', metrics=['mae'])
        history = model.fit(generator_train, epochs=epochs, validation_data=generator_train)

        # plt.title('')
        # plt.plot(history.history['mae'], label='Training')
        # plt.plot(history.history['val_mae'], label='Validation')
        #
        # plt.legend(loc='best')
        # plt.xlabel('# Epochs')
        # plt.ylabel('MAE')
        # plt.show()

        tf.keras.backend.clear_session()
        tf.random.set_seed(51)
        return model

    def lstm_conv1d_univariate_model(self, length, generator_train, generator_val, epochs=10):
        tf.keras.backend.clear_session()
        tf.random.set_seed(51)

        model = tf.keras.Sequential([
            tf.keras.layers.Masking(mask_value=0, input_shape=(length, 1)),
            tf.keras.layers.Conv1D(filters=32, kernel_size=12, strides=1, activation='relu'),
            tf.keras.layers.LSTM(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])

        model.compile(loss=tf.keras.losses.Huber(), optimizer='adam', metrics=['mae'])
        history = model.fit(generator_train, epochs=epochs, validation_data=generator_train)

        tf.keras.backend.clear_session()
        tf.random.set_seed(51)

        return model

    def lstm_multivariate_model(self, length, generator_train, generator_val, epochs=10):
        tf.keras.backend.clear_session()
        tf.random.set_seed(50)

        model = tf.keras.Sequential([
            tf.keras.layers.Masking(mask_value=0, input_shape=(length, 8)),
            tf.keras.layers.LSTM(32, activation='relu', return_sequences=True),
            tf.keras.layers.LSTM(32, activation='relu'),
            tf.keras.layers.Dense(1)
        ])

        model.compile(loss=tf.keras.losses.Huber(), optimizer='adam', metrics=['mae'])
        history = model.fit(generator_train, epochs=epochs, validation_data=generator_train)

        tf.keras.backend.clear_session()
        tf.random.set_seed(50)

        return model

    def mdv_test(self, n_days=5):
        # Dropping bad data
        iab3_df_copy = self.dropping_bad_data()
        iab3_df_copy.dropna(subset=['ET'], inplace=True)

        # Splitting Dataframe into two parts
        a, b = train_test_split(iab3_df_copy[['TIMESTAMP','ET']])

        # Creating Dataframe with full TIMESTAMP, based on the Dataframe of good data
        date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                   end=iab3_df_copy['TIMESTAMP'].max(),
                                   freq='30min')
        df_date_range = pd.DataFrame({'TIMESTAMP':date_range})

        # Merge and creating DataFrame with first part of good data and full TIMESTAMP
        iab3_alldates = pd.merge(left=df_date_range, right=a, on='TIMESTAMP', how='outer')
        # iab3_alldates = pd.merge(left=iab3_alldates, right=b, on='TIMESTAMP', how='outer')

        # Changing column name of second part of good data
        # To later be compared with gapfilled data
        b.rename(columns={"ET":'ET_val_mdv'}, inplace=True)

        # Merge DataFrame with second part of good data and full TIMESTAMP
        iab3_alldates = pd.merge(left=iab3_alldates, right=b, on='TIMESTAMP', how='outer')

        # Create new column for datetime adjecent days
        self._adjacent_days(df=iab3_alldates, n_days=n_days)

        # Iterating the 'nan' ET and using the non 'nan' ET and adjecent days for filling the data
        for i, row in iab3_alldates.loc[iab3_alldates['ET'].isna()].iterrows():
            iab3_alldates.loc[i, f'ET_mdv_{n_days}'] = iab3_alldates.loc[(iab3_alldates['TIMESTAMP'].isin(row[f'timestamp_adj_{n_days}']))&
                                                                         (iab3_alldates['ET'].notna()), 'ET'].mean()


        # Creating Dataframe for calculate metrics and removing non filled data
        iab3_metrics = iab3_alldates[['ET_val_mdv',f'ET_mdv_{n_days}']].copy()
        iab3_metrics.dropna(inplace=True)

        # Checking metrics
        print(mean_absolute_error(iab3_metrics['ET_val_mdv'], iab3_metrics[f'ET_mdv_{n_days}']))
        print(iab3_metrics.corr())

    def rfr_test(self):
        column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
        column_x_ET = column_x + ['ET']

        iab3_df_copy = self.dropping_bad_data()
        iab3_df_copy.dropna(subset=column_x_ET, inplace=True)

        X = iab3_df_copy[column_x]
        y = iab3_df_copy['ET']

        train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1)
        print(val_y)

        et_model_RFR = RandomForestRegressor(random_state=1, criterion='mae', max_depth=2)
        et_model_RFR.fit(train_X, train_y)

        val_prediction_RFR = et_model_RFR.predict(val_X)
        # val_y['ET_rfr'] = val_prediction_RFR

        iab3_metrics = pd.DataFrame({'ET':val_y.values, 'ET_rfr':val_prediction_RFR})

        mae_RFR = mean_absolute_error(val_y, val_prediction_RFR)
        print(mae_RFR)

        print(iab3_metrics.corr())
        # print(val_X.)

    def lr_test(self):
        column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
        column_x_ET = column_x + ['ET']

        iab3_df_copy = self.dropping_bad_data()
        iab3_df_copy.dropna(subset=column_x_ET, inplace=True)

        X = iab3_df_copy[column_x]
        y = iab3_df_copy['ET']

        train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1, shuffle=True)

        lm = LinearRegression()
        model = lm.fit(train_X, train_y)

        print(f'''ET = {column_x[0]}*{model.coef_[0]}
              +{column_x[1]}*{model.coef_[1]}
              +{column_x[2]}*{model.coef_[2]}
              +{column_x[3]}*{model.coef_[3]}
              +{column_x[4]}*{model.coef_[4]}
              +{column_x[5]}*{model.coef_[5]}
              +{column_x[6]}*{model.coef_[6]}
              +{column_x[7]}*{model.coef_[7]}
              +{column_x[8]}*{model.coef_[8]}+{model.intercept_}''')

        lm_prediction = model.predict(val_X)
        print(lm_prediction)

        mae_lm = mean_absolute_error(val_y, lm_prediction)
        print(mae_lm)

        iab3_metrics = pd.DataFrame({'ET':val_y.values, 'ET_lr':lm_prediction})
        print(iab3_metrics.corr())

    def pm_test(self):
        self._adjusting_input_pm()
        self._gagc()

        pm_inputs_iab3 = ['delta', 'Rn_Avg_MJmh', 'shf_Avg_MJmh', 'air_density', 'VPD_kPa', 'ga','LE_MJmh','psychrometric_kPa', 'gc', 'TIMESTAMP']
        pm_inputs_iab3_ET = pm_inputs_iab3 + ['ET']

        iab3_df_copy = self.dropping_bad_data()

        iab3_df_copy.dropna(subset=pm_inputs_iab3_ET, inplace=True)

        X = iab3_df_copy[pm_inputs_iab3]
        y = iab3_df_copy['ET']

        # print(X)

        train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1, shuffle=True)
        # print(val_X)
        val_X = val_X.copy()
        for i, row in self.iab3_df_gagc.iterrows():
            val_X.loc[(val_X['TIMESTAMP'].dt.month==row['TIMESTAMP'].month)&(val_X['TIMESTAMP'].dt.year==row['TIMESTAMP'].year), 'ga_mes'] = row['ga']
            val_X.loc[(val_X['TIMESTAMP'].dt.month==row['TIMESTAMP'].month)&(val_X['TIMESTAMP'].dt.year==row['TIMESTAMP'].year), 'gc_mes'] = row['gc']

        val_X['ET_est_pm'] = (val_X['delta']*(val_X['Rn_Avg_MJmh']-val_X['shf_Avg_MJmh'])+3600*val_X['air_density']*1.013*10**(-3)*val_X['VPD_kPa']*val_X['ga_mes'])/(2.45*(val_X['delta']+val_X['psychrometric_kPa']*(1+val_X['ga_mes']/val_X['gc_mes'])))
        print(val_X['ET_est_pm'])

        print(mean_absolute_error(val_y, val_X['ET_est_pm']))

        # print(val_X['ET_est_pm'])
        # print(val_y)

        # for i,row in self.iab3_df_gagc.iterrows():
        #     val_X.loc[val_X['TIMESTAMP'].dt.month==row['TIMESTAMP'].month, 'ET_est_pm'] = (val_X['delta']*(val_X['Rn_Avg_MJmh']-val_X['shf_Avg_MJmh'])+3600*val_X['air_density']*1.013*10**(-3)*val_X['VPD_kPa']*row['ga'])/(2.45*(val_X['delta']+val_X['psychrometric_kPa']*(1+row['ga']/row['gc'])))


            # print(val_X.loc[val_X['TIMESTAMP'].dt.month==row['TIMESTAMP'].month])

    def dnn_test(self):
        # Dropping bad data
        iab3_df_copy = self.dropping_bad_data()
        iab3_df_copy.dropna(subset=['ET'], inplace=True)
        column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
        column_x_ET = column_x + ['ET']

        X = iab3_df_copy[column_x]
        y = iab3_df_copy['ET']

        X_scale = preprocessing.scale(X)
        train_X, val_X, train_y, val_y = train_test_split(X_scale, y, random_state=1, shuffle=True)

        self.dnn_model(train_X=train_X,
                       val_X=val_X,
                       train_y=train_y,
                       val_y=val_y,
                       learning_rate=[0.5e-1, 1e-2],
                       epochs=[100],
                       batch_size=[512])

    def lstm_univariate_test(self, length=12, batch_size=3):
        column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']

        iab3_df_copy = self.dropping_bad_data()
        iab3_df_copy.dropna(subset=column_x, inplace=True)

        date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                   end=iab3_df_copy['TIMESTAMP'].max(),
                                   freq='30min')


        df_date_range = pd.DataFrame({'TIMESTAMP': date_range})

        iab3_alldates = pd.merge(left=df_date_range, right=iab3_df_copy, how='outer')
        iab3_alldates.loc[iab3_alldates['ET'].isnull(), "ET"] = 0

        train_X, val_X = train_test_split(iab3_alldates['ET'], shuffle=False)

        generator_train = TimeseriesGenerator(train_X, train_X, length=length, batch_size=batch_size)
        generator_val = TimeseriesGenerator(val_X.to_numpy(), val_X.to_numpy(), length=length, batch_size=batch_size)

        model = self.lstm_univariate_model(length=length,
                                           generator_train=generator_train,
                                           generator_val=generator_val,
                                           epochs=10)
        lstm_forecast = self.lstm_model_forecast(model, val_X[..., np.newaxis], length)
        lstm_forecast = np.insert(lstm_forecast, 0, [0 for i in range(length-1)])

        validation_data = pd.DataFrame({'lstm_forecast': lstm_forecast})
        validation_data['real_data'] = val_X.values

        print(mean_absolute_error(validation_data.loc[validation_data['real_data']!=0, 'real_data'], validation_data.loc[validation_data['real_data']!=0, 'lstm_forecast']))

        print(validation_data.loc[validation_data['real_data']!=0, ['real_data', 'lstm_forecast']].corr())

    def fill_ET(self, listOfmethods):
        self.iab3_ET_timestamp = self.dropping_bad_data()
        self.ET_names = []

        if 'mdv' in listOfmethods:
            print('MDV...')
            n_days_list = [5]

            iab3_df_copy = self.dropping_bad_data()
            iab3_df_copy.dropna(subset=['ET'], inplace=True)

            a, b = train_test_split(iab3_df_copy[['TIMESTAMP', 'ET']])

            date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                       end=iab3_df_copy['TIMESTAMP'].max(),
                                       freq='30min')
            df_date_range = pd.DataFrame({'TIMESTAMP':date_range})

            iab3_alldates = pd.merge(left=df_date_range, right=a, on='TIMESTAMP', how='outer')

            b.rename(columns={"ET":'ET_val_mdv'}, inplace=True)

            iab3_alldates = pd.merge(left=iab3_alldates, right=b, on='TIMESTAMP', how='outer')

            column_names = ['TIMESTAMP']
            for n in n_days_list:
                self.ET_names.append(f'ET_mdv_{n}')
                column_names.append(f'ET_mdv_{n}')
                self._adjacent_days(df=iab3_alldates, n_days=n)

                # for i, row in iab3_alldates.loc[iab3_alldates['ET'].isna()].iterrows():
                for i, row in iab3_alldates.iterrows():
                    iab3_alldates.loc[i, f'ET_mdv_{n}'] = iab3_alldates.loc[(iab3_alldates['TIMESTAMP'].isin(row[f'timestamp_adj_{n}']))&
                                                                                 (iab3_alldates['ET'].notna()), 'ET'].mean()

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_alldates[column_names], on='TIMESTAMP', how='outer')
            # print(self.iab3_ET_timestamp)
            # print(iab3_alldates)
                # iab3_metrics = iab3_alldates[['ET_val_mdv',f'ET_mdv_{n}']].copy()
                # iab3_metrics.dropna(inplace=True)

                # print(mean_absolute_error(iab3_metrics['ET_val_mdv'], iab3_metrics[f'ET_mdv_{n}']))
                # print(iab3_metrics.corr())

        if 'lr' in listOfmethods:
            print('LR...')
            self.ET_names.append('ET_lr')
            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
            column_x_ET = column_x + ['ET']
            iab3_df_copy_na = iab3_df_copy.copy()
            iab3_df_copy_na.dropna(subset=column_x_ET, inplace=True)

            X = iab3_df_copy_na[column_x]
            y = iab3_df_copy_na['ET']

            train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1, shuffle=True)

            lm = LinearRegression()
            model = lm.fit(train_X, train_y)

            lm_prediction = model.predict(val_X)
            iab3_df_copy.dropna(subset=column_x, inplace=True)
            lm_fill = model.predict(iab3_df_copy[column_x])
            iab3_df_copy['ET_lr'] = lm_fill
            # print(iab3_df_copy)

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_df_copy[['TIMESTAMP', 'ET_lr']], on='TIMESTAMP', how='outer')

        if 'rfr' in listOfmethods:
            print('RFR...')
            self.ET_names.append('ET_rfr')

            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
            column_x_ET = column_x + ['ET']
            iab3_df_copy_na = iab3_df_copy.copy()
            iab3_df_copy_na.dropna(subset=column_x_ET, inplace=True)

            X = iab3_df_copy_na[column_x]
            y = iab3_df_copy_na['ET']

            train_X, val_X, train_y, val_y = train_test_split(X, y, random_state=1, shuffle=True)

            et_model_RFR = RandomForestRegressor(random_state=1, criterion='mae', max_depth=2)
            et_model_RFR.fit(train_X, train_y)

            iab3_df_copy.dropna(subset=column_x, inplace=True)
            rfr_prediction = et_model_RFR.predict(iab3_df_copy[column_x])
            iab3_df_copy['ET_rfr'] = rfr_prediction

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_df_copy[['TIMESTAMP', 'ET_rfr']], on='TIMESTAMP', how='outer')

        if 'pm' in listOfmethods:
            print('PM...')
            self.ET_names.append('ET_pm')

            self._adjusting_input_pm()
            self._gagc()

            pm_inputs_iab3 = ['delta', 'Rn_Avg_MJmh', 'shf_Avg_MJmh', 'air_density', 'VPD_kPa', 'ga','LE_MJmh','psychrometric_kPa', 'gc', 'TIMESTAMP']
            pm_inputs_iab3_ET = pm_inputs_iab3 + ['ET']

            iab3_df_copy = self.dropping_bad_data()
            iab3_df_copy.dropna(subset=pm_inputs_iab3, inplace=True)
            for i, row in self.iab3_df_gagc.iterrows():
                iab3_df_copy.loc[(iab3_df_copy['TIMESTAMP'].dt.month==row['TIMESTAMP'].month)&(iab3_df_copy['TIMESTAMP'].dt.year), 'ga_mes'] = row['ga']
                iab3_df_copy.loc[(iab3_df_copy['TIMESTAMP'].dt.month==row['TIMESTAMP'].month)&(iab3_df_copy['TIMESTAMP'].dt.year), 'gc_mes'] = row['gc']

            iab3_df_copy['ET_pm'] = (iab3_df_copy['delta']*(iab3_df_copy['Rn_Avg_MJmh']-iab3_df_copy['shf_Avg_MJmh'])+3600*iab3_df_copy['air_density']*1.013*10**(-3)*iab3_df_copy['VPD_kPa']*iab3_df_copy['ga_mes'])/(2.45*(iab3_df_copy['delta']+iab3_df_copy['psychrometric_kPa']*(1+iab3_df_copy['ga_mes']/iab3_df_copy['gc_mes'])))
            # print(self.iab3_df_gagc[['TIMESTAMP','ga', 'gc']])
            # print(iab3_df_copy.loc[iab3_df_copy['ET_pm']>0])
            # print(iab3_df_copy[pm_inputs_iab3+['ET_pm']].describe())

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_df_copy[['TIMESTAMP', 'ET_pm']], on='TIMESTAMP', how='outer')

        if 'dnn' in listOfmethods:
            print('DNN...')
            self.ET_names.append('ET_dnn')

            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']
            column_x_ET = column_x + ['ET']
            iab3_df_copy.dropna(subset=column_x, inplace=True)
            iab3_df_copy_na = iab3_df_copy.copy()
            iab3_df_copy_na.dropna(subset=['ET'], inplace=True)

            X = iab3_df_copy_na[column_x]
            y = iab3_df_copy_na['ET']

            X_scale = preprocessing.scale(X)
            # train_X, val_X, train_y, val_y = train_test_split(X_scale, y, random_state=1, shuffle=True)

            models = self.dnn_model(train_X=X_scale,val_X=X_scale,
                                    train_y=y, val_y=y,
                                    learning_rate=[1e-2], epochs=[10], batch_size=[512])

            X_predict = iab3_df_copy[column_x]
            X_predict = preprocessing.scale(X_predict)

            y_predict = models[0].predict(X_predict)

            iab3_df_copy['ET_dnn'] = y_predict

            # print(iab3_df_copy['ET_dnn'].describe())
            # print(models[0].predict(X_predict))
            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_df_copy[['TIMESTAMP', 'ET_dnn']], on='TIMESTAMP', how='outer')

        if 'lstm_u' in listOfmethods:
            print('LSTM_u...')
            self.ET_names.append('ET_lstm_u')

            length = 24
            batch_size = 12

            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']

            iab3_df_copy.dropna(subset=column_x, inplace=True)

            date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                       end=iab3_df_copy['TIMESTAMP'].max(),
                                       freq='30min')


            df_date_range = pd.DataFrame({'TIMESTAMP': date_range})

            iab3_alldates = pd.merge(left=df_date_range, right=iab3_df_copy, how='outer')
            iab3_alldates.loc[iab3_alldates['ET'].isnull(), "ET"] = 0

            train_X, val_X = train_test_split(iab3_alldates['ET'], shuffle=False)

            generator_train = TimeseriesGenerator(train_X, train_X, length=length, batch_size=batch_size)
            generator_val = TimeseriesGenerator(val_X, val_X, length=length, batch_size=batch_size)
            model = self.lstm_univariate_model(length=length,
                                               generator_train=generator_train,
                                               generator_val=generator_val,
                                               epochs=2)
            lstm_forecast = self.lstm_model_forecast(model, iab3_alldates['ET'].to_numpy()[..., np.newaxis], length)
            lstm_forecast = np.insert(lstm_forecast, 0, [0 for i in range(length-1)])

            validation_data = pd.DataFrame({'TIMESTAMP': date_range})
            validation_data['ET_lstm_u'] = lstm_forecast

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=validation_data[['TIMESTAMP','ET_lstm_u']], on='TIMESTAMP', how='outer')

            # print(self.iab3_ET_timestamp['ET_lstm_u'].describe())

        if 'lstm_conv1d_u' in listOfmethods:
            print('LSTM_Conv1D_u...')
            self.ET_names.append('ET_lstm_conv1d_u')

            length = 12
            batch_size = 3

            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'air_pressure','shf_Avg(1)','shf_Avg(2)','e','wind_speed']

            iab3_df_copy.dropna(subset=column_x, inplace=True)

            date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                       end=iab3_df_copy['TIMESTAMP'].max(),
                                       freq='30min')


            df_date_range = pd.DataFrame({'TIMESTAMP': date_range})

            iab3_alldates = pd.merge(left=df_date_range, right=iab3_df_copy, how='outer')
            iab3_alldates.loc[iab3_alldates['ET'].isnull(), "ET"] = 0

            train_X, val_X = train_test_split(iab3_alldates['ET'], shuffle=False)

            generator_train = TimeseriesGenerator(train_X, train_X, length=length, batch_size=batch_size)
            generator_val = TimeseriesGenerator(val_X, val_X, length=length, batch_size=batch_size)

            model = self.lstm_conv1d_univariate_model(length=length,
                                                      generator_train=generator_train,
                                                      generator_val=generator_val,
                                                      epochs=2)
            lstm_conv1d_forecast = self.lstm_model_forecast(model, iab3_alldates['ET'].to_numpy()[..., np.newaxis], length)
            lstm_conv1d_forecast = np.insert(lstm_conv1d_forecast, 0, [0 for i in range(length-1)])

            validation_data = pd.DataFrame({'TIMESTAMP': date_range})
            validation_data['ET_lstm_conv1d_u'] = lstm_forecast

            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=validation_data[['TIMESTAMP','ET_lstm_conv1d_u']], on='TIMESTAMP', how='outer')

        if 'lstm_m' in listOfmethods:
            print('LSTM_m...')
            self.ET_names.append('ET_lstm_m')

            length = 12
            batch_size = 3

            iab3_df_copy = self.dropping_bad_data()
            column_x = ['Rn_Avg', 'RH', 'VPD','air_temperature', 'shf_Avg(1)','shf_Avg(2)','e','wind_speed']

            iab3_df_copy.dropna(subset=column_x, inplace=True)

            date_range = pd.date_range(start=iab3_df_copy['TIMESTAMP'].min(),
                                       end=iab3_df_copy['TIMESTAMP'].max(),
                                       freq='30min')


            df_date_range = pd.DataFrame({'TIMESTAMP': date_range})

            iab3_alldates = pd.merge(left=df_date_range, right=iab3_df_copy, how='outer')

            column_x_n = ['Rn_Avg_n', 'RH_n','VPD_n','air_temperature_n','shf_Avg(1)_n','shf_Avg(2)_n','e_n','wind_speed_n']
            for i in column_x:
                iab3_alldates.loc[iab3_alldates[i].isna(), i] = 0
                iab3_alldates[f'{i}_n'] = preprocessing.scale(iab3_alldates[i])

            # print(iab3_alldates[column_x_n].describe())

            iab3_alldates['ET_shift'] = iab3_alldates['ET'].shift(1)
            generator_t = TimeseriesGenerator(iab3_alldates[column_x_n].to_numpy(), iab3_alldates['ET_shift'].to_numpy(), length=length, batch_size=3, shuffle=False)

            model = self.lstm_multivariate_model(length=length,
                                                 generator_train=generator_t,
                                                 generator_val=generator_t,
                                                 epochs=2)
            generator_prediction = TimeseriesGenerator(iab3_alldates[column_x_n].to_numpy(), iab3_alldates['ET_shift'].to_numpy(), length=length, batch_size=len(iab3_alldates[column_x_n]), shuffle=False)

            for i in generator_prediction:
                forecast = model.predict(i[0])
            lstm_forecast = np.insert(forecast, 0, [0 for i in range(length)])

            iab3_alldates['ET_lstm_multi_shift'] = lstm_forecast
            iab3_alldates['ET_lstm_m'] = iab3_alldates['ET_lstm_multi_shift'].shift(-1)
            self.iab3_ET_timestamp = pd.merge(left=self.iab3_ET_timestamp, right=iab3_alldates[['TIMESTAMP','ET_lstm_m']], on='TIMESTAMP', how='outer')


        print(self.iab3_ET_timestamp[self.ET_names+['ET']].describe())
        # print(self.iab3_ET_timestamp[['ET_lr','ET_pm']].describe())
        # print(self.iab3_ET_timestamp.loc[self.iab3_ET_timestamp['ET_pm'].notna()].describe())
        # print(self.iab3_ET_timestamp[['ET', 'ET_lstm_u']].corr())

    def join_ET(self):
        self.filled_ET = []
        for et in self.ET_names:
            self.filled_ET.append(f'{et}_and_ET')
            self.iab3_ET_timestamp[f'{et}_and_ET'] = self.iab3_ET_timestamp.loc[self.iab3_ET_timestamp['ET'].notna(), 'ET']
            self.iab3_ET_timestamp.loc[self.iab3_ET_timestamp[et]<0, et] = 0
            self.iab3_ET_timestamp.loc[self.iab3_ET_timestamp[f'{et}_and_ET'].isna(), f'{et}_and_ET'] = self.iab3_ET_timestamp[et]

    def plot(self):
        print(self.iab3_ET_timestamp[self.ET_names+['ET']].describe())
        print(self.iab3_ET_timestamp[self.filled_ET+['ET']].cumsum().plot())
        # print(self.iab3_ET_timestamp[self.ET_names+['ET']].cumsum().plot())

    def stats_others(self, stats=[], which=[]):
        iab3_df = self.iab3_df
        if 'gaps' in stats:

            print(iab3_df.columns)

            print(self.iab1_df.columns)

            print(self.iab2_df_resample.columns)

            fig_01, ax = plt.subplots(2, figsize=(15,10))
            b = iab3_df.set_index('TIMESTAMP')
            b.resample('D').count()[['Rn_Avg', 'RH', 'VPD','shf_Avg(1)','shf_Avg(2)']].plot(ax=ax[0])

            # b.resample('D').count()[['ga','gc']].plot(ax=ax[1])
        if 'pm' in stats:
            b = iab3_df.set_index('TIMESTAMP')
            b.resample('D').count()[['ga','gc']].plot(ax=ax[1])


    def stats_ET(self,stats=[]):
        if 'gaps' in stats:
            without_bigGAP = False

            fig_01, ax = plt.subplots(len(self.filled_ET)+2, figsize=(15,100))
            b = self.iab3_ET_timestamp.set_index('TIMESTAMP')
            b.resample('D').count()[self.filled_ET+['ET']].plot(ax=ax[0], figsize=(15,30))
            ax[0].set_ylim((0,48))
            ax[0].set_title('Count of gaps')

            for j, variable in enumerate(['ET']+self.filled_ET):
                # print(j, variable)
                et_diff = self.iab3_ET_timestamp.loc[(self.iab3_ET_timestamp[f'{variable}'].notna()), 'TIMESTAMP'].diff()

                if without_bigGAP == False:
                    gaps_et_index = et_diff.loc[et_diff>pd.Timedelta('00:30:00')].value_counts().sort_index().index
                    gap_cumulative = gaps_et_index/pd.Timedelta('00:30:00')-1
                    gaps_et_index = [str(i) for i in gaps_et_index]
                    gaps_et_count = et_diff.loc[et_diff>pd.Timedelta('00:30:00')].value_counts().sort_index().values

                elif without_bigGAP == True:
                    gaps_et_index = et_diff.loc[(et_diff>pd.Timedelta('00:30:00')) & (et_diff<pd.Timedelta('120 days'))].value_counts().sort_index().index
                    gap_cumulative = gaps_et_index/pd.Timedelta('00:30:00')-1
                    gaps_et_index = [str(i) for i in gaps_et_index]
                    gaps_et_count = et_diff.loc[(et_diff>pd.Timedelta('00:30:00')) & (et_diff<pd.Timedelta('120 days'))].value_counts().sort_index().values



                ax2 = ax[j+1].twinx()



                gaps_sizes = ax[j+1].bar(gaps_et_index, gaps_et_count)
                # plt.xticks(rotation=90)
                ax[j+1].set_xticklabels(labels=gaps_et_index,rotation=90)
                ax[j+1].set_title(f'{variable} GAPS')
                for i, valor in enumerate(gaps_et_count):
                    ax[j+1].text(i-0.5, valor+1, str(valor))

                ax2.plot(gaps_et_index, gap_cumulative*gaps_et_count, color='red',linestyle='--')

                # ax[j+1].set_xticklabels([])

            fig_01.tight_layout()

        if 'corr' in stats:
            corr = self.iab3_ET_timestamp.loc[(self.iab3_ET_timestamp['ET'].notna()), ['ET']+self.ET_names].corr()
            print(corr)

        # print(self.iab3_ET_timestamp.loc[:, ['TIMESTAMP', 'ET']+self.filled_ET].describe())




if __name__ == '__main__':
    gapfilling_iab3(ep_path=r'G:\Meu Drive\USP-SHS\Resultados_processados\EddyPro_Fase010203',
                    lf_path=r'G:\Meu Drive\USP-SHS\Mestrado\Dados_Brutos\IAB3',
                    iab1_path=r'G:\Meu Drive\USP-SHS\Mestrado\Dados_Brutos\IAB1\IAB1',
                    iab2_path=r'G:\Meu Drive\USP-SHS\Mestrado\Dados_Brutos\IAB2\IAB2')
