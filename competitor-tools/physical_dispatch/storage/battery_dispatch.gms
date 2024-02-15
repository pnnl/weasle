*** ESPA-Comp: Physical Dispatch, 0th order battery model

$setnames "%gams.i%" filepath filename fileextension
$if not set market_uid $abort "Must provide the current market UID to initialize the market clearing engine."
$if not set previous_uid $abort "Must provide the previous market UID to initialize the market clearing engine."
$if not set run_path $set run_path '.'
$if not set savesol $set savesol 0
$if not set relax $set relax 0
option decimals=5;

Sets
participant,resource
str(resource)
resource_owner(participant,resource)
;
Alias (resource,n);

$include "../utils/load_battery_attributes.gms"
$include "../utils/load_previous_interval.gms"
$include "../utils/load_current_interval.gms"

* Rescale soc to percentage (and rescale to MWh)
soc_init(n) = soc_init(n)/soc_capacity(n);

* Input
Parameters
imax_n              Maximum current charge into battery n   
imin_n              Maximum current discharge from battery n
vmax_n              Maximum voltage of battery n
vmin_n              Minimum voltage of battery n
cell_count_n        Number of cells in battery n (power scaling factor)                         /0/
ch_cap_n            Charge capacity of battery n                                                /0/
target_n            Target dispatch level                                                       /0/
temp_env_n          Ambient temperature                                                         /0/
eff_coul_n          Coulombic efficiency of battery n   Float   %                               /0/
eff_inv0_n          0-order inverter efficiency coefficient of battery n                        /0/
eff_inv1_n          1st order inverter efficiency coefficient of battery n                      /0/
eff_inv2_n          2nd-ord inverter efficiency coefficient of battery n                        /0/
voc0_n              0th-order open-circuit voltage coefficient of battery n                     /0/
voc1_n              1st-order open-circuit voltage coefficient of battery n                     /0/
voc2_n              2nd-order open-circuit voltage coefficient of battery n                     /0/
voc3_n              3rd-order open-circuit voltage coefficient of battery n                       /0/
resis_n             Internal resistance of battery n                                            /0/  
soc_init_n          Initial state-of-charge of battery n                                        /0/
socmax_n            Maximum state-of-charge of battery n                                        /0/
socmin_n            Minimum state-of-charge of battery n                                        /0/
soc_capacity_n      State-of-charge capacity in MWh of battery n                                /0/
therm_cap_n         Thermal capacity of battery n                                               /0/
temp_init_n         Initial temperature of battery n                                            /0/
Utherm_n            Thermal transmittance between the surface of battery n and the environment  /0/
;
* Output
Parameters
current(n)          DC current through battery (at the cell level)
dispatch(n)         Actual dispatch of battery (MW)
dc_power(n)         DC power output of battery (at the cell level)
voltage_bat(n)      Voltage at battery terminal (at the cell level)
voltage_oc(n)       Open circuit voltage of battery (at the cell level)
*soc(n)              (defined in load_previous_interval.gms)
*temp(n)             (defined in load_previous_interval.gms)
;

Variables
i_bat               DC current through the battery
i_in                Current flowing into the battery
i_out               Current flowing out of the battery
p_dispatch          Dispatched power (positive discharge sign convention)
p_ac                AC power dispatch   
p_dc                DC power output 
v_bat               Battery terminal voltage    
v_oc                Battery open circuit voltage
v_socmwh            Interavl-ending state-of-charge in MWh for output
v_soc               Interval-ending state-of-charge
v_temp              Interval-ending cell temperature
v_dev               Dispatch deviation of battery n
v_pos               Positive dispatch deviation
v_neg               Negative dispatch deviation
;

Equations
c_deviation         Dispatch deviation
c_dispatch          Conversion from p_ac to dispatch
c_socmwh            Conversion from soc % to MWh
c_target            Battery dispatch target value
c_ac_dc_inverter    Quadratic AC-DC power inverter efficiency
c_ohms_law          Ohm's law calculation of battery DC power output
c_kvl               KVL calculation of battery terminal voltage
c_opencircuit       Open-circuit voltage approximation from cubic function of state-of-charge
c_current_in_out    Definition for nonnegative battery current variables
c_state_of_charge   State-of-charge progression
c_temperature       Temperature progression due to resistive heating and environmental cooling
c_complementarity   Battery current complementarity
;

v_pos.lo = 0;
v_neg.lo = 0;

* Constraints
c_deviation..       v_dev =g= v_pos + v_neg;
c_dispatch..        p_dispatch =e= -p_ac * cell_count_n / 1000.0;
c_socmwh..          v_socmwh =e= v_soc * soc_capacity_n;
c_target..          p_dispatch =e= target_n + v_pos - v_neg;
c_ac_dc_inverter..  p_dc =e= eff_inv2_n * power(p_ac,2) + eff_inv1_n * p_ac + eff_inv0_n;
c_ohms_law..        p_dc =e= i_bat * v_bat / 1000;
c_kvl..             v_bat =e= v_oc + resis_n * i_bat;
c_opencircuit..     v_oc =e= voc3_n * power(v_soc,3) + voc2_n * power(v_soc,2) + voc1_n * v_soc + voc0_n;
c_current_in_out..  i_bat =e= i_in - i_out;
c_state_of_charge.. ch_cap_n * (v_soc - soc_init_n) =e= duration_h * (eff_coul_n * i_in - i_out);
c_temperature..     therm_cap_n * (v_temp - temp_init_n) =e= duration_s * (resis_n * power(i_bat,2) + Utherm_n * (temp_env_n - v_temp));
c_complementarity.. i_in * i_out =e= 0;

model dispatch_sim /all/;

set dict /  n.              scenario.   ''
            ch_cap_n.       param.      ch_cap  
            target_n.       param.      target
            cell_count_n.   param.      cell_count
            eff_coul_n.     param.      eff_coul 
            eff_inv0_n.     param.      eff_inv0 
            eff_inv1_n.     param.      eff_inv1 
            eff_inv2_n.     param.      eff_inv2 
            voc0_n.         param.      voc0     
            voc1_n.         param.      voc1     
            voc2_n.         param.      voc2   
            voc3_n.         param.      voc3   
            resis_n.        param.      resis    
            soc_init_n.     param.      soc_init
            soc_capacity_n. param.      soc_capacity
            therm_cap_n.    param.      therm_cap
            temp_init_n.    param.      temp_init
            temp_env_n.     param.      temp_env 
            Utherm_n.       param.      Utherm                         
            i_bat.          lower.      imin            
            i_bat.          upper.      imax            
            v_bat.          lower.      vmin            
            v_bat.          upper.      vmax            
            p_dispatch.     lower.      pmin            
            p_dispatch.     upper.      pmax            
            v_soc.          lower.      socmin                     
            v_soc.          upper.      socmax                     
            v_temp.         lower.      temp_min              
*            v_temp.         upper.      temp_max              
            i_bat.          level.      current   
            p_dispatch.     level.      dispatch  
            p_dc.           level.      dc_power  
            v_bat.          level.      voltage_bat
            v_oc.           level.      voltage_oc
            v_socmwh.       level.      soc      
            v_temp.         level.      temp
/;

solve dispatch_sim using nlp min v_dev scenario dict;

display dispatch, soc;

execute_unload '%run_path%/results/dispatch_%market_uid%.gdx', target,dispatch,soc,temp,current,dc_power,voltage_bat,voltage_oc;


