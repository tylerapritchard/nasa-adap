import matplotlib.pyplot as plt
import json
import pandas as pd
import os
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, Matern
from sklearn.model_selection import train_test_split
from statistics import mean, stdev
import warnings

from typing import Union, Optional


warnings.filterwarnings('ignore')

class CAAT:

    def __init__(self):
        #This might need to be replaced long term with some configuration parameters/config file    
        base_path = '../data/'
        base_db_name = 'caat.csv'
        db_loc = base_path + base_db_name

        if(os.path.isfile(db_loc)):
            #Chech to see if db file exists 
            self.caat=pd.read_csv(db_loc)
        else:
            raise Warning("No db file found")
    
    @staticmethod
    def create_db_file(type_list = None):
        #This might need to be replaced long term with some configuration parameters/config file    
        base_path = '../data/'
        base_db_name = 'caat.csv'
        db_loc = base_path + base_db_name

        #Create A List Of Folders To Parse
        if type_list is None:
            type_list = ["SESNE", "SLSN-I", "SLSN-II", "SNII", "SNIIn"]

        sndb_name = []
        sndb_type = []
        sndb_subtype = []
        #etc
        for sntype in type_list:
            """ For each folder:
            get a list of subfolders
            get a list of objects in each folder
            assign SN, subtypes to list
            """
            subtypes = os.listdir(base_path+sntype+"/")
            for snsubtype in subtypes:
                sn_names = os.listdir(base_path+sntype+"/"+snsubtype+"/")

                sndb_name.extend(sn_names)
                sndb_type.extend([sntype] * len(sn_names))
                sndb_subtype.extend([snsubtype] * len(sn_names))

        sndb = pd.DataFrame({"Name": sndb_name, "Type": sndb_type, "subtype": sndb_subtype})
        sndb.to_csv(db_loc)
    
    @property
    def db(self):
        return self.caat

    def get_list_of_SNe(self, Type = None,
                            Year = None):#etc, other filter parameters - # of dete tions in filer/wavelength regime?
        #parse the pandas db
        raise NotImplementedError


class SN:
    """
    A Supernova object, taking a classification (i.e. SN II, SESNe, FBOT, etc.),
    a subtype (i.e., SN IIP, SN IIb, SN Ibn, etc.), and a name (i.e. SN2022acko)
    """

    base_path = '../data/'


    def __init__(self, name: str = None, data: dict = None):

        if isinstance(name, str):
            self.name = name
            self.data = {}

            found = False
            for typ in os.listdir(self.base_path):
                if os.path.isdir(os.path.join(self.base_path, typ)):
                    for subtyp in os.listdir(os.path.join(self.base_path, typ)):
                        if os.path.isdir(os.path.join(self.base_path, typ, subtyp)):
                            for snname in os.listdir(os.path.join(self.base_path, typ, subtyp)):
                                if name == snname:
                                    self.classification = typ
                                    self.subtype  = subtyp
                                    found = True

            if not found:
                print('No SN by that name found in our archives')
                raise Exception
            
            self.read_info_file()
            self.load_shifted_data()

        if isinstance(data, dict):
            self.name = ''
            self.classification = ''
            self.subtype = ''
            self.data = data
            self.info = {}
            self.shifted_data = {}


    def __repr__(self):
        return self.name


    def write_info_file(self):

        with open(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_info.json'), 'w+') as f:
            json.dump(self.info, f, indent=4)


    def read_info_file(self):

        if not os.path.exists(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_info.json')):
            print('Could not load info file')
            self.info = {}

        else:
            with open(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_info.json'), 'r') as f:
                info_dict = json.load(f)

            self.info = info_dict

    
    def load_swift_data(self):
        ### Load the Swift data for this object
        if not os.path.exists(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_uvotB15.1.dat')):
            print('No Swift file for ', self.name)
            return

        df = pd.read_csv(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_uvotB15.1.dat'), delim_whitespace=True, comment='#', names=['Filter', 'MJD', 'Mag', 'MagErr', '3SigMagLim', '0.98SatLim', 'Rate', 'RateErr', 'Ap', 'Frametime', 'Exp', 'Telapse'])

        for i, row in df.iterrows():
            if not np.isnan(row['Mag']):
                self.data.setdefault(row['Filter'], []).append({'mag': row['Mag'], 'err': row['MagErr'], 'mjd': row['MJD']})


    def load_json_data(self):

        ### Load data saved as a JSON file (ZTF, ATLAS, OpenSN, ASASSN)
        if not os.path.exists(os.path.join(self.base_path, self.classification, self.subtype, self.name)):
            print('No additional data files for ', self.name)
            return 

        dirfiles = os.listdir(os.path.join(self.base_path, self.classification, self.subtype, self.name))

        for f in dirfiles:
            ### Trying to filter out info file and shifted data file, should do this better
            if '.json' in f and '_info.json' not in f and '_shifted_data.json' not in f: 
                # print('Working with ', f)
                with open(os.path.join(self.base_path, self.classification, self.subtype, self.name, f), 'r') as jsonf:
                    d = json.load(jsonf)

                for filt, mag_list in d.items():
                    self.data.setdefault(filt, []).extend([mag for mag in mag_list if mag['err'] < 9999])


    def write_shifted_data(self):

        with open(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_shifted_data.json'), 'w+') as f:
            json.dump(self.shifted_data, f, indent=4)
    

    def load_shifted_data(self):

        ### Load shifted data that has been saved to a file

        if not os.path.exists(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_shifted_data.json')):
            print('Could not load shifted data file')
            self.shifted_data = {}

        else:

            with open(os.path.join(self.base_path, self.classification, self.subtype, self.name, self.name+'_shifted_data.json'), 'r') as f:
                shifted_data = json.load(f)

            self.shifted_data = shifted_data


    def plot_data(self, filts_to_plot=['all'], shifted_data_exists=False, view_shifted_data=False):
        if not self.data: # check if data/SN has not been previously read in/initialized
            self.load_swift_data()
            self.load_json_data()
        
        fig, ax = plt.subplots()

        colors = {'U': 'purple',
        'B': 'blue',
        'V': 'lime',
        'g': 'cyan',
        'r': 'orange',
        'i': 'red',
        'UVW2': '#FE0683',
        'UVM2': '#BF01BC',
        'UVW1': '#8B06FF',
        'c': 'turquoise',
        'o': 'salmon',
        }

        if filts_to_plot[0] == 'all': # if individual filters not specified, plot all by default
            filts_to_plot = colors.keys()

        if shifted_data_exists:
            data_to_plot = self.shifted_data
        elif view_shifted_data:
            for f in filts_to_plot:
                self.shift_to_max(f)
            data_to_plot = self.shifted_data
        else:
            data_to_plot = self.data
        
        for f in filts_to_plot:
            for filt, mag_list in data_to_plot.items():
                if f and f != filt:
                    continue
                else:
                    mjds = np.asarray([phot['mjd'] for phot in mag_list])
                    mags = np.asarray([phot['mag'] for phot in mag_list])
                    errs = np.asarray([phot['err'] for phot in mag_list])

                    ax.errorbar(mjds, mags, yerr=errs, fmt='o', mec='black', color=colors.get(filt, 'k'), label=filt)

        plt.gca().invert_yaxis()
        plt.legend()
        plt.xlabel('MJD')
        plt.ylabel('Apparent Magnitude')
        plt.minorticks_on()
        plt.show()


    def fit_for_max(self, filt, shift_array=[-3, -2, -1, 0, 1, 2, 3], plot=False):
        """
        Takes as input arrays for MJD, mag, and err for a filter
        as well as the guess for the MJD of maximum and an array
        to shift the lightcurve over,
        and returns estimates of the peak MJD and mag at peak
        """
        mjd_array = np.asarray([phot['mjd'] for phot in self.data[filt]])
        mag_array = np.asarray([phot['mag'] for phot in self.data[filt]])
        err_array = np.asarray([phot['err'] for phot in self.data[filt]])

        if len(mag_array) == 0:
            return None, None

        guess_mjd_max = mjd_array[np.where((mag_array == min(mag_array)))[0]][0]

        ### Do this because the array might not be ordered
        inds_to_fit = np.where((mjd_array > guess_mjd_max - 10) & (mjd_array < guess_mjd_max + 10))

        if len(inds_to_fit[0]) < 4:
            #print('Select a wider date range')
            return None, None

        numdata = len(mjd_array[inds_to_fit])
        numiter = max(int(numdata * np.log(numdata)**2), 200)

        fit_mjds = mjd_array[inds_to_fit]
        fit_mags = mag_array[inds_to_fit]
        fit_errs = err_array[inds_to_fit]

        peak_mags = []
        peak_mjds = []
        for num in range(numiter):
            simulated_points = []

            ### Shift by a certain number of days to randomly sample the light curve
            sim_shift = np.random.choice(shift_array)

            inds_to_fit = np.where((mjd_array > guess_mjd_max - 5 + sim_shift) & (mjd_array < guess_mjd_max + 5 + sim_shift))
            fit_mjds = mjd_array[inds_to_fit]
            fit_mags = mag_array[inds_to_fit]
            fit_errs = err_array[inds_to_fit]

            for i in range(len(fit_mjds)):
                simulated_points.append(np.random.normal(fit_mags[i], fit_errs[i]))
            fit = np.polyfit(fit_mjds, simulated_points, 2)
            f = np.poly1d(fit)
            fit_time = np.linspace(min(fit_mjds), max(fit_mjds), 100)

            if num % 25 == 0 and plot:
                plt.plot(fit_time, f(fit_time), color='black', linewidth=0.5)
            peak_mag = min(f(fit_time))
            peak_mags.append(peak_mag)
            peak_mjds.append(fit_time[np.argmin(f(fit_time))])

        if plot:
            plt.errorbar(mjd_array, mag_array, yerr=err_array, fmt='o', color='black')
            plt.errorbar(fit_mjds, fit_mags, yerr=fit_errs, fmt='o', color='blue')
            plt.errorbar(mean(peak_mjds), mean(peak_mags), xerr=stdev(peak_mjds), yerr=stdev(peak_mags), color='red', fmt='o')
            #plt.xlim(guess_mjd_max-10, guess_mjd_max+10)
            #plt.ylim(min(mag_array[inds_to_fit])-0.5, max(mag_array[inds_to_fit])+0.5)
            plt.gca().invert_yaxis()
            plt.show()

        self.info['peak_mjd'] = mean(peak_mjds)
        self.info['peak_mag'] = mean(peak_mags)
        self.info['peak_filt'] = filt

        return mean(peak_mjds), mean(peak_mags)


    def shift_to_max(self, filt, shift_array=[-3, -2, -1, 0, 1, 2, 3], plot=False):

        if not self.data:
            self.load_swift_data()
            self.load_json_data()

        if filt not in self.data.keys():
            return [], [], []


        if not self.info.get('peak_mjd') and not self.info.get('peak_mag'):

            peak_mjd, peak_mag = self.fit_for_max(filt, shift_array=shift_array, plot=plot)
            while not peak_mjd:
                # Fitting didn't work, try another filter
                for newfilt in ['V', 'g', 'c', 'B', 'r', 'o', 'U', 'i', 'UVW1']:
                    if newfilt in self.data.keys() and newfilt != filt:
                        peak_mjd, peak_mag = self.fit_for_max(newfilt, shift_array=shift_array, plot=plot)
            
                if newfilt == 'UVW1' and not peak_mjd:
                    print('Reached last filter and could not fit for peak')
                    break
        
        if not self.info.get('peak_mag', 0) > 0:
            return [], [], []

        mjds = np.asarray([phot['mjd'] for phot in self.data[filt]]) - self.info['peak_mjd']
        mags = np.asarray([phot['mag'] for phot in self.data[filt]]) - self.info['peak_mag']
        errs = np.asarray([phot['err'] for phot in self.data[filt]])

        self.shifted_data.setdefault(filt, []).extend(
            [{'mjd': mjds[i], 'mag': mags[i], 'err': errs[i]} for i in range(len(mjds))]
        )
        return mjds, mags, errs


    def log_transform_time(self, phases, phase_start=30):

        return np.log(phases + phase_start)
    

class SNCollection:

    """
    A SNCollection object, which holds an arbitrary number of SNe
    
    """
    base_path = '../data/'


    def __init__(self, names: Union[str, None] = None, 
                 Type: Union[str, None] = None, 
                 SNe: Union[list[SN], None] = None,
                **kwargs):
        
        self.subtypes = list(kwargs.keys())
        
        if(isinstance(SNe, SN)):
            self.sne = SNe
        else:
            if(isinstance(names, str)):
                self.sne = [SN(name) for name in names]
            else:
                if(type(Type) is not None):
                    type_list = CAAT.get_list_of_SNe(Type=Type)
                    self.sne = [SN(name) for name in type_list]
                    self.type=Type

    def __repr__(self):
        print("Collection of SN Objects")
        return self.sne

    def get_type_list(self):
        #Maybe this lives in a separate class that handles the csv db file
        raise NotImplementedError

    def plot_all_lcs(self, filt, subtypes='all', log_transform=False):

        if not type(subtypes) == list:
            subtypes = [subtypes]

        if 'all' in subtypes:
            subtypes = self.subtypes

        print(subtypes)

        for subtype in subtypes:

            fig, ax = plt.subplots()
            
            ### First find max values for given filt
            for sn in self.sne[subtype]:

                mjds, mags, errs = sn.shift_to_max(filt)
                
                if len(mjds) == 0:
                    continue
                
                if log_transform is not False:
                    mjds = sn.log_transform_time(mjds, phase_start=log_transform)
                ax.errorbar(mjds, mags, yerr=errs, fmt='o', color='k')
            
            plt.gca().invert_yaxis()
            plt.title('{} + {}'.format(subtype, filt))
            plt.show()


class SNType(SNCollection):

    """
    A Type object, building a collection of all SNe of a given type (classification)
    """
    subtypes = []
    sne = {}

    def __init__(self, classification):
        
        self.classification = classification

        self.get_subtypes()
        self.build_object_list()


    def get_subtypes(self):

        for d in os.listdir(os.path.join(self.base_path, self.classification)):
            if os.path.isdir(os.path.join(self.base_path, self.classification, d)):
                self.subtypes.append(d)


    def build_object_list(self):
    
        for subtype in self.subtypes:
            self.sne[subtype] = []
            for name in os.listdir(os.path.join(self.base_path, self.classification, subtype)):
                if os.path.isdir(os.path.join(self.base_path, self.classification, subtype, name)):
                    sn = SN(classification=self.classification, subtype=subtype, name=name)

                    self.sne[subtype].append(sn)
        

class Fitter:

    """
    A Fitter object, fitting the light curves of a class (Type) of supernovae
    """
    
    def __init__(self, collection):

        self.collection = collection


class RBFKernel:

    """
    An RBFKernel object, to be used in GP fitting
    Allows users to define Kernel parameters such as length scale, bounds, etc.
    """

    def __init__(self, length_scale, length_scale_bounds):

        self.kernel = RBF(length_scale=length_scale, length_scale_bounds=length_scale_bounds)


class WhiteNoiseKernel:

    """
    An RBFKernel object, to be used in GP fitting
    Allows users to define Kernel parameters such as noise level, bounds, etc.
    """

    def __init__(self, noise_level, noise_level_bounds):

        self.kernel = WhiteKernel(noise_level=noise_level, noise_level_bounds=noise_level_bounds)
    

class MaternKernel:

    """
    A MaternKernel, to be used in GP fitting
    Allows users to define Kernel parameters such as length scale, bounds, etc.
    """

    def __init__(self, length_scale, length_scale_bounds, nu):

        self.kernel = Matern(length_scale=length_scale, length_scale_bounds=length_scale_bounds, nu=nu)


class GP(Fitter):

    """
    GP fit to a single band
    """

    def __init__(self, collection, subtype, kernel):
        super().__init__(collection)
        self.subtype = subtype
        self.kernel = kernel


    def process_dataset_for_gp(self, filt, phasemin, phasemax, log_transform=False):
        phases, mags, errs = np.asarray([]), np.asarray([]), np.asarray([])

        for sn in self.collection.sne[self.subtype]:

            shifted_mjd, shifted_mag, err = sn.shift_to_max(filt)
            if len(shifted_mjd) == 0:
                continue
            if log_transform is not False:
                shifted_mjd = sn.log_transform_time(shifted_mjd, phase_start=log_transform)

            if log_transform is not False:
                inds_to_fit = np.where((shifted_mjd > np.log(phasemin+log_transform)) & (shifted_mjd < np.log(phasemax+log_transform)))[0]
            else:
                inds_to_fit = np.where((shifted_mjd > phasemin) & (shifted_mjd < phasemax))[0]
            
            phases = np.concatenate((phases, shifted_mjd[inds_to_fit]))
            mags = np.concatenate((mags, shifted_mag[inds_to_fit]))
            errs = np.concatenate((errs, err[inds_to_fit]))

        return phases.reshape(-1, 1), mags.reshape(-1, 1), errs.reshape(-1, 1)


    def run_gp(self, filt, phasemin, phasemax, test_size):

        phases, mags, errs = self.process_dataset_for_gp(filt, phasemin, phasemax)
        X_train, X_test, Y_train, Y_test, Z_train, Z_test = train_test_split(phases, mags, errs, test_size=test_size)

        ### Get array of errors at each timestep
        min_phase, max_phase = sorted(X_train)[0], sorted(X_train)[-1]
        phase_grid = np.linspace(min_phase, max_phase, len(X_train))
        phase_grid_space = (max_phase - min_phase)/len(X_train)

        err_grid = np.ones(len(phase_grid))
        for mjd in phase_grid:
            ind = np.where((X_train < mjd + phase_grid_space/2) & (X_train > mjd - phase_grid_space/2))[0]
            mags_at_this_phase = Y_train[ind]
            if len(mags_at_this_phase) > 1:
                std_mag = max(np.std(mags_at_this_phase), 0.01)
            elif len(mags_at_this_phase) == 1:
                std_mag = Z_train[ind]
            else:
                std_mag = 0.1
            err_grid[ind] = std_mag

        ### Run the GP
        #kernel = 1 * RBF(length_scale=10.0, length_scale_bounds=(1.0, 1e2)) + WhiteKernel(noise_level=1., noise_level_bounds=(1e-10, 10.))
        gaussian_process = GaussianProcessRegressor(
            kernel=self.kernel, alpha=err_grid, n_restarts_optimizer=9
        )
        gaussian_process.fit(X_train, Y_train)

        self.gaussian_process = gaussian_process

        return gaussian_process, phases, mags, errs, err_grid


    def predict_gp(self, filt, phasemin, phasemax, test_size, plot=False):

        gaussian_process, phases, mags, errs, err_grid = self.run_gp(filt, phasemin, phasemax, test_size)

        mean_prediction, std_prediction = gaussian_process.predict(sorted(phases), return_std=True)

        if plot:
            fig, ax = plt.subplots()
            ax.plot(sorted(phases), mean_prediction)
            ax.errorbar(phases, mags.reshape(-1), errs.reshape(-1), fmt='o', alpha=0.2)
            ax.fill_between(
                    sorted(phases.ravel()),
                    mean_prediction - 1.96*std_prediction,
                    mean_prediction + 1.96*std_prediction,
                    alpha=0.5
            )
            plt.gca().invert_yaxis()
            plt.show()


class GP3D(GP):

    """
    GP fit to all bands and epochs
    """
    wle = {'u': 3560,  'g': 4830, 'r': 6260, 'i': 7670, 'z': 8890, 'y': 9600, 'w':5985, 'Y': 9600,
           'U': 3600,  'B': 4380, 'V': 5450, 'R': 6410, 'G': 6730, 'E': 6730, 'I': 7980, 'J': 12200, 'H': 16300,
           'K': 21900, 'UVW2': 2030, 'UVM2': 2231, 'UVW1': 2634, 'F': 1516, 'N': 2267, 'o': 6790, 'c': 5330,
           'W': 33526, 'Q': 46028
    }

    def build_samples_3d(self, filt, phasemin, phasemax, log_transform=False):

        phases, mags, errs = self.process_dataset_for_gp(filt, phasemin, phasemax, log_transform=log_transform)

        min_phase, max_phase = sorted(phases)[0], sorted(phases)[-1]
        phase_grid = np.linspace(min_phase, max_phase, len(phases))
        phase_grid_space = (max_phase - min_phase)/len(phases)

        wl_grid = np.ones(len(phase_grid))
        err_grid = np.ones(len(phase_grid))
        for mjd in phase_grid:
            ind = np.where((phases < mjd + phase_grid_space/2) & (phases > mjd - phase_grid_space/2))[0]
            mags_at_this_phase = mags[ind]
            if len(mags_at_this_phase) > 1:
                std_mag = max(np.std(mags_at_this_phase), 0.01)
            elif len(mags_at_this_phase) == 1:
                std_mag = errs[ind]
            else:
                std_mag = 0.1

            err_grid[ind] = std_mag

            wl_grid[ind] = self.wle[filt]

        return phases, wl_grid, mags, err_grid


    def process_dataset_for_gp_3d(self, filtlist, phasemin, phasemax, log_transform=False, plot=False):

        all_phases, all_wls, all_mags, all_errs = [], [], [], []

        for filt in filtlist:
            phases, wl_grid, mags, err_grid = self.build_samples_3d(filt, phasemin, phasemax, log_transform=log_transform)

            all_phases = np.concatenate((all_phases, phases.flatten()))
            all_wls = np.concatenate((all_wls, wl_grid.flatten()))
            all_mags = np.concatenate((all_mags, mags.flatten()))
            all_errs = np.concatenate((all_errs, err_grid.flatten()))

        ### Create the template grid from the observations

        if log_transform is not False:
            phase_grid_linear = np.arange(phasemin, phasemax, 1/24.) # Grid of phases to iterate over, by hour
            phase_grid = np.log(phase_grid_linear + log_transform) # Grid of phases in log space
        else:
            phase_grid = np.arange(phasemin, phasemax, 1/24.) # Grid of phases to iterate over, by hour
        
        wl_grid = np.arange(min([self.wle[f] for f in filtlist])-500, max([self.wle[f] for f in filtlist])+500, 100) # Grid of wavelengths to iterate over, by 100 A
        grid = np.zeros((len(phase_grid), len(wl_grid)))
        err_grid = np.copy(grid)

        for i in range(len(phase_grid)):
            for j in range(len(grid[i,:])):

                ### Get all data that falls within this phase + 5 days, and this wl +- 100 A
                if log_transform is not False:
                    inds = np.where((np.exp(all_phases) - np.exp(phase_grid[i]) <= 5.0) & (np.exp(all_phases) - np.exp(phase_grid[i]) > 0.0) & (abs(all_wls - wl_grid[j]) < 100))[0]
                else:
                    inds = np.where((all_phases - phase_grid[i] <= 5.0) & (all_phases - phase_grid[i] > 0.0) & (abs(all_wls - wl_grid[j]) < 100))[0]
                
                if len(inds) == 0:
                    continue
                
                median_mag = np.median(all_mags[inds])
                iqr = np.subtract(*np.percentile(all_mags[inds], [75, 25]))
                
                grid[i,j] = median_mag
                err_grid[i,j] = iqr

        if plot:
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            
            if log_transform is not False:
                X, Y = np.meshgrid(np.exp(phase_grid) - log_transform, wl_grid)
            else:
                X, Y = np.meshgrid(phase_grid, wl_grid)

            Z = grid.T

            ax.plot_surface(X, Y, Z)
            plt.show()
        
        ### Subtract off templates for each SN LC set

        return all_phases, all_wls, all_mags, all_errs


    def run_gp(self, filtlist, phasemin, phasemax, test_size, plot=False, log_transform=False):

        all_phases, all_wls, all_mags, all_errs = self.process_dataset_for_gp_3d(filtlist, phasemin, phasemax, log_transform=log_transform, plot=plot)
        x = np.vstack((all_phases, all_wls)).T
        y = all_mags
        err = all_errs

        X_train, X_test, Y_train, Y_test, Z_train, Z_test = train_test_split(x, y, err, test_size=test_size)
    
        ### Run the GP
        #kernel = 1 * RBF(length_scale=[10.0, 500.0], length_scale_bounds=(1.0, 2e3)) + WhiteKernel(noise_level=1., noise_level_bounds=(1e-10, 10.))
        gaussian_process = GaussianProcessRegressor(
            kernel=self.kernel, alpha=Z_train, n_restarts_optimizer=10, normalize_y=True
        )
        gaussian_process.fit(X_train, Y_train)
        
        self.gaussian_process = gaussian_process
        
        return gaussian_process, X_train, X_test, Y_train, Y_test, Z_train, Z_test


    def predict_gp(self, filtlist, phasemin, phasemax, test_size, plot=False, log_transform=False):

        gaussian_process, X_train, X_test, Y_train, Y_test, Z_train, Z_test = self.run_gp(filtlist, phasemin, phasemax, test_size, plot=plot, log_transform=log_transform)

        if plot:
            fig, ax = plt.subplots()

        for filt in filtlist:

            test_times = np.linspace(min(X_test[:,0]), max(X_test[:,0]), 60)
            test_waves = np.ones(len(test_times)) * self.wle[filt]

            test_prediction, std_prediction = gaussian_process.predict(np.vstack((test_times, test_waves)).T, return_std=True)

            if plot:
                if log_transform is not False:
                    test_times = np.exp(test_times) - log_transform
                ax.plot(test_times, test_prediction, label=filt)
                ax.fill_between(
                        test_times,
                        test_prediction - 1.96*std_prediction,
                        test_prediction + 1.96*std_prediction,
                        alpha=0.2,
                )

        if plot:
            ax.invert_yaxis()
            ax.set_xlabel('Normalized Time [days]')
            ax.set_ylabel('Normalized Magnitude')
            #plt.suptitle('Classification: {}'.format(self.classification))
            ax.set_title('SubType: {}'.format(self.subtype))
            plt.legend()
            plt.show()

