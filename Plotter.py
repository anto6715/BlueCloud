import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

import numpy as np
import xarray as xr

from PIL import Image, ImageFont, ImageDraw


class Plotter:
    '''New class for visualisation of data from pyxpcm

       Parameters
       ----------
           ds: dataset including PCM results
           m: pyxpcm model
           coords_dict: (optional) dictionary with coordinates names (ex: {'latitude': 'lat', 'time': 'time', 'longitude': 'lon'})
           cmap_name: (optional) colormap name (default: 'Accent')

           '''

    def __init__(self, ds, m, coords_dict=None, cmap_name='Accent'):

        # TODO: automatic detection of PCM_LABELS and q_variable ?
        # TODO: Check if the PCM is trained:
        # validation.check_is_fitted(m, 'fitted')
        # TODO: automatic detection of vertical dimension
        # TODO: check if datatype works with different datasets

        self.ds = ds
        self.m = m
        self.cmap_name = cmap_name

        # check if dataset should include PCM variables
        assert ("PCM_LABELS" in self.ds), "Dataset should include PCM_LABELS variable to be plotted. Use pyxpcm.predict function with inplace=True option"

        if coords_dict == None:
            # creates dictionary with coordinates
            coords_list = list(self.ds.coords.keys())
            coords_dict = {}
            for c in coords_list:
                axis_at = self.ds[c].attrs.get('axis')
                if axis_at == 'Y':
                    coords_dict.update({'latitude': c})
                if axis_at == 'X':
                    coords_dict.update({'longitude': c})
                if axis_at == 'T':
                    coords_dict.update({'time': c})

            self.coords_dict = coords_dict

            if 'latitude' not in coords_dict or 'longitude' not in coords_dict:
                raise ValueError(
                    'Coordinates not found in dataset. Please, define coordinates using coord_dict input')

        else:
            self.coords_dict = coords_dict

        # assign a data type
        dims_dict = list(ds.dims.keys())
        dims_dict = [e for e in dims_dict if e not in (
            'quantile', 'pcm_class')]
        if len(dims_dict) > 2:
            self.data_type = 'gridded'
        else:
            self.data_type = 'profile'

    def pie_classes(self):
        """Pie chart of classes

            name: name of the colormap, eg 'Paired' or 'jet'
            K: number of colors in the final discrete colormap
        """

        # loop in k for counting
        pcm_labels = self.ds['PCM_LABELS']
        kmap = self.m.plot.cmap(name=self.cmap_name)

        for cl in range(self.m.K):
            # get labels
            pcm_labels_k = pcm_labels.where(pcm_labels == cl)
            if cl == 0:
                counts_k = pcm_labels_k.count(...)
                pie_labels = list(['K=%i' % cl])
                table_cn = list([[str(cl), str(counts_k.values)]])
            else:
                counts_k = xr.concat([counts_k, pcm_labels_k.count(...)], "k")
                pie_labels.append('K=%i' % cl)
                table_cn.append([str(cl), str(counts_k[cl].values)])

        fig, ax = plt.subplots(ncols=2, figsize=(10, 6))
        # fig.set_cmap(kmap)

        cheader = ['k', 'profiles']
        ccolors = plt.cm.BuPu(np.full(len(cheader), 0.1))
        the_table = plt.table(cellText=table_cn, cellLoc='center', loc='center left',
                              colLabels=cheader, colColours=ccolors, fontsize=12)

        kmap_n = [list(kmap(k)[0:3]) for k in range(self.m.K)]
        ax[0].pie(counts_k, labels=pie_labels, autopct='%1.1f%%',
                  shadow=True, startangle=90, colors=kmap_n)
        ax[0].axis('equal')
        ax[1].get_xaxis().set_visible(False)
        ax[1].get_yaxis().set_visible(False)
        plt.box(on=None)
        the_table.scale(1, 1.5)
        fig.suptitle(r"$\bf{"'Classes'"}$"+' ' + r"$\bf{"'distribution'"}$")
        plt.tight_layout()

    @staticmethod
    def cmap_discretize(name, K):
        """Return a discrete colormap from a quantitative or continuous colormap name

            name: name of the colormap, eg 'Paired' or 'jet'
            K: number of colors in the final discrete colormap
        """
        if name in ['Set1', 'Set2', 'Set3', 'Pastel1', 'Pastel2', 'Paired', 'Dark2', 'Accent']:
            # Segmented (or quantitative) colormap:
            N_ref = {'Set1': 9, 'Set2': 8, 'Set3': 12, 'Pastel1': 9,
                     'Pastel2': 8, 'Paired': 12, 'Dark2': 8, 'Accent': 8}
            N = N_ref[name]
            cmap = plt.get_cmap(name=name)
            colors_i = np.concatenate(
                (np.linspace(0, 1., N), (0., 0., 0., 0.)), axis=0)
            cmap = cmap(colors_i)  # N x 4
            n = np.arange(0, N)
            new_n = n.copy()
            if K > N:
                for k in range(N, K):
                    r = np.roll(n, -k)[0][np.newaxis]
                    new_n = np.concatenate((new_n, r), axis=0)
            new_cmap = cmap.copy()
            new_cmap = cmap[new_n, :]
            new_cmap = mcolors.LinearSegmentedColormap.from_list(
                name + "_%d" % K, colors=new_cmap, N=K)
        else:
            # Continuous colormap:
            N = K
            cmap = plt.get_cmap(name=name)
            colors_i = np.concatenate(
                (np.linspace(0, 1., N), (0., 0., 0., 0.)))
            colors_rgba = cmap(colors_i)  # N x 4
            indices = np.linspace(0, 1., N + 1)
            cdict = {}
            for ki, key in enumerate(('red', 'green', 'blue')):
                cdict[key] = [(indices[i], colors_rgba[i - 1, ki], colors_rgba[i, ki])
                              for i in np.arange(N + 1)]
            # Return colormap object.
            new_cmap = mcolors.LinearSegmentedColormap(
                cmap.name + "_%d" % N, cdict, N)
        return new_cmap

    def vertical_structure(self,
                           q_variable,
                           xlim=None,
                           classdimname='pcm_class',
                           quantdimname='quantile',
                           maxcols=3,
                           cmap=None,
                           ylabel='depth (m)',
                           ylim='auto',
                           **kwargs):
        '''Plot vertical structure of each class

           Parameters
           ----------
               q_variable: quantile variable calculated with pyxpcm.quantile function (inplace=True option)
               xlim: (optional) x axis limits 
               classdimname: (optional) pcm classes dimension name (default = 'pcm_class')
               quantdimname: (optional) pcm quantiles dimension name (default = 'quantiles')
               maxcols: (optional) max number of column (default = 3)
               cmap: (optional) colormap name for quantiles (default = 'brg')
               ylabel: (optional) y axis label (default = 'depth (m)')
               ylim: (optional) y axis limits (default = 'auto')
               **kwargs

           Returns
           ------
               fig : :class:`matplotlib.pyplot.figure.Figure`
               ax : :class:`matplotlib.axes.Axes` object or array of Axes objects.
                    *ax* can be either a single :class:`matplotlib.axes.Axes` object or an
                    array of Axes objects if more than one subplot was created.  The
                    dimensions of the resulting array can be controlled with the squeeze
                    keyword.

               '''

        # copy of pyxpcm.plot.quantile function
        # TODO: Is it neccesary to use all this options in function?
        # TODO: detection of quantile variable?

        # select quantile variable
        da = self.ds[q_variable]

        ###########################################################################
        # da must be 3D with a dimension for: CLASS, QUANTILES and a vertical axis
        # The QUANTILES dimension is called "quantile"
        # The CLASS dimension is identified as the one matching m.K length.
        if classdimname in da.dims:
            CLASS_DIM = classdimname
        elif (np.argwhere(np.array(da.shape) == self.m.K).shape[0] > 1):
            raise ValueError(
                "Can't distinguish the class dimension from the others")
        else:
            CLASS_DIM = da.dims[np.argwhere(
                np.array(da.shape) == self.m.K)[0][0]]
        QUANT_DIM = quantdimname
        VERTICAL_DIM = list(
            set(da.dims) - set([CLASS_DIM]) - set([QUANT_DIM]))[0]
        ############################################################################

        nQ = len(da[QUANT_DIM])  # Nb of quantiles

        # cmapK = self.m.plot.cmap()  # cmap_discretize(plt.cm.get_cmap(name='Paired'), m.K)
        cmapK = self.cmap_discretize(
            plt.cm.get_cmap(name=self.cmap_name), self.m.K)
        if not cmap:
            cmap = self.cmap_discretize(plt.cm.get_cmap(name='brg'), nQ)
        defaults = {'figsize': (10, 8), 'dpi': 80,
                    'facecolor': 'w', 'edgecolor': 'k'}
        fig, ax = self.m.plot.subplots(
            maxcols=maxcols, **{**defaults, **kwargs})  # TODO: function in pyxpcm

        if not xlim:
            xlim = np.array([0.9 * da.min(), 1.1 * da.max()])
        for k in self.m:
            Qk = da.loc[{CLASS_DIM: k}]
            for (iq, q) in zip(np.arange(nQ), Qk[QUANT_DIM]):
                Qkq = Qk.loc[{QUANT_DIM: q}]
                ax[k].plot(Qkq.values.T, da[VERTICAL_DIM], label=(
                    "%0.2f") % (Qkq[QUANT_DIM]), color=cmap(iq))
            ax[k].set_title(("Component: %i") % (k), color=cmapK(k))
            ax[k].legend(loc='lower right')
            ax[k].set_xlim(xlim)
            if isinstance(ylim, str):
                ax[k].set_ylim(
                    np.array([da[VERTICAL_DIM].min(), da[VERTICAL_DIM].max()]))
            else:
                ax[k].set_ylim(ylim)
            # ax[k].set_xlabel(Q.units)
            if k == 0:
                ax[k].set_ylabel(ylabel)
            ax[k].grid(True)
        plt.subplots_adjust(top=0.90)
        fig.suptitle(r"$\bf{"'Vertical'"}$"+' ' + r"$\bf{"'structure'"}$" +
                     ' '+r"$\bf{"'of'"}$"+' '+r"$\bf{"'classes'"}$")
        # plt.tight_layout()

    def vertical_structure_comp(self, q_variable,
                                plot_q='all',
                                xlim=None,
                                classdimname='pcm_class',
                                quantdimname='quantile',
                                maxcols=3, cmap=None,
                                ylabel='depth (m)',
                                ylim='auto',
                                **kwargs):
        '''Plot vertical structure of each class

           Parameters
           ----------
               q_variable: quantile variable calculated with pyxpcm.quantile function (inplace=True option)
               plot_q: quantiles to be plotted
               classdimname

               quantdimname

               maxcols

               ylim

               Returns


           Returns
           ------
               fig : :class:`matplotlib.pyplot.figure.Figure`

               ax : :class:`matplotlib.axes.Axes` object or array of Axes objects.
                    *ax* can be either a single :class:`matplotlib.axes.Axes` object or an
                    array of Axes objects if more than one subplot was created.  The
                    dimensions of the resulting array can be controlled with the squeeze
                    keyword.

               '''

        # TODO: merge with vertical_structure function
        # TODO: automatic number of rows

        # select quantile variable
        da = self.ds[q_variable]

        ###########################################################################
        # da must be 3D with a dimension for: CLASS, QUANTILES and a vertical axis
        # The QUANTILES dimension is called "quantile"
        # The CLASS dimension is identified as the one matching m.K length.
        if classdimname in da.dims:
            CLASS_DIM = classdimname
        elif (np.argwhere(np.array(da.shape) == self.m.K).shape[0] > 1):
            raise ValueError(
                "Can't distinguish the class dimension from the others")
        else:
            CLASS_DIM = da.dims[np.argwhere(
                np.array(da.shape) == self.m.K)[0][0]]
        QUANT_DIM = quantdimname
        VERTICAL_DIM = list(
            set(da.dims) - set([CLASS_DIM]) - set([QUANT_DIM]))[0]
        ############################################################################

        nQ = len(da[QUANT_DIM])  # Nb of quantiles

        if isinstance(plot_q, str):  # plot all quantiles, default
            q_range = np.arange(0, nQ)
        else:
            q_range = np.where(da[QUANT_DIM].isin(plot_q))[0]

        nQ_p = len(q_range)  # Nb of plots

        # cmap_discretize(plt.cm.get_cmap(name='Paired'), m.K)
        cmapK = self.m.plot.cmap(name=self.cmap_name)
        #cmapK = self.cmap_discretize(plt.cm.get_cmap(name='Accent'), self.m.K)
        if not cmap:
            cmap = self.cmap_discretize(plt.cm.get_cmap(name='brg'), nQ)

        if not xlim:
            xlim = np.array([0.9 * da.min(), 1.1 * da.max()])

        fig, ax = plt.subplots(nrows=1, ncols=nQ_p, figsize=(
            10, 8), facecolor='w', edgecolor='k', sharey=True,  squeeze=False)
        cnt = 0
        for q in q_range:
            Qq = da.loc[{QUANT_DIM: da[QUANT_DIM].values[q]}]
            for k in self.m:
                Qqk = Qq.loc[{CLASS_DIM: k}]
                ax[0][cnt].plot(Qqk.values.T, da[VERTICAL_DIM], label=(
                    "K=%i") % (Qqk[CLASS_DIM]), color=cmapK(k))
            ax[0][cnt].set_title(("quantile: %.2f") % (
                da[QUANT_DIM].values[q]), color=cmap(q), fontsize=12)
            ax[0][cnt].legend(loc='lower right', fontsize=11)
            ax[0][cnt].set_xlim(xlim)
            if isinstance(ylim, str):
                ax[0][cnt].set_ylim(
                    np.array([da[VERTICAL_DIM].min(), da[VERTICAL_DIM].max()]))
            else:
                ax[0][cnt].set_ylim(ylim)
            # ax[k].set_xlabel(Q.units)
            if k == 0:
                ax[0][cnt].set_ylabel(ylabel)
            ax[0][cnt].grid(True)
            cnt = cnt+1

        plt.subplots_adjust(top=0.90)
        plt.rc('xtick', labelsize=12)
        plt.rc('ytick', labelsize=12)
        fig.suptitle(r"$\bf{"'Vertical'"}$"+' ' + r"$\bf{"'structure'"}$" +
                     ' '+r"$\bf{"'of'"}$"+' '+r"$\bf{"'classes'"}$")
        fig.text(0.04, 0.5, 'depth (m)', va='center',
                 rotation='vertical', fontsize=12)
        # plt.tight_layout()

    def spatial_distribution(self, proj=ccrs.PlateCarree(), extent='auto', time_slice=0):
        '''Plot spatial distribution of classes

           Parameters
           ----------
               proj: projection
               extent: map extent
               time_slice: time snapshot to be plot (default 0). If time_slice = 'most_freq_label', most frequent label in dataseries is plotted.

           Returns
           -------

               '''
        # TODO: check if time variable exits if not error (time variable should be 'time' at the moment)
        # TODO: make default values for projection and extent (dataset extent)

        def get_most_freq_labels(this_ds):
            this_ds = this_ds.stack(
                {'N_OBS': [d for d in this_ds['PCM_LABELS'].dims if d != 'time']})

            def fct(this):
                def most_prob_label(vals):
                    return np.argmax(np.bincount(vals))
                mpblab = []
                for i in this['N_OBS']:
                    val = this.sel(N_OBS=i)['PCM_LABELS'].values
                    res = np.nan
                    if np.count_nonzero(~np.isnan(val)) != 0:
                        res = most_prob_label(val.astype('int'))
                    mpblab.append(res)
                mpblab = np.array(mpblab)
                return xr.DataArray(mpblab, dims='N_OBS', coords={'N_OBS': this['N_OBS']}, name='PCM_MOST_FREQ_LABELS').to_dataset()
            this_ds['PCM_MOST_FREQ_LABELS'] = this_ds.map_blocks(
                fct)['PCM_MOST_FREQ_LABELS'].load()
            return this_ds.unstack('N_OBS')

        # spatial extent
        if isinstance(extent, str):
            extent = np.array([min(self.ds[self.coords_dict.get('longitude')]), max(self.ds[self.coords_dict.get('longitude')]), min(self.ds[self.coords_dict.get('latitude')]), max(self.ds[self.coords_dict.get('latitude')])]) + np.array([-0.1, +0.1, -0.1, +0.1])
        
        if isinstance(time_slice, str):
            dsp = get_most_freq_labels(self.ds)
            var_name = 'PCM_MOST_FREQ_LABELS'
            title_str = r"$\bf{"'Spatial'"}$"+' ' + r"$\bf{"'ditribution'"}$"+' ' + \
                r"$\bf{"'of'"}$"+' '+r"$\bf{"'classes'"}$" + \
                ' \n (most frequent label in time series)'
        else:
            dsp = self.ds.isel(time=time_slice)
            var_name = 'PCM_LABELS'
            title_str = r"$\bf{"'Spatial'"}$"+' ' + r"$\bf{"'ditribution'"}$"+' '+r"$\bf{"'of'"}$"+' ' + \
                r"$\bf{"'classes'"}$" + \
                ' \n (time: ' + \
                '%s' % dsp["time"].dt.strftime("%Y/%m/%d %H:%M").values + ')'

        subplot_kw = {'projection': proj, 'extent': extent}
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(
            6, 6), dpi=120, facecolor='w', edgecolor='k', subplot_kw=subplot_kw)
        # TODO: function already in pyxpcm
        kmap = self.m.plot.cmap(name=self.cmap_name)

        # check if gridded or profiles data
        if self.data_type == 'profiles':
            ax.scatter(dsp[self.coords_dict.get('longitude')], dsp[self.coords_dict.get('latitude')], s=3,
                       c=self.ds[var_name], cmap=kmap, transform=proj, vmin=0, vmax=self.m.K)
        if self.data_type == 'gridded':
            ax.pcolormesh(dsp[self.coords_dict.get('longitude')], dsp[self.coords_dict.get('latitude')], dsp[var_name],
                          cmap=kmap, transform=proj, vmin=0, vmax=self.m.K)

        # TODO: function already in pyxpcm
        self.m.plot.colorbar(ax=ax, cmap='Accent', shrink=0.3)
        self.m.plot.latlongrid(ax, dx=10)  # TODO: function already in pyxpcm
        land_feature=cfeature.NaturalEarthFeature(category='physical',name='land',scale='50m',facecolor=[0.4,0.6,0.7])
        ax.add_feature(land_feature, edgecolor='black')
        ax.set_title(title_str)
        fig.canvas.draw()
        fig.tight_layout()
        plt.margins(0.1)

    def plot_posteriors(self, proj=ccrs.PlateCarree(), extent='auto', time_slice=0):
        '''Plot posteriors in a map

           Parameters
           ----------
               proj: projection (default ccrs.PlateCarree())
               extent: map extent (default 'auto')
               time_slice: time snapshot to be plot (default 0)

           Returns
           -------

           '''
        # TODO: class colors in title in subplots using colormap
        # TODO: time should be called time in dataset. use coords_dict

        dsp = self.ds.isel(time=time_slice)

        # spatial extent
        if isinstance(extent, str):
            extent = np.array([min(dsp[self.coords_dict.get('longitude')]), max(dsp[self.coords_dict.get('longitude')]), min(dsp[self.coords_dict.get('latitude')]), max(dsp[self.coords_dict.get('latitude')])]) + np.array([-0.1, +0.1, -0.1, +0.1])

        # check if PCM_POST variable exists
        assert ("PCM_POST" in dsp), "Dataset should include PCM_POST varible to be plotted. Use pyxpcm.predict_proba function with inplace=True option"

        cmap = sns.light_palette("blue", as_cmap=True)
        subplot_kw = {'projection': proj, 'extent': extent}
        land_feature=cfeature.NaturalEarthFeature(category='physical',name='land',scale='50m',facecolor=[0.4,0.6,0.7])
        # TODO: function already in pyxpcm
        fig, ax = self.m.plot.subplots(
            figsize=(10, 16), maxcols=2, subplot_kw=subplot_kw)

        for k in self.m:
            if self.data_type == 'profiles':
                sc = ax[k].scatter(dsp[self.coords_dict.get('longitude')], self.ds[self.coords_dict.get('latitude')], s=3, c=dsp['PCM_POST'].sel(pcm_class=k),
                                   cmap=cmap, transform=proj, vmin=0, vmax=1)
            if self.data_type == 'gridded':
                sc = ax[k].pcolormesh(dsp[self.coords_dict.get('longitude')], dsp[self.coords_dict.get('latitude')], dsp['PCM_POST'].sel(pcm_class=k),
                                      cmap=cmap, transform=proj, vmin=0, vmax=1)

            plt.colorbar(sc, ax=ax[k], fraction=0.03, shrink=0.7)
            self.m.plot.latlongrid(ax[k], fontsize=8, dx=20, dy=10)

            
            ax[k].add_feature(land_feature, edgecolor='black')
            ax[k].set_title('PCM Posteriors for k=%i' % k)

        fig.suptitle(r"$\bf{"'PCM  Posteriors'"}$" + ' \n probability of a profile to belong to a class k'
                     + ' \n (time: ' + '%s' % dsp["time"].dt.strftime("%Y/%m/%d %H:%M").values + ')')
        #plt.subplots_adjust(wspace=0.1, hspace=0.1)
        # fig.canvas.draw()
        fig.tight_layout()
        # fig.subplots_adjust(top=0.95)

    def temporal_distribution(self, time_bins, start_month=0):
        '''Plot temporal distribution of classes by moth or by season

           Parameters
           ----------
                time_bins: 'month' or 'season'
                start_month: (optional) start plot in this month (index from 1:Jan to 12:Dec)

            Returns
            -------

        '''

        # check if more than one temporal step
        assert (len(self.ds[self.coords_dict.get('time')]) >
                1), "Length of time variable should be > 1"

        # data to be plot
        # TODO: is it the best way??
        pcm_labels = self.ds['PCM_LABELS']
        kmap = self.m.plot.cmap(name=self.cmap_name)


        if time_bins == 'month':
            xaxis_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                                'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            if start_month != 0:
                new_order = np.concatenate((np.arange(start_month,13), np.arange(1,start_month)))
                xaxis_labels = [xaxis_labels[i-1] for i in new_order]
        if time_bins == 'season':
            seasons_dict = {1: 'DJF', 2: 'MAM', 3: 'JJA', 4: 'SON'}
            xaxis_labels = ['DJF', 'MAM', 'JJA', 'SON']

        fig, ax = plt.subplots(figsize=(10, 6))

        # loop in k for counting
        for cl in range(self.m.K):
            # get time array with k=cl
            pcm_labels_k = pcm_labels.where(pcm_labels == cl)

            if cl == 0:
                counts_k = pcm_labels_k.groupby(
                    self.coords_dict.get('time') + '.' + time_bins).count(...)
            else:
                counts_k = xr.concat([counts_k, pcm_labels_k.groupby(
                    self.coords_dict.get('time') + '.' + time_bins).count(...)], "k")

        counts_k = counts_k/sum(counts_k)*100
        # change order
        if start_month != 0:
            counts_k = counts_k.reindex({'month': new_order})
    
        #start point in stacked bars
        counts_cum = counts_k.cumsum(axis=0)

        # loop for plotting
        for cl in range(self.m.K):

            if time_bins == 'month':
                starts = counts_cum.isel(k=cl) - counts_k.isel(k=cl)
                #ax.barh(counts_k.month, counts_k.isel(k=cl), left=starts, color=kmap(cl), label='K=' + str(cl))
                ax.barh(xaxis_labels, counts_k.isel(k=cl), left=starts, color=kmap(cl), label='K=' + str(cl))
                    
            if time_bins == 'season':
                x_ticks_k = []
                for i in range(len(counts_k.season)):
                    x_ticks_k.append(
                       list(seasons_dict.values()).index(counts_k.season[i])+1)
                    # print(x_ticks_k)
                # plot
                starts = counts_cum.isel(k=cl) - counts_k.isel(k=cl)
                ax.barh(x_ticks_k, counts_k.isel(k=cl), left=starts, label='K=' + str(cl),
                        color=kmap(cl))

        # format
        title_string = r'Percentage of profiles in each class by $\bf{' + time_bins + '}$'
        ylabel_string = '% of profiles'
        plt.gca().invert_yaxis()
        if time_bins == 'season':
            ax.set_yticks(np.arange(1, len(xaxis_labels)+1))
        ax.set_yticklabels(xaxis_labels, fontsize=12)
        plt.yticks(fontsize=12)
        ax.legend(fontsize=12, bbox_to_anchor=(1.01, 1), loc='upper left')
        ax.set_xlabel(ylabel_string, fontsize=12)
        ax.set_title(title_string, fontsize=14)
        fig.tight_layout()

    @staticmethod
    def add_lowerband(mfname, outfname, band_height=70, color=(255, 255, 255, 255)):
        """ Add lowerband to a figure

            Parameters
            ----------
            mfname : string
                source figure file
            outfname : string
                output figure file
        """
        # TODO: do I need to use self here?
        image = Image.open(mfname, 'r')
        image_size = image.size
        width = image_size[0]
        height = image_size[1]
        background = Image.new('RGBA', (width, height + band_height), color)
        background.paste(image, (0, 0))
        background.save(outfname)

    def add_2logo(self, mfname, outfname, logo_height=70, txt_color=(0, 0, 0, 255), data_src='CMEMS'):
        """ Add 2 logos and text to a figure

            Parameters
            ----------
            mfname : string
                source figure file
            outfname : string
                output figure file
        """
        def pcm1liner(this_pcm):
            def prtval(x): return "%0.2f" % x
            def getrge(x): return [np.max(x), np.min(x)]
            def prtrge(x): return "[%s:%s]" % (
                prtval(getrge(x)[0]), prtval(getrge(x)[1]))
            def prtfeatures(p): return "{%s}" % ", ".join(
                ["'%s':%s" % (k, prtrge(v)) for k, v in p.features.items()])
            return "PCM model information: K:%i, F:%i%s, %s" % (this_pcm.K,
                                                                this_pcm.F,
                                                                prtfeatures(
                                                                    this_pcm),
                                                                this_pcm._props['with_classifier'].upper())

        font_path = "logos/Calibri_Regular.ttf"
        lfname2 = "logos/Blue-cloud_compact_color_W.jpg"
        lfname1 = "logos/Logo-LOPS_transparent_W.jpg"

        mimage = Image.open(mfname)

        # Open logo images:
        limage1 = Image.open(lfname1)
        limage2 = Image.open(lfname2)

        # Resize logos to match the requested logo_height:
        aspect_ratio = limage1.size[1]/limage1.size[0]  # height/width
        simage1 = limage1.resize((int(logo_height/aspect_ratio), logo_height))

        aspect_ratio = limage2.size[1]/limage2.size[0]  # height/width
        simage2 = limage2.resize((int(logo_height/aspect_ratio), logo_height))

        # Paste logos along the lower white band of the main figure:
        box = (0, mimage.size[1]-logo_height)
        mimage.paste(simage1, box)

        box = (simage1.size[0], mimage.size[1]-logo_height)
        mimage.paste(simage2, box)

        # Add dataset and model information
        # time extent
        if len(self.ds.time.sizes) == 0:
            # TODO: when using isel hours information is lost
            time_extent = self.ds["time"].dt.strftime("%Y/%m/%d %H:%M")
            time_string = 'Period: %s' % time_extent.values
        else:
            time_extent = [min(self.ds["time"].dt.strftime(
                "%Y/%m/%d")), max(self.ds["time"].dt.strftime("%Y/%m/%d"))]
            time_string = 'Period: from %s to %s' % (
                time_extent[0].values, time_extent[1].values)

        # spatial extent
        lat_extent = [min(self.ds[self.coords_dict.get('latitude')].values), max(
            self.ds[self.coords_dict.get('latitude')].values)]
        lon_extent = [min(self.ds[self.coords_dict.get('longitude')].values), max(
            self.ds[self.coords_dict.get('longitude')].values)]
        spatial_string = 'Domain: lat:%s, lon:%s' % (
            str(lat_extent), str(lon_extent))

        txtA = "User selection:\n   %s\n   %s\n   %s\nSource: %s\n%s" % (self.ds.attrs.get(
            'title'), time_string, spatial_string, self.ds.attrs.get('credit'), pcm1liner(self.m))
        fontA = ImageFont.truetype(font_path, 10)

        txtsA = fontA.getsize_multiline(txtA)

        xoffset = 5 + simage1.size[0] + simage2.size[0]
        if 0:  # Align text to the top of the band:
            posA = (xoffset, mimage.size[1]-logo_height - 1)
        else:  # Align text to the bottom of the band:
            posA = (xoffset, mimage.size[1]-txtsA[1]-5)

        # Print
        drawA = ImageDraw.Draw(mimage)
        drawA.text(posA, txtA, txt_color, font=fontA)

        # Final save
        mimage.save(outfname)

    def save_BlueCloud(self, out_name):  # function which saves figure and add logos

        # save image
        # plt.margins(0.1)
        plt.savefig(out_name, bbox_inches='tight', pad_inches=0.1)

        # add lower band
        #self.add_lowerband(out_name, out_name, band_height = 120, color=(255, 255, 255, 255))
        self.add_lowerband(out_name, out_name)

        # add logo
        #self.add_2logo(out_name, out_name, logo_height=120, txt_color=(0, 0, 0, 255), data_src='CMEMS')
        self.add_2logo(out_name, out_name)

        print('Figure saved in %s' % out_name)

    pass
