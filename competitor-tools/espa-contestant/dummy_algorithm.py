# This is a test dummy algorithm to get the opportunity cost curves
from ortools.linear_solver import pywraplp
import pandas as pd
import numpy as np
import argparse
import json
import datetime
from itertools import accumulate

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

#calculate the opportunity cost for charge/discharge in the DA market
def da_offers(market_type, prices):
    # battery parameters

    capacity=608
    ch_limit=125
    dis_limit=125
    effcy=0.892

    def scheduler(prices):

        number_step =len(prices)
        # [START solver]
        # Create the linear solver with the GLOP backend.
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if not solver:
            return
        # [END solver]

    #Variables: all are continous
        charge = [solver.NumVar(0.0, ch_limit, "c"+str(i)) for i in range(number_step)]
        discharge = [solver.NumVar(0, dis_limit,  "d"+str(i)) for i in range(number_step)]
        dasoc = [solver.NumVar(0.0, capacity, "b"+str(i)) for i in range(number_step+1)]
        dasoc[0]=0

    #Objective function
        solver.Minimize(
            sum(prices[i]*(charge[i]-discharge[i]) for i in range(number_step)))
        for i in range(number_step):
            solver.Add(dasoc[i] +effcy*charge[i] -discharge[i]==dasoc[i+1])
        solver.Solve()
        #print("Solution:")
        #print("The Storage's profit =", solver.Objective().Value())
        charge_list=[]
        discharge_list=[]
        dasoc_list=[]
        for i in range(number_step):
            charge_list.append(charge[i].solution_value())
            discharge_list.append(discharge[i].solution_value())
            #dasoc_list.append(dasoc[i].solution_value())
        return charge_list,discharge_list
    #return scheduler(prices)

    [charge_list,discharge_list]=scheduler(prices)
    #combine the charge/discharge list
    reversed_charge_list = [-ch if ch>0 else ch for ch in charge_list]
    combined_list = [reversed_charge if dis == 0 else dis for reversed_charge, dis in zip(reversed_charge_list, discharge_list)]
    #finding the index for first charge and last discharge
    t1_ch = next((index for index, value in enumerate(combined_list) if value < 0), None)
    t_last_dis = next((index for index in range(len(combined_list) - 1, -1, -1) if combined_list[index] > 0), None)
    # create two list for charging/discharging opportunity costs
    oc_dis_list=[]
    oc_ch_list=[]

    offer = pd.DataFrame(None,index=range(len(prices)), columns=['Time','charge cost','disch cost'])
    soc = pd.DataFrame(None,index=range(len(prices)+1), columns=['Time','SOC'])

#offer =offer.astype('Float64')

    for index, row in offer.iterrows():
        i =index
        row['Time'] =index
        if combined_list[i] <0:
            # Find the index of the first positive value after index i
            #j = np.argmax((combined_list > 0) & (np.arange(len(combined_list)) > i))
            j = i+ 1 + next((index for index, value in enumerate(combined_list[i+1:]) if value > 0), None)
            #print("i is ", i)
            #print("j is ", j)
            oc_ch = min(prices[1:j], effcy * prices[j]) if i == 0 else min(np.delete(prices[0:j], i).min(), effcy * prices[j])
            oc_ch_list.append(oc_ch)
            arr1 = prices[0] if i == 0 else prices[0:i].min()
            arr2 = 0 if j == i + 1 else prices[i + 1] if j == i + 2 else prices[(i + 1):j].min()
            oc_dis =oc_ch+0.01 if i==0 else (-prices[i]+arr1+arr2)/effcy
            oc_dis_list.append(oc_dis)
            #print("oc_ch type is", oc_ch.dtype)
            row['charge cost'] =oc_ch
            row['disch cost'] =oc_dis

        elif combined_list[i] >0:
                # for scheduled discharge

                j = max((index for index, value in enumerate(combined_list[:i]) if value < 0), default=None)
                arr1 = 0 if i==len(prices) else prices[i+1] if i==len(prices)-1 else prices[(i+1):].max()
                arr2 = 0 if j ==i-1 else prices[j+1] if j == i-2 else prices[(j+1):i].max()
                oc_ch =(-prices[i] +arr1 +arr2)*effcy
                oc_ch_list.append(oc_ch)
                oc_dis = max(prices[j]/effcy, prices[(j+1):].max())
                oc_dis_list.append(oc_dis)
                row['charge cost'] =oc_ch
                row['disch cost'] =oc_dis
        # For hours before the first charge
        elif combined_list[i]==0:
            if i< t1_ch:
                    # opportunity cost for charging
                    max_ch_temp = 0 if i == t1_ch-1 else prices[i+1] if i== t1_ch-2 else prices[(i+1):t1_ch].max()
                    oc_ch =max(max_ch_temp*effcy, prices[t1_ch])
                    oc_ch_list.append(oc_ch)
                    row['charge cost'] =oc_ch
                    oc_dis = oc_ch+0.01 if i==0 else prices[0]/effcy if i==1 else prices[0:i].min()/effcy
                    #opportunity cost for discharging
                    oc_dis_list.append(oc_dis)
                    row['disch cost'] =oc_dis
            #For hours after the last discharge
            elif i>t_last_dis:
                    print("index i is," , i)
                    print("last discharge is," , t_last_dis)
                    oc_ch =  prices[(i+1):].max()*effcy if i <len(prices)-2 else prices[i+1] if i== len(prices)-2 else np.min(prices)
                    oc_ch_list.append(oc_ch)
                    arr3 = prices[i-1] if i== t_last_dis+2 else prices[(t_last_dis+1):i] if i> t_last_dis+2 else np.max(prices)
                    oc_dis = min(prices[t_last_dis], arr3.min()/effcy)
                    oc_dis_list.append(oc_dis)
                    row['charge cost'] =oc_ch
                    row['disch cost'] =oc_dis

                # for hours between
                #print("orignial i is ", i)
            # For hours between a scheduled withdrwal and injection
            else:
                    j_next = i+ 1 + next((index for index, value in enumerate(combined_list[i+1:]) if value > 0), None)
                    j_prev = max((index for index, value in enumerate(combined_list[:i]) if value < 0), default=None)
                    oc_ch = 0 if i<j_prev+2 else prices[i-1] if i==j_prev+2 else max(prices[(j_prev+1):i].max()*effcy,prices[j_prev])
                    oc_ch_list.append(oc_ch)
                    row['charge cost'] =oc_ch

                    oc_dis = 0 if i>j_next-2 else min(prices[j_next], prices[i+1]/effcy) if i== j_next-2 else min(prices[j_next], prices[(i+1):j_next].min()/effcy)
                    oc_dis_list.append(oc_dis)
                    row['disch cost'] =oc_dis
    quantity = pd.DataFrame(charge_list)
    offer_ch =pd.concat([offer['Time'], offer['charge cost'], quantity], axis=1,ignore_index=True)
    offer_ch.columns =['Time','COST','MW']

    quan2 =pd.DataFrame(discharge_list)
    offer_dis=pd.concat([offer['Time'], offer['disch cost'], quantity], axis=1,ignore_index=True)
    offer_dis.columns= ['Time','COST','MW']

    return offer_ch, offer_dis,soc

if __name__ == '__main__':
    # Add argument parser for three required input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('time_step', type=int, help='Integer time step tracking the progress of the\
                        simulated market.')
    parser.add_argument('market_file', help='path to json formatted dictionary with market \
                        information.')
    parser.add_argument('resource_file', help='path to json formatted dictionary with resource \
                        information.')

    args = parser.parse_args()

    # Parse json inputs into python dictionaries
    time_step = args.time_step
    with open(args.market_file, 'r') as f:
        market_info = json.load(f)
    with open(args.resource_file, 'r') as f:
        resource_info = json.load(f)

    # Read in information from the market
    uid = market_info["uid"]
    market_type = market_info["market_type"]
    if 'DAM' in market_type:
        prices = market_info["previous"][market_type]["prices"]["EN"]["CISD"]
        required_times = [t for t in market_info['timestamps']]
        price_dict = {required_times[i]:prices[i] for i in range(len(required_times))}
        # Writing prices to a local JSON file
        file_path = "da_prices.json"
        with open(file_path, "w") as file:
            json.dump(price_dict, file)
        prices = np.array(prices)

        # Make the offer curves and unload into arrays
        offer_ch, offer_dis,soc = da_offers(market_type, prices)
        charge_mc = offer_ch['COST'].values
        charge_mq = offer_ch['MW'].values
        discharge_mc = offer_dis['COST'].values
        discharge_mq = offer_dis['MW'].values

        # Offer parsing script below:

        # Convert the offer curves to timestamp:offer_value dictionaries
        block_ch_mc = {}
        for i, cost in enumerate(charge_mc):
            block_ch_mc[required_times[i]] = float(cost)

        block_ch_mq = {}
        for i, power in enumerate(charge_mq):
            block_ch_mq[required_times[i]] = float(power) # 125MW

        block_dc_mc = {}
        block_soc_mc = {}
        for i, cost in enumerate(discharge_mc):
            block_dc_mc[required_times[i]] = float(cost)
            block_soc_mc[required_times[i]] = 0

        block_dc_mq = {}
        block_soc_mq = {}
        for i, power in enumerate(discharge_mq):
            block_dc_mq[required_times[i]] = float(power) # 125MW
            block_soc_mq[required_times[i]] = 0

        reg = ['cost_rgu', 'cost_rgd', 'cost_spr', 'cost_nsp']
        zero_arr = np.zeros(len(required_times))
        rgu_dict = {}
        for r in reg:
            rgu_dict[r] = {}
            for t in required_times:
                rgu_dict[r][t] = 0

        max_dict = {}
        for mx in ['chmax', 'dcmax']:
            max_dict[mx] = {}
            for t in required_times:
                max_dict[mx][t] = 125

        constants = {}
        constants['soc_begin'] = 128
        constants['init_en'] = 0
        constants['init_status'] = 0
        constants['ramp_dn'] = 9999
        constants['ramp_up'] = 9999
        constants['socmax'] = 608
        constants['socmin'] = 128
        constants['eff_ch'] = 0.892
        constants['eff_dc'] = 1.0
        constants['soc_end'] = 128
        constants['bid_soc'] = False

        # Pacakge the dictionaries into an output formatted dictionary
        rid = 'R00229'
        offer_out_dict = {rid:{}}
        offer_out_dict[rid] = {"block_ch_mc":block_ch_mc, "block_ch_mq":block_ch_mq, "block_dc_mc":block_dc_mc, "block_dc_mq":block_dc_mq, "block_soc_mc":block_soc_mc, "block_soc_mq":block_soc_mq}
        offer_out_dict[rid].update(rgu_dict)
        offer_out_dict[rid].update(max_dict)
        offer_out_dict[rid].update(constants)

        # Save as json file in the current directory with name offer_{time_step}.json
        with open(f'offer_{time_step}.json', 'w') as f:
            json.dump(offer_out_dict, f, indent=4, cls=NpEncoder)
    elif 'RTM' in market_type:
        price_path = "da_prices.json"
        with open(price_path, "r") as file:
            prices = json.load(file)
            dam_times = [key for key in prices.keys()]
            prices = [value for value in prices.values()]
        # Read in information from the resource
        en_schedule_list = [z[0] for z in resource_info["ledger"]["R00229"]["EN"].values()]
        sch_time = [z for z in resource_info["ledger"]["R00229"]["EN"].keys()]
        #print(en_schedule_list)
        #print("time is", time)
        initial_soc = resource_info["status"]["R00229"]["soc"]
        marginal_quantities, marginal_prices = zip(*en_schedule_list)
        adjusted_marginal_quantities = [initial_soc] + list(marginal_quantities)
        # Calculating the cumulative sum of adjusted marginal quantities
        cumulative_soc = list(accumulate(adjusted_marginal_quantities))
        #print("cumulative soc is", cumulative_soc)
        # Generating a new list of cumulative soc and marginal prices
        soc_price_list = list(zip(cumulative_soc, marginal_prices))
        #print(soc_price_list)
        required_times = [t for t in market_info['timestamps']]
         # Convert the offer curves to timestamp:offer_value dictionaries
        #soc_mq =soc_price_list.values
        soc_mq =cumulative_soc
        soc_mc =prices
        time_soc = np.zeros(len(required_times))
        price_soc = np.zeros(len(required_times))
        soc = np.zeros(len(required_times))
        ti =0
        idx_price = 0
        for i in range(len(required_times)):
            # real-time datetime format
            dt1 = datetime.datetime.strptime(required_times[i], '%Y%m%d%H%M')
            # resource json file datetime format
            dt2 = datetime.datetime.strptime(sch_time[ti], '%Y%m%d%H%M')
            dt3 = datetime.datetime.strptime(dam_times[idx_price], '%Y%m%d%H%M')
            while dt1 > dt3 and dt1.hour != dt3.hour:
                idx_price += 1
                dt3 = datetime.datetime.strptime(dam_times[idx_price], '%Y%m%d%H%M')
            if idx_price == len(dam_times)-1:
                price_soc[i] = 0
            else:
                if marginal_quantities[ti]>0:
                    multiplier = 1
                else:
                    multiplier = -1
                price_soc[i] = prices[idx_price+1]*multiplier

            while dt1 > dt2 and dt1.hour != dt2.hour:
                ti += 1
                dt2 = datetime.datetime.strptime(sch_time[ti], '%Y%m%d%H%M')

            if dt1.hour == dt2.hour:
                soc[i] = soc_mq[ti+1]
            elif ti == 0:
                soc[i] = initial_soc
            else:
                soc[i] = soc_mq[ti]
            print("soc is", soc[i])

        block_soc_mq = {}
        for i, soc_mq in enumerate(required_times):
            block_soc_mq[required_times[i]] = float(soc[i])
        block_soc_mc = {}
        for i, soc_mc in enumerate(required_times):
            block_soc_mc[required_times[i]] = float(price_soc[i])

         # Offer parsing script below:

        # Convert the offer curves to timestamp:offer_value dictionaries
        charge_mc = np.zeros(36)
        charge_mq = np.zeros(36)
        discharge_mc = np.zeros(36)
        discharge_mq = np.zeros(36)
        block_ch_mc = {}
        for i, cost in enumerate(charge_mc):
            block_ch_mc[required_times[i]] = 0

        block_ch_mq = {}
        for i, power in enumerate(charge_mq):
            block_ch_mq[required_times[i]] = 0 # 125MW

        block_dc_mc = {}

        for i, cost in enumerate(discharge_mc):
            block_dc_mc[required_times[i]] = 0


        block_dc_mq = {}
        for i, power in enumerate(discharge_mq):
            block_dc_mq[required_times[i]] = 0 # 125MW


        reg = ['cost_rgu', 'cost_rgd', 'cost_spr', 'cost_nsp']
        zero_arr = np.zeros(len(required_times))
        rgu_dict = {}
        for r in reg:
            rgu_dict[r] = {}
            for t in required_times:
                rgu_dict[r][t] = 0

        max_dict = {}
        for mx in ['chmax', 'dcmax']:
            max_dict[mx] = {}
            for t in required_times:
                max_dict[mx][t] = 125

        constants = {}
        constants['soc_begin'] = 128
        constants['init_en'] = 0
        constants['init_status'] = 0
        constants['ramp_dn'] = 9999
        constants['ramp_up'] = 9999
        constants['socmax'] = 608
        constants['socmin'] = 128
        constants['eff_ch'] = 0.892
        constants['eff_dc'] = 1.0
        constants['soc_end'] = 128
        constants['bid_soc'] = True

        # Pacakge the dictionaries into an output formatted dictionary
        rid = 'R00229'
        offer_out_dict = {rid:{}}
        offer_out_dict[rid] = {"block_ch_mc":block_ch_mc, "block_ch_mq":block_ch_mq, "block_dc_mc":block_dc_mc, "block_dc_mq":block_dc_mq, "block_soc_mc":block_soc_mc, "block_soc_mq":block_soc_mq}
        offer_out_dict[rid].update(rgu_dict)
        offer_out_dict[rid].update(max_dict)
        offer_out_dict[rid].update(constants)
        # Save as json file in the current directory with name offer_{time_step}.json
        with open(f'offer_{time_step}.json', 'w') as f:
            json.dump(offer_out_dict, f, indent=4, cls=NpEncoder)



