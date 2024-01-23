import os
import datetime
import json
import logging
import glob
import subprocess
import argparse
from strenum import StrEnum
from enum import Enum, auto

mktSpec = {}
mktSpec['TS'] = {
    "TSDAM": {
        'starting_period': [("PD", 0)],
        'market_clearing_period': ("CD", 540),
        'interval_durations': [(36, 60)],
        'interval_types': [(24, "FWD"), (12, "ADVS")]
    },
    # "TSRTM": {
    #     'starting_period': [("PH", 0), ("PH", 5), ("PH", 10), ("PH", 15), ("PH", 20), ("PH", 25), ("PH", 30),
    #                         ("PH", 35), ("PH", 40), ("PH", 45), ("PH", 50), ("PH", 55)],
    #     'market_clearing_period': ("SP", -5),
    #     'interval_durations': [(36, 5)],
    #     'interval_types': [(1, "PHYS"), (35, "ADVS")]
    # }
    "TSRTM": {
        'starting_period': [("CH", 0), ("CH", 5), ("CH", 10), ("CH", 15), ("CH", 20), ("CH", 25), ("CH", 30),
                            ("CH", 35), ("CH", 40), ("CH", 45), ("CH", 50), ("CH", 55)],
        'market_clearing_period': ("SP", 0),
        'interval_durations': [(36, 5)],
        'interval_types': [(1, "PHYS"), (35, "ADVS")]
    }
}
mktSpec['MS'] = {
    "MSDAM": {
        'starting_period': [("PD", 0)],
        'market_clearing_period': ("CD", 540),
        'interval_durations': [(36, 60)],
        'interval_types': [(24, "FWD"), (12, "ADVS")]
    },
    "MSRTM": {
        'starting_period': [("PH", 0), ("PH", 5), ("PH", 10), ("PH", 15), ("PH", 20), ("PH", 25), ("PH", 30),
                            ("PH", 35), ("PH", 40), ("PH", 45), ("PH", 50), ("PH", 55)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(36, 5)],
        'interval_types': [(1, "PHYS"), (23, "FWD"), (12, "ADVS")]
    }
}
mktSpec['RHF'] = {
    "RHF36": {
        'starting_period': [("PH", 0)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(24, 5), (40, 15), (24, 60)],
        'interval_types': [(1, "PHYS"), (87, "FWD")]
    },
    "RHF12a": {
        'starting_period': [("PH", 15)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(24, 5), (39, 15)],
        'interval_types': [(1, "PHYS"), (62, "ADVS")]
    },
    "RHF12b": {
        'starting_period': [("PH", 30)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(24, 5), (38, 15)],
        'interval_types': [(1, "PHYS"), (61, "FWD")]
    },
    "RHF12c": {
        'starting_period': [("PH", 45)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(24, 5), (37, 15)],
        'interval_types': [(1, "PHYS"), (60, "FWD")]
    },
    "RHF2a": {
        'starting_period': [("PH", 5), ("PH", 20), ("PH", 35), ("PH", 50)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(23, 5)],
        'interval_types': [(1, "PHYS"), (21, "FWD")]
    },
    "RHF2b": {
        'starting_period': [("PH", 10), ("PH", 25), ("PH", 40), ("PH", 55)],
        'market_clearing_period': ("SP", -5),
        'interval_durations': [(22, 5)],
        'interval_types': [(1, "PHYS"), (20, "FWD")]
    }
}

class MarketType(StrEnum):
    TS = "TS"
    MS = "MS"
    RHF = "RHF"
    TEST = "TEST"

class IntervalType(StrEnum):
    PHYS = 'PHYS'
    FWD ='FWD'
    ADVS ='ADVS'

class Timeline(StrEnum):
    current_time = "CT"
    current_day = "CD"
    current_hour = "CH"
    planning_day = "PD"
    planning_hour = "PH"
    horizon_begin = "HB"
    horizon_end = "HE"
    market_clearing = "MC"
    start_period = "SP"

def validate_virtual(offer, time_step, rlist, times, found_errors):
    ''' Checks for any virtual offers and validates their format. '''
    virtual_keys = ['block_dec_mq', 'block_inc_mq', 'block_v_mv', 'block_v_mc']
    block_types = [list, str, float, int]
    for vkey in offer.keys():
        if vkey in rlist:
            continue
        try:
            vid, bus = vkey.split('_')
        except ValueError:
            print(f"ERROR: Invalid virtual offer key {vkey}. Does not match format [pid]_[bus]")
            found_errors = True
            continue
        for i, key in enumerate(virtual_keys):
            if key not in offer[vkey].keys():
                print(f'KEY ERROR: Virtual offer is missing required offer key: {key}')
                found_errors = True
            else:
                in_times = [t for t in offer[vkey][key].keys()]
                for time in in_times:
                    if time not in times:
                        print(f"VALUE ERROR: Found unexpected time {time} in virtual offer " + \
                              f" {key}. Expected the following times\n{times}")
                        found_errors = True
                for sys_t in times:
                    if sys_t not in in_times:
                        print(f"Warning: Missing offer at expected time {sys_t} in virtual " + \
                              f"offer {key}. This time step will not be bid into the market.")
                        found_errors = True
                cnt = 0
                for time, val in offer[vkey][key].items():
                    if type(val) not in block_types and cnt == 0:
                        print(f"TYPE ERROR: Unexpected value type ({type(val)}) in " + \
                              f"virtual block offer {key}")
                        found_errors = True
                    cnt += 1
        for key in offer[vkey].keys():
            if key not in virtual_keys:
                print(f"Warning: Extra key '{key}' found in virtual offer. This key will be " + \
                      "ignored.")
    return found_errors

def validate(offer, time_step, rlist, times):
    ''' Checks keys and timesteps/values for a storage offer. '''
    offer_keys = ['cost_rgu', 'cost_rgd', 'cost_spr', 'cost_nsp', 'block_ch_mc', 'block_dc_mc',
                  'block_soc_mc', 'block_ch_mq', 'block_dc_mq', 'block_soc_mq', 'soc_end',
                  'bid_soc', 'init_en', 'init_status', 'ramp_up', 'ramp_dn', 'socmax', 'socmin',
                  'soc_begin', 'eff_ch', 'eff_dc', 'chmax', 'dcmax']
    use_time = [True, True, True, True, True, True, True, True, True, True, False, False, False,
                False, False, False, False, False, False, False, False, True, True]
    block_types = [list, str, float, int]
    reg_types = [str, float, int]
    found_errors = False
    for rid in rlist:
        if rid not in offer.keys():
            print(f'KEY ERROR: Offer is missing top level key for resource id: {rid}')
            found_errors = True
        for i, key in enumerate(offer_keys):
            if key not in offer[rid].keys():
                print(f'KEY ERROR: Offer is missing required offer key: {key}')
                found_errors = True
            else:
                if use_time[i]:
                    in_times = [t for t in offer[rid][key].keys()]
                    for time in in_times:
                        if time not in times:
                            print(f"VALUE ERROR: Found unexpected time {time} in offer {key}. " + \
                                  f"Expected the following times\n{times}")
                            found_errors = True
                    for sys_t in times:
                        if sys_t not in in_times:
                            print(f"Warning: Missing offer at expected time {sys_t} in offer " + \
                                  f"{key}. This time step will not be bid into the market.")
                            found_errors = True
                if 'block' in key:
                    cnt = 0
                    for time, val in offer[rid][key].items():
                        if type(val) not in block_types and cnt == 0:
                            print(f"TYPE ERROR: Unexpected value type ({type(val)}) in " + \
                                  f"block offer {key}")
                            found_errors = True
                        cnt += 1
                elif key == 'bid_soc':
                    val = offer[rid][key]
                    if type(val) == bool or type(val) == int:
                        pass
                    else:
                        print(f"TYPE ERROR: bid_soc keyword must be boolean (not {type(val)})")
                        found_errors = True
                elif use_time[i]:
                    cnt = 0
                    for time, val in offer[rid][key].items():
                        if type(val) not in reg_types and cnt == 0:
                            print(f"TYPE ERROR: Unexpected value type ({type(val)}) in offer {key}")
                            found_errors = True
                        cnt += 1
                else:
                    val = offer[rid][key]
                    if type(val) not in reg_types:
                        print(f"TYPE ERROR: Unexpected value type ({type(val)}) in offer {key}")
                        found_errors = True
        for key in offer[rid].keys():
            if key not in offer_keys:
                print(f"Warning: Extra key '{key}' found in submitted offer. This key will be "+\
                      "ignored.")
    return found_errors

def print_message(found_errors, time_step):
    if not found_errors:
        print(f"Good news! Offer format appears valid for market clearing time step {time_step}")
    else:
        print("\nThe above errors were found in the formatted offer. Please address and retry.\n")
        exit(0)

class TimeKeeper:
    '''
    TimeKeeper maintains the simulation clock and facilitates sharing the timeline with other classes.
    Keys:
        Timeline.current_time:  current time on the simulation clock
        Timeline.current_day:   updates to 12:00:00 AM of the current time
        Timeline.current_hour:  updates to HH:00:00 of the current time
        Timeline.planning_day:  updates to one day after Timeline.current_day
        Timeline.planning_hour: updates to one hour after Timeline.current_hour
        Timeline.horizon_begin: first period in the market clearing horizon
        Timeline.horizon_end:   last period in the market clearing horizon
    Methods:
        get_status(): returns current status of clock with respect to simulation horizon.
        set_current_time(timestamp): initializes the clock at the timestamp (datetime), rounded to the next 5 minute interval.
        increment_time(): increments the clock by one interval (default 5 minutes).
        copy(): returns a copy of the dictionary of timeline data.
    '''
    def __init__(self, current_time=None):
        self.data = {}
        # Initialize the keys based on the Timeline class
        for key in Timeline:
            self.data[key] = None
        self.logger = logging.getLogger("TimeKpr")
        self.logger.debug("Initialized TimeKeeper")
        if current_time is not None:
            self.set_current_time(current_time)

    def __getitem__(self, key):
        return self.data[key]
    def __setitem__(self, key, value):
        self.data[key] = value

    class status(Enum):
        #-----PRE_SIMULATION-----|-----NORMAL-----|-----COMPLETE-----
        #                        ^Start           ^End
        PRE_SIMULATION = auto()
        NORMAL = auto()
        COMPLETE = auto()
        HORIZON_NOT_SET = auto()

    def get_status(self):
        current_time = self[Timeline.current_time]
        horizon_begin = self[Timeline.horizon_begin]
        horizon_end = self[Timeline.horizon_end]
        if horizon_begin is None or horizon_end is None:
            status = self.status.HORIZON_NOT_SET
        elif current_time < horizon_begin:
            status = self.status.PRE_SIMULATION
        elif current_time < horizon_end:
            status = self.status.NORMAL
        elif current_time >= horizon_end:
            status = self.status.COMPLETE
        else:
            raise Exception("Unexpected error in timeline status.")
        self.logger.debug(f"{status}")
        return status

    def set_horizon(self, start=None, end=None):
        if start is not None:
            self.data[Timeline.horizon_begin] = self._round_to_5min_interval(start)
        if end is not None:
            self.data[Timeline.horizon_end] = self._round_to_5min_interval(end)

    def set_current_time(self, timestamp):
        self.data[Timeline.current_time] = self._round_to_5min_interval(timestamp)
        self._update_timeline()
        self.logger.debug(f"Current time set to {self.data[Timeline.current_time]}")

    def increment_time(self, minutes=5):
        self.data[Timeline.current_time] += datetime.timedelta(minutes=minutes)
        self._update_timeline()
        self.logger.debug(f"Current time incremented to {self.data[Timeline.current_time]}")

    def _update_timeline(self):
        self.data[Timeline.current_day] = self.data[Timeline.current_time].replace(hour=0, minute=0, second=0, microsecond=0)
        self.data[Timeline.current_hour] = self.data[Timeline.current_time].replace(minute=0, second=0, microsecond=0)
        self.data[Timeline.planning_day] = self.data[Timeline.current_day] + datetime.timedelta(days=1)
        self.data[Timeline.planning_hour] = self.data[Timeline.current_hour] + datetime.timedelta(hours=1)

    def _round_to_5min_interval(self, timestamp):
        minutes_to_add = 5 - timestamp.minute % 5
        rounded_time = timestamp + datetime.timedelta(minutes=minutes_to_add)
        return rounded_time.replace(second=0, microsecond=0)

    def copy(self):
        return self.data.copy()

class MarketConfiguration:
    '''
    MarketConfiguration holds data that initializes a market model when prompted
    Methods:
        next_market_clearing(TimeKeeperCopy): returns the next timestamp when the market model should be created.
        to_json(): saves the market data to a JSON file.
    '''
    def __init__(self, name, config, network_file='./system_data/case5.json'):
        self.name = name
        self.__dict__.update(config)
        self._network_file = network_file
        self._first_t = None
        self._strtimefmt = '%Y%m%d%H%M'
        self.logger = logging.getLogger("MktConfig")
        self.logger.debug("Initialized MarketConfiguration.")

    def next_market_clearing(self, timekeeper):
        # sets the start_period and then the market_clearing_period.
        current_time = timekeeper[Timeline.current_time]
        clear_key, clear_delta = self.market_clearing_period
        mc = None
        sp = None
        reject_time = []
        for start_key, start_delta in self.starting_period:
            start_period = timekeeper[start_key] + datetime.timedelta(minutes=start_delta)
            if start_period < timekeeper[Timeline.horizon_begin]:
                self.logger.debug(f"Market start period {start_period} is before simulation start time {timekeeper[Timeline.horizon_begin]}. Skipped.")
                continue
            if start_period >= timekeeper[Timeline.horizon_end]:
                self.logger.debug(f"Market start period {start_period} is after simulation end time {timekeeper[Timeline.horizon_end]}. Skipped.")
                continue
            else:
                pass
            timekeeper[Timeline.start_period] = start_period
            new_mc = timekeeper[clear_key] + datetime.timedelta(minutes=clear_delta)
            if current_time <= new_mc:
                if mc is None or new_mc < mc:
                    mc = new_mc
                    sp = start_period
            else:
                reject_time.append(new_mc)
        self._first_t = sp
        return mc

    def to_json(self, t_dense=None):
        data_out = {}
        data_out = self._generate_interval_data(data_out, t_dense)
        data_out = self._generate_network_data(data_out)

        # save to json file
        uid = f"{self.name}{self._time2str(self._first_t)}"
        uid_json = f"./system_data/{uid}.json"
        cwd = os.getcwd()
        with open(os.path.join(cwd,uid_json), "w") as file_out:
            json.dump(data_out, file_out, indent=4)
        self.logger.info(f"Saved {uid_json}")
        return uid

    def _time2str(self, timestamp):
        return timestamp.strftime('%Y%m%d%H%M')

    def _generate_interval_data(self, data_out={}, t_dense=None):
        assert self._first_t is not None, "First period of model has not been identified. Please run MarketConfiguration.next_market_clearing() first."
        # populate t and duration data
        interval = self._first_t
        interval_list = []
        duration_list = []
        for duration_tuple in self.interval_durations:
            t_count, t_delta = duration_tuple
            for idx in range(t_count):
                interval_list.append(self._time2str(interval))
                duration_list.append(t_delta)
                interval += datetime.timedelta(minutes=t_delta)
        # populate physical, forward, and advisory data
        type_list = []
        for type_tuple in self. interval_types:
            t_count, t_type = type_tuple
            for idx in range(t_count):
                type_list.append(t_type)
        assert len(interval_list) == len(type_list), AssertionError(f"Input has duration data for {len(interval_list)} "
                                                                    f"intervals but type data for {len(type_list)} intervals.")
        type_dict = dict(zip(interval_list, type_list))
        phys_list = [key for key,value in type_dict.items() if value==IntervalType.PHYS]
        fwd_list = [key for key,value in type_dict.items() if value==IntervalType.FWD]
        advs_list = [key for key,value in type_dict.items() if value==IntervalType.ADVS]
        # populate dictionary
        data_in = {}
        data_in['t'] = interval_list
        data_in['tt'] = interval_list # Copy of t to use in generator startup logic
        # "Dense" time (5 minute intervals) included for forward position calculation
        if t_dense is None:
            data_in['t_dense'] = interval_list
        else:
            # Add in any new regular times
            t_dense += [t for t in interval_list if t not in t_dense]
            data_in['t_dense'] = t_dense
        data_in['physical'] = phys_list
        data_in['forward'] = fwd_list
        data_in['advisory'] = advs_list
        data_in['duration'] = {'dim': 1,
                               'keys': interval_list,
                               'values': duration_list}
        data_out.update(data_in)
        return data_out

    def _generate_network_data(self, data_out={}):
        '''Loads the electrical network topology'''
        with open(self._network_file, 'r') as file:
            data_in = json.load(file)
        data_out.update(data_in)
        return data_out

    def _generate_line_status(self, network_data:dict):
        '''Adds linestatus and monitored keywords to the topology dictionary.'''
        for item in ['linestatus', 'monitored']:
            append_dict = {item: {}}
            status = append_dict[item]
            status['__tuple__'] = True
            status['keys'] = []
            status['values'] = []
            for line in network_data['line']:
                status['keys'].append(line)
                status['values'].append(1)
            network_data.update(append_dict)

class MarketQueue:
    '''
    MarketQueue keeps track of the next MarketConfiguration that needs to be solved.
    Methods:
        on_deck(timestamp):         returns an iterator tuple of (key, MarketConfiguration) that are ready to be generated and solved.
        update(timestamp, [key]):   recomputes the next_market_clearing time given current time at timestamp.
    '''
    def __init__(self, config_dict, timekeeper=None, log_level=logging.DEBUG):
        self.queue = {key: {'market_configuration': MarketConfiguration(name=key, config=config),
                            'next_market_clearing': None}
                      for key, config in config_dict.items()}
        if timekeeper is not None:
            self.update(timekeeper)
        self.logger = logging.getLogger("MktQueue")

    def on_deck(self, timestamp):
        for name, market_data in self.queue.items():
            nmc = market_data['next_market_clearing']
            if nmc is not None and nmc <= timestamp:
                self.logger.info(f"Queueing {name} for {nmc}.")
                yield name, market_data['market_configuration']
            else:
                self.logger.debug(f"{name} next usage is at {nmc}.")

    def update(self, timekeeper, keys=None):
        if keys is None:
            self._update_all(timekeeper)
        else:
            for key in keys:
                self._update(self.queue[key], timekeeper)

    def _update(self, mkt_data, timekeeper):
        mkt_data['next_market_clearing'] = mkt_data['market_configuration'].next_market_clearing(timekeeper)

    def _update_all(self, timekeeper):
        for name, mkt_data in self.queue.items():
            self._update(mkt_data, timekeeper)

class MarketScheduler:
    '''
    MarketScheduler simulates market activities throughout the specified horizon.
    Arguments:
        type:   this specifies the market configuration (valid types are TS, MS, RHF, and TEST)
        start:  The first interval in the simulation horizon that will have a physical market settlement
        end:    The end of the last period in the simulation horizon (note: no physical delivery in this period)
    Methods:
        simulate(): controls the main loop of the market simulation.
        collect_offers(uid): collects all resource offers in JSON format
        solve_market(uid): executes the GAMS market clearing engine (market_clearing_engine.py)
        physical_dispatch(uid): simulates the physical dispatch of all resources
        settle_positions(uid): calculates the financial settlements of each market participant

    '''
    def __init__(self, mkttype:MarketType, start:datetime, end:datetime, language='python',
                 alg_name='market_participant.py', pid='p00001'):
        self.type = mkttype
        self.language = language
        self.alg_name = alg_name
        self.pid = pid
        self.logger = logging.getLogger("MktSchdlr")
        self.logger.debug("Initialized MarketScheduler.")
        current_time = start - datetime.timedelta(days=1)
        self.timekeeper = TimeKeeper(current_time=current_time)
        self.timekeeper.set_horizon(start=start, end=end)
        self.queue = MarketQueue(mktSpec[mkttype], timekeeper=self.timekeeper.copy())

    def simulate(self):
        time = self.timekeeper
        queue = self.queue

        # Load participant and resource information
        # participant_res = {'p00001':['T000001']} #du.load_participant_info()
        # resources_df = du.load_resource_info()
        # Save mkt_config file for participants
        # with open('offer_data/market_specification.json', "w") as fout:
        #     json.dump(mktSpec, fout, indent=4)
        # Tracker for the previous physical results and dispatch uid
        # self.prev_mkt_uid = None
        # self.prev_disp_uid = None
        # self.dense_time = None # For settlements at five-minute increments
        time_step = 1
        while time.get_status() is not time.status.COMPLETE:
            current_time = time[Timeline.current_time]
            cleared_mkts = []
            queue.update(time.copy())
            # Perform market clearing for market types (e.g. DAM, RTM)
            for mkt_key, mkt_config in queue.on_deck(current_time):
                # create data files
                # uid = mkt_config.to_json(t_dense=self.dense_time)
                # Update system offers, send status to participants, then collect all offers
                # du.update_participant_status(resources_df, participant_res, uid)
                # clear market
                print(f"Calling Participant Algorithm ({self.alg_name}) in language " + \
                      f"{self.language} for time step {time_step}\n")
                rlist, times = self.run_participant_algorithms(self.pid, self.language, self.alg_name,
                                                        time_step)
                self.validate_offers(self.pid, rlist, time_step, times)
                # self.send_history(uid)
                cleared_mkts.append(mkt_key)
                time_step += 1
            # prepare for next time interval
            time.increment_time()

            queue.update(time.copy(), keys=cleared_mkts)
        self.logger.info("Simulation completed.")

    def run_participant_algorithms(self, pid, language, alg_name, time_step):
        '''Calls participant offer algorithms to run and waits until they are finished'''
        pdir = f'offer_data/participant_{pid}'
        if time_step == 1:
            idx = 0
        elif time_step == 2:
            idx = 1
        else:
            idx = 2
        cwd = os.getcwd()
        with open(os.path.join(cwd,f'system_data/market{idx}.json'), 'r') as f:
            market_dict = json.load(f)
            market_json = json.dumps(market_dict)
        with open(os.path.join(cwd,f'system_data/resources{idx}.json'), 'r') as f:
            resource_dict = json.load(f)
            resource_json = json.dumps(resource_dict)
        if not os.path.exists(pdir):
            os.makedirs(pdir)
        if language.lower() == 'python':
            try:
                algorithm = subprocess.run(['python',f'{self.alg_name}', f'{time_step}', f'{market_json}',
                                        f'{resource_json}'], capture_output=True, text=True,
                                       check=True, cwd=os.path.join(os.getcwd(),pdir))
                print(algorithm.stdout)
                print(algorithm.stderr)
                self.logger.debug(algorithm.stdout)
                self.logger.debug(algorithm.stderr)
            except subprocess.CalledProcessError as e:
                print(e.output)
                print(e.stderr)
                exit(0)
        else:
            raise ValueError(f"No launcher built yet for coding language {language}.")

        rlist = [r for r in resource_dict['status'].keys()]
        times = [t for t in market_dict['timestamps']]
        return rlist, times

    def validate_offers(self, pid, rlist, time_step, times):
        '''
        Checks the submitted offer and returns a message if any formatting errors are found.
        '''
        # Walk through the participant and system directories and subdirectories
        part_directories = [entry for entry in glob.glob('offer_data/participant_p*') if os.path.isdir(entry)]
        for offer_dir in part_directories:
            files = glob.glob(os.path.join(offer_dir,f'offer_{time_step}.json'))
            if len(files) == 0:
                raise FileNotFoundError(f"File 'offer_{time_step}.json' not found in {offer_dir}")
            # Open the JSON file and load its contents
            with open(files[0], 'r') as file:
                offer_data = json.load(file)
                errs = validate(offer_data, time_step, rlist, times)
                errs = validate_virtual(offer_data, time_step, rlist, times, errs)
                print_message(errs, time_step)

    # def send_history(self, uid):
    #     '''Sends a formatted history.json file to the offer_data directory'''
    #     hist_keys = ['actual', 'delta', 'fwd_en', 'fwd_nsp', 'fwd_rgd', 'fwd_rgu', 'fwd_spr', 'lmp',
    #                    'mcp', 'schedule', 'settlement']
    #     hist_dict = {}
    #     for key in hist_keys:
    #         hist_dict[key] = f'{key}_placeholder'
    #     hist_file = './offer_data/history.json'
    #     with open(hist_file, "w") as f:
    #         json.dump(hist_dict, f, indent=4)

def setup_logger(log_level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s/%(name)s - %(message)s')
    # Set up Handlers (clear any existing to avoid multiple instances)
    if (logger.hasHandlers()):
        logger.handlers.clear()
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def test_scheduler(args):
    # Unpack input arguments
    mkt_type = args.mkt_type
    duration, duration_units = args.duration, args.duration_units
    start_date = args.start_date
    language, alg_name = args.language, args.algorithm_name
    now = datetime.datetime.strptime(start_date, '%Y%m%d%H%M')
    if duration_units == 'minutes':
        minutes = duration
    elif duration_units == 'hours':
        minutes = duration*60
    elif duration_units == 'days':
        minutes = duration*24*60
    else:
        raise ValueError(f'Unsupported duration_units ({duration_units}. Choose from "minutes",\
                         "hours", or "days".')
    # Round to the nearest 5 minutes
    minutes -= minutes % 5
    # Cap at one month
    if minutes > 60*24*30:
        minutes = 60*24*30
    if minutes < 5:
        minutes = 5
    then = now + datetime.timedelta(minutes=minutes)#60*36)
    mkt_types = ['TS', 'MS', 'RHF']
    if mkt_type not in mkt_types:
        raise ValueError(f'Input mkt_type {mkt_type} is not a valid choice. Enter one of: "TS", "MS", or "RHF".')
    scheduler = MarketScheduler(mkt_type, start=now, end=then, language=language,
                                alg_name=alg_name)
    scheduler.simulate()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--mkt_type', type=str, default='TS',
                        help="Market types, can choose TS (Two-Settlement), MS (Multi-Settlement), or RHF (Rolling Horizon Forward).", choices=['TS', 'MS', 'RHF'])
    parser.add_argument('-d', '--duration', type=int, default=10,
                        help="Choose the integer duration (units of duration are set in duration_units).")
    parser.add_argument('-u', '--duration_units', type=str, default='minutes',
                        help="Set the units of the duration. May be 'minutes', 'hours', or 'days'. (Minumum of 5 minutes, maximum of 30 days).", choices=['days', 'hours', 'minutes'])
    parser.add_argument('-s', '--start_date', type=str, default='201801272355',
                        help="Date/Time to start simulation. Format is YYYYmmddHHMM. Must be within the time stamp of the supplied forecast.")
    parser.add_argument('-l', '--language', type=str, default='python',
                        help="Code language desired for participant algorithm.")
    parser.add_argument('-a', '--algorithm_name', type=str, default='market_participant.py',
                        help="The name of the participant algorithm to run.")
    args = parser.parse_args()
    setup_logger(log_level=logging.INFO)
    test_scheduler(args)
